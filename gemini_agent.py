"""
Gemini-powered EMI & Loan Advisor.

How it works (hybrid):
  * Gemini understands the user's message (free-form language, Hinglish, attached
    salary slips / offer letters) and decides which tools to call.
  * YOUR code does all the maths and memory updates: compute_emi, compare_options,
    save_user_profile and estimate_eligibility run locally, so the numbers are exact.
  * If Gemini is unavailable (no key, no internet, quota reached) the original
    rule-based EMILoanAgent answers instead, so the app never stops working.
"""
import copy
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from agent import (EMILoanAgent, AFFORDABILITY_LIMIT, DEFAULT_RATE, DEFAULT_MONTHS,
                   inr, fmt_tenure)

try:
    from google import genai
    from google.genai import types
    _IMPORT_ERROR = None
except Exception as _e:          # google-genai not installed
    genai = types = None
    _IMPORT_ERROR = _e

# Models are tried in this order. Flash-Lite first because its free daily quota is larger.
# Override without editing code:  set GEMINI_MODELS=gemini-3.5-flash,gemini-3.5-flash-lite
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]

MAX_TOOL_ROUNDS = 6
MAX_FILE_BYTES = 15 * 1024 * 1024
HISTORY_TURNS = 8
DEFAULT_FILE_PROMPT = ("I attached file(s). Read them, tell me the loan details you find "
                       "(income, loan amount, rate, tenure) and calculate the EMI if you can.")

FILE_NOTE = ("📎 I've saved your attachment to this chat, but I can't read the contents of images "
             "or documents in offline mode. Please type the key details (monthly income, loan amount, "
             "rate, tenure) and I'll calculate.")

# Cheap intents are answered by the rule-based agent without spending an API call.
_RULES_ONLY = re.compile(
    r"^\s*(?:(?:hi|hii+|hello|hey|namaste|good (?:morning|afternoon|evening))"
    r"|(?:thanks?|thank you|ok(?:ay)?|great|cool))\b[\s!.]*$"
    r"|\b(?:reset|start over|clear memory|new session)\b", re.I)

# Process-wide memory of which model worked / does not exist
_GOOD_MODEL: Optional[str] = None
_DEAD_MODELS: set = set()


def _configured_models() -> List[str]:
    env = os.environ.get("GEMINI_MODELS", "").strip()
    return [m.strip() for m in env.split(",") if m.strip()] if env else list(DEFAULT_MODELS)


def _err_code(e: Exception) -> Optional[int]:
    code = getattr(e, "code", None)
    if isinstance(code, int):
        return code
    m = re.search(r"\b([45]\d\d)\b", str(e))
    return int(m.group(1)) if m else None


def _friendly_reason(e: Exception) -> str:
    code, msg = _err_code(e), str(e).lower()
    if code == 429 or "resource_exhausted" in msg or "quota" in msg:
        return "free-tier limit reached"
    if code in (401, 403) or "api key" in msg or "api_key" in msg:
        return "API key was rejected"
    if code == 404:
        return "model not available"
    if code in (500, 503):
        return "Gemini is busy"
    if code is None and any(w in msg for w in ("connect", "resolve", "timeout", "network", "ssl")):
        return "could not reach Gemini (check internet)"
    return (str(e).strip().splitlines() or ["unknown error"])[0][:100]


# ---------------------------------------------------------------------------
# Tool declarations shown to Gemini (execution happens in _dispatch below)
# ---------------------------------------------------------------------------
def _build_tools():
    S, T = types.Schema, types.Type
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="save_user_profile",
            description="Remember facts the user stated about themselves. Pass ONLY what the user "
                        "actually said (or what an attached document clearly shows).",
            parameters=S(type=T.OBJECT, properties={
                "monthly_income": S(type=T.NUMBER, description="Monthly income in rupees, e.g. 80000"),
                "no_regular_income": S(type=T.BOOLEAN, description="True if the user says they have no regular income / are unemployed"),
                "no_credit_history": S(type=T.BOOLEAN, description="True if the user has no credit history / never took a loan or card"),
                "credit_score": S(type=T.INTEGER, description="CIBIL / credit score if stated"),
            })),
        types.FunctionDeclaration(
            name="compute_emi",
            description="Calculate EMI, total interest and total payment for ONE loan scenario and "
                        "store it in memory. Call once per scenario (e.g. once for 3 years and once for 5 years).",
            parameters=S(type=T.OBJECT, properties={
                "amount": S(type=T.NUMBER, description="Principal in rupees (5 lakh = 500000)"),
                "rate_annual": S(type=T.NUMBER, description="Annual interest rate in percent, e.g. 8.5"),
                "months": S(type=T.INTEGER, description="Tenure in months (5 years = 60)"),
                "new_comparison": S(type=T.BOOLEAN, description="True for the FIRST scenario of a new loan amount, so old scenarios are cleared"),
                "assumptions": S(type=T.STRING, description="If the user did not give the rate or tenure and you used defaults, describe them, e.g. 'interest rate 10.5%, tenure 5 yr (60m)'"),
            }, required=["amount", "rate_annual", "months"])),
        types.FunctionDeclaration(
            name="compare_options",
            description="Compare all stored loan scenarios against the user's income (40% EMI rule) and "
                        "find the affordable option with the lowest total interest. Call after compute_emi."),
        types.FunctionDeclaration(
            name="estimate_eligibility",
            description="Estimate the maximum safe EMI and loan size from monthly income.",
            parameters=S(type=T.OBJECT, properties={
                "monthly_income": S(type=T.NUMBER, description="Optional; defaults to the remembered income"),
            })),
    ])


class GeminiLoanAgent(EMILoanAgent):
    def __init__(self, monthly_income: Optional[float] = None, api_key: Optional[str] = None):
        super().__init__(monthly_income)
        self.api_key = api_key
        self.models = _configured_models()
        self.last_model: Optional[str] = None
        self.last_error: Optional[str] = None

    # The base reset() calls __init__(); keep the connection settings across a reset.
    def reset(self):
        key, models = self.api_key, self.models
        super().reset()
        self.api_key, self.models = key, models

    # ---------- configuration ----------
    def configure(self, api_key: Optional[str]) -> None:
        self.api_key = (api_key or "").strip() or None

    @property
    def gemini_ready(self) -> bool:
        return bool(self.api_key) and genai is not None

    def status_text(self) -> str:
        if genai is None:
            return "⚠️ google-genai is not installed. Run: pip install google-genai"
        if not self.api_key:
            return "Offline mode: no API key, using the built-in calculator."
        if self.last_error:
            return f"⚠️ Last request fell back to offline mode ({self.last_error})."
        if self.last_model:
            return f"✅ Gemini connected ({self.last_model})."
        return "✅ API key found. Gemini will be used on your next message."

    # ---------- main loop ----------
    def run_step(self, user_prompt: str, files: Optional[List[Tuple[str, bytes]]] = None) -> Dict[str, Any]:
        text = (user_prompt or "").strip()
        files = files or []
        hist = self.memory["conversation_history"]
        fallback_reason = None

        if self.gemini_ready and not (text and _RULES_ONLY.search(text)):
            try:
                return self._run_gemini(text, files)
            except Exception as e:                     # network, quota, bad key, ...
                fallback_reason = _friendly_reason(e)
                self.last_error = fallback_reason
        elif genai is None and self.api_key:
            fallback_reason = "google-genai is not installed"

        # ----- offline path: original rule-based agent -----
        if not text:            # files only, nothing to parse
            trace = ["[Files] Saved attachment(s); offline mode cannot read file contents."]
            if fallback_reason:
                trace.append(f"[Fallback] Gemini unavailable ({fallback_reason}).")
            hist.append({"role": "user", "content": ""})
            hist.append({"role": "assistant", "content": FILE_NOTE, "trace": trace})
            return {"trace": trace, "response": FILE_NOTE, "files_read": False}

        result = super().run_step(text)
        if fallback_reason:
            note = f"⚠️ *Gemini unavailable ({fallback_reason}), so I answered with the built-in calculator.*"
            hist[-1]["content"] += "\n\n" + note
            hist[-1].setdefault("trace", []).insert(0, f"[Fallback] Gemini unavailable ({fallback_reason}).")
            result["response"] = hist[-1]["content"]
        result["files_read"] = False
        return result

    # ---------- Gemini path ----------
    def _run_gemini(self, text: str, files: List[Tuple[str, bytes]]) -> Dict[str, Any]:
        global _GOOD_MODEL
        client = genai.Client(api_key=self.api_key)
        order = [m for m in self.models if m not in _DEAD_MODELS]
        if _GOOD_MODEL in order:
            order.remove(_GOOD_MODEL)
            order.insert(0, _GOOD_MODEL)
        if not order:
            raise RuntimeError("no Gemini model available (404)")

        # tools mutate memory; snapshot everything except the history list (the UI holds it)
        snapshot = {k: copy.deepcopy(v) for k, v in self.memory.items() if k != "conversation_history"}
        notes: List[str] = []
        last_exc: Optional[Exception] = None

        for model in order:
            try:
                response, trace, files_read = self._attempt(client, model, text, files)
            except Exception as e:
                self.memory.update(snapshot)           # undo partial tool effects
                code = _err_code(e)
                if code == 404:
                    _DEAD_MODELS.add(model)
                if code in (404, 429, 500, 503):       # try the next model
                    notes.append(f"[Fallback] {model} unavailable ({_friendly_reason(e)}).")
                    last_exc = e
                    continue
                raise
            _GOOD_MODEL = model
            self.last_model, self.last_error = model, None
            trace = notes + trace
            hist = self.memory["conversation_history"]
            hist.append({"role": "user", "content": text})
            hist.append({"role": "assistant", "content": response, "trace": list(trace)})
            return {"trace": trace, "response": response, "files_read": files_read}

        raise last_exc or RuntimeError("Gemini request failed")

    def _attempt(self, client, model: str, text: str, files) -> Tuple[str, List[str], bool]:
        trace: List[str] = [f"[Plan] Gemini ({model}) is reading the request and choosing tools."]
        turn = {"assumed": [], "comp": None, "computed": False}

        contents = self._history_contents()
        user_parts, files_read = self._user_parts(text or DEFAULT_FILE_PROMPT, files, trace)
        contents.append(types.Content(role="user", parts=user_parts))

        config = types.GenerateContentConfig(
            system_instruction=self._system_prompt(),
            tools=[_build_tools()],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        final_text = ""
        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            cand = resp.candidates[0] if getattr(resp, "candidates", None) else None
            if cand is None or cand.content is None or not cand.content.parts:
                raise RuntimeError("empty response from Gemini")
            parts = cand.content.parts
            calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
            if not calls:
                final_text = "".join(p.text for p in parts
                                     if getattr(p, "text", None) and not getattr(p, "thought", False))
                break
            contents.append(cand.content)              # keep the model turn verbatim (thought signatures)
            replies = []
            for fc in calls:
                result = self._dispatch(fc.name, dict(fc.args or {}), trace, turn)
                replies.append(types.Part.from_function_response(name=fc.name, response={"result": result}))
            contents.append(types.Content(role="user", parts=replies))
        else:
            raise RuntimeError("too many tool rounds")

        # Guarantee a comparison whenever scenarios were computed this turn
        if turn["computed"] and turn["comp"] is None:
            self._dispatch("compare_options", {}, trace, turn)

        out: List[str] = []
        if turn["comp"] is not None and "error" not in turn["comp"]:
            out.append(self._format_comparison_response(turn["comp"], turn["assumed"]))
            if final_text.strip():
                out.append("**Advisor's note:** " + final_text.strip())
            if self.memory["no_income"]:
                out.append(self._no_income_note(text))
        else:
            out.append(final_text.strip() or "Done. I've updated your details.")
        return "\n\n".join(out), trace, files_read

    # ---------- tool execution ----------
    def _dispatch(self, name: str, args: Dict[str, Any], trace: List[str], turn: Dict[str, Any]) -> Dict[str, Any]:
        if name == "save_user_profile":
            inc = args.get("monthly_income")
            if inc and float(inc) > 0:
                self.set_income(float(inc))
                trace.append(f"[Memory Update] Stored monthly income: {inr(float(inc))}")
            if args.get("no_regular_income"):
                self.memory["no_income"] = True
                self.memory["monthly_income"] = None
                trace.append("[Memory Update] User has no regular income.")
            if args.get("no_credit_history"):
                self.memory["no_credit"] = True
                trace.append("[Memory Update] User has no credit history/score.")
            if args.get("credit_score"):
                self.memory["credit_score"] = int(args["credit_score"])
                self.memory["no_credit"] = False
                trace.append(f"[Memory Update] Stored credit score: {int(args['credit_score'])}")
            m = self.memory
            return {"saved": True, "monthly_income": m["monthly_income"], "no_regular_income": m["no_income"],
                    "no_credit_history": m["no_credit"], "credit_score": m["credit_score"]}

        if name == "compute_emi":
            try:
                amount, rate, months = float(args["amount"]), float(args["rate_annual"]), int(round(float(args["months"])))
            except (KeyError, TypeError, ValueError):
                return {"error": "amount, rate_annual and months are required numbers."}
            if not (1000 <= amount <= 1e10 and 0 <= rate <= 60 and 1 <= months <= 480):
                return {"error": "Unrealistic values: amount must be 1,000 to 10 billion, rate 0-60%, tenure 1-480 months."}
            if args.get("new_comparison"):
                self.memory["computed_options"].clear()
                trace.append("[Memory Update] New loan amount -> started a fresh comparison.")
            res = self.execute_tool("compute_emi", {"amount": amount, "rate_annual": rate, "months": months})
            if "error" in res:
                return res
            self.memory["last_request"] = {"amount": amount, "rate": rate, "months": months}
            turn["computed"], turn["comp"] = True, None      # force a fresh comparison afterwards
            if args.get("assumptions") and args["assumptions"] not in turn["assumed"]:
                turn["assumed"].append(str(args["assumptions"]))
            trace.append(f"[Tool Call] compute_emi({inr(amount)}, {rate}%, {months}m) -> EMI {inr(res['emi'])}")
            return res

        if name == "compare_options":
            comp = self.execute_tool("compare_options", {"monthly_income": self.memory["monthly_income"]})
            turn["comp"] = comp
            if "error" in comp:
                trace.append("[Tool Call] compare_options() -> no stored options.")
                return comp
            trace.append("[Tool Call] compare_options() executed.")
            return self._summarize_comparison(comp)

        if name == "estimate_eligibility":
            income = args.get("monthly_income") or self.memory["monthly_income"]
            if not income:
                return {"error": "Monthly income is not known yet."}
            income = float(income)
            max_emi = income * AFFORDABILITY_LIMIT / 100
            r, n = DEFAULT_RATE / 100 / 12, DEFAULT_MONTHS
            f = (1 + r) ** n
            principal = max_emi * (f - 1) / (r * f)
            trace.append(f"[Tool Call] estimate_eligibility({inr(income)}) -> max EMI {inr(max_emi)}")
            return {"monthly_income": income, "max_safe_emi": round(max_emi, 2),
                    "assumed_rate": DEFAULT_RATE, "assumed_months": n, "approx_max_loan": round(principal, 2)}

        return {"error": f"Unknown tool: {name}"}

    @staticmethod
    def _summarize_comparison(comp: Dict[str, Any]) -> Dict[str, Any]:
        opts = []
        for i, e in enumerate(comp["compared_options"], 1):
            d = e["loan_details"]
            opts.append({"option": i, "amount": d["amount"], "rate_annual": d["rate_annual"], "months": d["months"],
                         "emi": d["emi"], "total_interest": d["total_interest"], "affordable": e["affordable"],
                         "note": e["note"]})
        rec = comp["recommended_index"]
        return {"options": opts, "recommended_option": None if rec is None else rec + 1,
                "lowest_interest_option": comp["lowest_interest_index"] + 1,
                "lowest_emi_option": comp["lowest_emi_index"] + 1, "status": comp["status"],
                "note": "The app already shows the user a full comparison table; do not repeat it."}

    # ---------- prompt building ----------
    def _system_prompt(self) -> str:
        m = self.memory
        opts = "; ".join(
            f"#{i} {inr(o['amount'])} @ {o['rate_annual']}% for {o['months']}m -> EMI {inr(o['emi'])}"
            for i, o in enumerate(m["computed_options"], 1)) or "none"
        inc = inr(m["monthly_income"]) if m["monthly_income"] else "not provided"
        return f"""You are the EMI & Loan Advisor, a friendly assistant for Indian borrowers.

SCOPE: loans, EMI, affordability, credit score, eligibility, prepayment, documents. Politely decline unrelated topics.

RULES
- Never calculate EMI or interest yourself. Always use the tools; they are exact.
- When the user states income, no income, no credit history or a credit score, call save_user_profile.
- Convert Indian formats: 5 lakh = 500000, 1 crore = 10000000, 80k = 80000; years -> months.
- If the rate or tenure is missing, assume {DEFAULT_RATE}% and {DEFAULT_MONTHS} months, and pass that in `assumptions`.
- For each scenario call compute_emi; use new_comparison=true on the first scenario of a NEW loan amount. Then call compare_options.
- If the user only changes rate or tenure, reuse the last loan amount from memory.
- Affordability rule: EMI should be at most {AFFORDABILITY_LIMIT:.0f}% of monthly income.
- After compare_options, the app shows the comparison table itself. Reply with 2-4 short, personal sentences (why the recommended option fits, the interest trade-off). Do not repeat the table.
- For general loan questions, answer clearly and briefly. This is educational guidance, not regulated financial advice.
- If a document is attached (salary slip, offer letter), state what you read from it, then use the tools.
- If the user has no regular income, mention a co-applicant, collateral or other income proof.

CURRENT MEMORY
- monthly income: {inc}
- no regular income: {m['no_income']}; no credit history: {m['no_credit']}; credit score: {m['credit_score'] or 'not provided'}
- stored loan scenarios: {opts}"""

    def _history_contents(self):
        out = []
        for msg in self.memory["conversation_history"][-HISTORY_TURNS:]:
            txt = (msg.get("content") or "").strip()
            if not txt:
                continue
            if msg["role"] == "assistant":
                txt = txt[:1500]
            out.append(types.Content(role="user" if msg["role"] == "user" else "model",
                                     parts=[types.Part(text=txt)]))
        while out and out[0].role != "user":
            out.pop(0)
        return out

    @staticmethod
    def _user_parts(text: str, files, trace: List[str]):
        parts = [types.Part(text=text)]
        sent = 0
        for name, data in files:
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            if len(data) > MAX_FILE_BYTES:
                trace.append(f"[Files] Skipped {name}: larger than 15 MB.")
                continue
            if mime.startswith("image/") or mime == "application/pdf":
                parts.append(types.Part.from_bytes(data=data, mime_type=mime))
            elif mime.startswith("text/") or name.lower().endswith((".txt", ".csv")):
                body = data.decode("utf-8", errors="replace")[:20000]
                parts.append(types.Part(text=f"[Attached file: {name}]\n{body}"))
            else:
                trace.append(f"[Files] Skipped {name}: unsupported type.")
                continue
            sent += 1
        if sent:
            trace.append(f"[Files] Sent {sent} attachment(s) to Gemini for reading.")
        return parts, sent > 0
