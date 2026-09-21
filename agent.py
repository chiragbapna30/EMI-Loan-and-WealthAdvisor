import math
import re
from typing import List, Dict, Any, Optional

# =====================================================================
# CONFIG
# =====================================================================
AFFORDABILITY_LIMIT = 40.0   # EMI should be <= 40% of monthly income
DEFAULT_RATE = 10.5          # assumed annual rate (%) when user gives none
DEFAULT_MONTHS = 60          # assumed tenure when user gives none


# =====================================================================
# HELPERS
# =====================================================================
def inr(n: float) -> str:
    """Format a number in Indian digit grouping: 2000000 -> ₹20,00,000"""
    n = int(round(n))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"₹{sign}{s}"


def fmt_tenure(months: int) -> str:
    if months % 12 == 0:
        return f"{months // 12} yr ({months}m)"
    return f"{months}m"


# =====================================================================
# 1. TOOLS
# =====================================================================
def compute_emi(amount: float, rate_annual: float, months: int) -> Dict[str, Any]:
    """Monthly EMI, total payment and total interest."""
    if months <= 0 or amount <= 0:
        return {"error": "Amount and months must be greater than 0."}
    if rate_annual < 0:
        return {"error": "Interest rate cannot be negative."}

    r = (rate_annual / 100) / 12
    if r == 0:
        emi = amount / months
        total_payment = amount
        total_interest = 0.0
    else:
        f = math.pow(1 + r, months)
        emi = amount * r * f / (f - 1)
        total_payment = emi * months
        total_interest = total_payment - amount

    return {
        "amount": round(amount, 2),
        "rate_annual": rate_annual,
        "months": months,
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
    }


def compare_options(options: List[Dict[str, Any]], monthly_income: Optional[float] = None) -> Dict[str, Any]:
    """
    Compares EMI options. Applies the 40% income rule (if income known),
    and reports the income required for each option.
    Recommended = affordable option with the LOWEST TOTAL INTEREST.
    """
    if not options:
        return {"error": "No options provided for comparison."}

    have_income = bool(monthly_income and monthly_income > 0)
    evaluated = []
    for opt in options:
        emi = opt.get("emi", 0)
        required_income = emi / (AFFORDABILITY_LIMIT / 100)
        if have_income:
            ratio = emi / monthly_income * 100
            affordable = ratio <= AFFORDABILITY_LIMIT
            note = f"{ratio:.1f}% of income - " + (
                f"affordable (≤{AFFORDABILITY_LIMIT:.0f}%)" if affordable else f"too high (>{AFFORDABILITY_LIMIT:.0f}%)"
            )
        else:
            affordable = None
            note = f"Needs income ≥ {inr(required_income)}/month"
        evaluated.append({
            "loan_details": opt,
            "affordable": affordable,
            "required_income": round(required_income, 2),
            "note": note,
        })

    idx_interest = min(range(len(options)), key=lambda i: options[i]["total_interest"])
    idx_emi = min(range(len(options)), key=lambda i: options[i]["emi"])
    affordable_idx = [i for i, e in enumerate(evaluated) if e["affordable"]]
    idx_rec = min(affordable_idx, key=lambda i: options[i]["total_interest"]) if affordable_idx else None

    if not have_income:
        status = "no_income"
    elif idx_rec is None:
        status = "none_affordable"
    else:
        status = "ok"

    return {
        "compared_options": evaluated,
        "lowest_interest_index": idx_interest,
        "lowest_emi_index": idx_emi,
        "recommended_index": idx_rec,
        "status": status,
    }


TOOLS_SCHEMA = [
    {
        "name": "compute_emi",
        "description": "Calculate EMI, total interest, and total payment for a specific loan offer.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Principal loan amount"},
                "rate_annual": {"type": "number", "description": "Annual interest rate percentage (e.g., 8.5)"},
                "months": {"type": "integer", "description": "Loan tenure in months"},
            },
            "required": ["amount", "rate_annual", "months"],
        },
    },
    {
        "name": "compare_options",
        "description": "Compares calculated loan options and checks affordability against monthly income.",
        "parameters": {
            "type": "object",
            "properties": {
                "options": {"type": "array", "description": "List of dicts from compute_emi", "items": {"type": "object"}},
                "monthly_income": {"type": "number", "description": "User's monthly income"},
            },
            "required": ["options"],
        },
    },
]


# =====================================================================
# 2. KNOWLEDGE BASE
# =====================================================================
KB = {
    "what_is_loan": """A **loan** is money borrowed from a bank/NBFC/individual that you repay with interest over an agreed period.

* **Principal:** the amount borrowed
* **Interest rate:** the lender's charge for lending
* **Tenure:** how long you have to repay
* **EMI:** the fixed monthly payment (part principal, part interest)""",

    "types": """Main types of loans:

* **Personal loan:** unsecured; for emergencies, travel, weddings etc.
* **Home loan:** secured by the property; for buying/constructing a house.
* **Auto loan:** secured by the vehicle.
* **Education loan:** for tuition and study expenses (usually needs a co-borrower).
* **Business loan:** for working capital, expansion or equipment.
* **Gold loan / Loan against FD or property:** secured loans where approval depends mostly on the asset.""",

    "what_is_emi": """**EMI (Equated Monthly Instalment)** is the fixed amount you pay every month until the loan is cleared.

Formula: `EMI = P × r × (1+r)^n / ((1+r)^n − 1)` where P = principal, r = monthly rate (annual rate ÷ 12 ÷ 100), n = number of months.

A longer tenure means a lower EMI but **more total interest**.""",

    "credit_score": """A **credit score** (300-900 in India, e.g. CIBIL) summarises how reliably you repay credit.

* 750+ is generally considered good and gets better rates
* 650-750 is average; approval possible but at higher rates
* Below 650 makes approval harder

To improve it: pay EMIs and card bills on time, keep card usage under ~30% of the limit, avoid many loan applications in a short time, and don't close your oldest account.""",

    "no_income": """**Getting a loan with no job / no salary**

Lenders approve loans based on your ability to repay, so with no income you usually can't get a large loan on your own. Realistic options:

* **Add a co-applicant or guarantor** with stable income (parent, spouse). Their income and credit score are assessed.
* **Offer collateral:** gold loan, loan against FD/mutual funds/property. Approval then depends on the asset's value more than your income.
* **Show other income:** freelance work, rent, interest/dividends or family-business income with bank statements/ITR.
* **Purpose-specific loans:** an education loan (parent as co-borrower), or business schemes like MUDRA/PMEGP if you're starting a business (you need a project plan).
* **Ask for less:** a smaller, secured loan is far easier than a big unsecured one.

Avoid "instant loan, no documents" apps that ask for an upfront fee, as these are common scams.""",

    "no_credit": """**No credit score / no credit history**

This is called being *new to credit*. It isn't an automatic rejection, but lenders have nothing to judge you on, so they lean on income, a co-applicant or collateral.

To build a score:
* Get a **secured credit card** against a fixed deposit
* Take a small credit-builder loan or a phone/consumer EMI and repay on time
* Pay all bills on time and keep card usage low
* Your first score typically appears after about 3-6 months of reported activity

You can check your score and report free once a year with the credit bureaus (CIBIL, Experian, Equifax, CRIF).""",

    "reduce_interest": """Ways to reduce the interest you pay:

* Pick the **shortest tenure** whose EMI you can comfortably afford
* Make **part-prepayments** whenever you have spare cash
* Improve your credit score (750+) and negotiate the rate
* Compare offers from several lenders, including processing fees
* Add a co-applicant with a strong profile or provide collateral (lower rate)""",

    "prepayment": """**Prepayment / foreclosure** means paying part or all of the loan early.

* Part-prepayment reduces principal, so it cuts interest (and either EMI or tenure)
* Floating-rate loans for individuals in India generally have no prepayment penalty; fixed-rate loans may charge a fee, so check your loan agreement""",

    "fixed_floating": """* **Fixed rate:** stays the same for the tenure, so it's predictable but usually a bit higher.
* **Floating rate:** linked to a benchmark, so it can go up or down, and is usually lower at the start.""",

    "documents": """Typical documents for a loan:

* **KYC:** Aadhaar, PAN, address proof, photo
* **Income proof:** salary slips (3 months), bank statements (6 months), Form 16/ITR
* **Self-employed:** ITR, business proof, GST returns
* **Secured loans:** property/vehicle/gold documents

Process: check eligibility → compare offers → apply → document verification → credit check → sanction → disbursal.""",
}

LOAN_WORDS = ["loan", "emi", "interest", "principal", "borrow", "lender", "tenure", "salary", "income",
              "credit", "cibil", "afford", "rate", "bank", "lakh", "lkh", "crore", "job", "working"]

# =====================================================================
# 3. MESSAGE PARSING
# =====================================================================
NUM_RE = re.compile(
    r"(?<!\w)(\d+(?:,\d+)*(?:\.\d+)?)(?!\d)\s*"
    r"(%|per\s*cent|lakhs?|lkhs?|lacs?|lks?|crores?|crs?|thousand|k|"
    r"years?|yrs?|months?|mths?|mos?|yr|y|m|l)?(?![a-z])",
    re.IGNORECASE,
)
LAKH = {"l", "lakh", "lakhs", "lkh", "lkhs", "lac", "lacs", "lk", "lks"}
CRORE = {"cr", "crs", "crore", "crores"}
THOUSAND = {"k", "thousand"}
YEARS = {"y", "yr", "yrs", "year", "years"}
MONTHS = {"m", "mth", "mths", "mo", "mos", "month", "months"}

NO_INCOME_RE = re.compile(
    r"not working|not employed|unemployed|jobless|no job|no salary|no income|no regular income|"
    r"no work|not earning|don'?t work|homemaker|housewife|"
    r"(?:don'?t|do not|dont) have (?:a |any )?(?:job|salary|income)|"
    r"without\b[^.?!]{0,40}\b(?:salary|income|job)", re.I)
NO_CREDIT_RE = re.compile(
    r"(?:without|no|zero|don'?t have|dont have|do not have|not have)\s+(?:a\s+|any\s+)?(?:credit|cibil)|"
    r"without\b[^.?!]{0,40}\b(?:credit|cibil)|new to credit|no credit|"
    r"(?:credit|cibil)\s*(?:score|history)?\s*(?:is\s+)?(?:zero|nil|not there)|never taken (?:a )?(?:loan|credit)", re.I)
INCOME_BEFORE_RE = re.compile(r"(income|salary|earn|earning|earns|ctc|stipend|\bi make\b)", re.I)
INCOME_AFTER_RE = re.compile(r"\s*(per month|a month|/\s*month|monthly|p\.?m\b|salary|income)", re.I)


def parse_message(text: str) -> Dict[str, Any]:
    """Extract amount, rate(s), tenure(s), income, credit score and status flags."""
    clean = re.sub(r"₹|\b(?:rs|inr)\.?\s*", " ", text, flags=re.I)
    low = clean.lower()
    out: Dict[str, Any] = {"rates": [], "months": []}
    prev_end = 0

    for m in NUM_RE.finditer(clean):
        val = float(m.group(1).replace(",", ""))
        unit = re.sub(r"\s+", "", (m.group(2) or "").lower())
        before = low[max(prev_end, m.start() - 45):m.start()]
        after = low[m.end():m.end() + 18]
        prev_end = m.end()

        if unit in ("%", "percent"):
            out["rates"].append(val)
            continue
        if unit in YEARS:
            out["months"].append(int(round(val * 12)))
            continue
        if unit in MONTHS:
            out["months"].append(int(round(val)))
            continue

        mult = 1
        if unit in LAKH:
            mult = 1e5
        elif unit in CRORE:
            mult = 1e7
        elif unit in THOUSAND:
            mult = 1e3
        value = val * mult
        is_income_ctx = bool(INCOME_BEFORE_RE.search(before) or INCOME_AFTER_RE.match(after))

        if mult == 1:  # plain number, decide from context
            if re.search(r"(credit|cibil|score)", before) and 300 <= val <= 900:
                out["credit_score"] = val
            elif re.search(r"(rate|interest|roi)[^\d]*$", before) and val <= 40:
                out["rates"].append(val)
            elif re.search(r"(tenure|term|duration|period)[^\d]*$", before):
                out["months"].append(int(val * 12) if val <= 30 else int(val))
            elif is_income_ctx:
                out["income"] = value
            elif val >= 1000:
                out.setdefault("amount", value)
        else:
            if is_income_ctx:
                out["income"] = value
            else:
                out.setdefault("amount", value)

    out["no_income"] = bool(NO_INCOME_RE.search(low))
    out["no_credit"] = bool(NO_CREDIT_RE.search(low))
    return out


# =====================================================================
# 4. AGENT
# =====================================================================
class EMILoanAgent:
    def __init__(self, monthly_income: Optional[float] = None):
        self.memory = {
            "monthly_income": monthly_income,
            "no_income": False,
            "no_credit": False,
            "credit_score": None,
            "computed_options": [],
            "last_request": None,       # {"amount":..., "rate":...}
            "no_income_guidance_shown": False,
            "conversation_history": [],
        }

    # ---------- tool execution ----------
    def set_income(self, income: float):
        self.memory["monthly_income"] = income
        self.memory["no_income"] = False

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "compute_emi":
            res = compute_emi(args["amount"], args["rate_annual"], args["months"])
            if "error" not in res and res not in self.memory["computed_options"]:
                self.memory["computed_options"].append(res)
            return res
        if tool_name == "compare_options":
            income = args.get("monthly_income", self.memory["monthly_income"])
            options = args.get("options", self.memory["computed_options"])
            return compare_options(options=options, monthly_income=income)
        return {"error": f"Unknown tool: {tool_name}"}

    def reset(self):
        self.__init__()

    # ---------- main loop ----------
    def run_step(self, user_prompt: str) -> Dict[str, Any]:
        trace: List[str] = []
        text = user_prompt.strip()
        low = text.lower()
        hist = self.memory["conversation_history"]
        hist.append({"role": "user", "content": text})

        def finish(resp: str) -> Dict[str, Any]:
            hist.append({"role": "assistant", "content": resp, "trace": list(trace)})
            return {"trace": trace, "response": resp}

        # --- reset / greeting / thanks ---
        if re.search(r"\b(reset|start over|clear memory|new session)\b", low):
            self.reset()
            self.memory["conversation_history"] = hist
            trace.append("[Memory] Cleared income, options and loan details.")
            return finish("Memory cleared. Tell me the loan amount you need (e.g. *'I need a loan of 20 lakh'*).")
        if re.match(r"^(hi|hii+|hello|hey|namaste|good (morning|afternoon|evening))\b[\s!.]*$", low):
            trace.append("[Plan] Greeting.")
            return finish("Hello! I'm your **EMI & Loan Advisor**. Tell me a loan amount, rate and tenure "
                          "(e.g. *'10 lakh at 9% for 5 years'*), share your income, or ask any loan question.")
        if re.match(r"^(thanks?|thank you|ok(ay)?|great|cool)\b[\s!.]*$", low):
            return finish("You're welcome! Ask me anything else about loans or EMIs.")

        # --- extract & update memory ---
        p = parse_message(text)
        trace.append(f"[Parse] amount={p.get('amount')}, rates={p['rates']}, months={p['months']}, "
                     f"income={p.get('income')}, no_income={p['no_income']}, no_credit={p['no_credit']}")

        if p.get("income"):
            self.set_income(p["income"])
            trace.append(f"[Memory Update] Stored monthly income: {inr(p['income'])}")
        elif p["no_income"]:
            self.memory["no_income"] = True
            self.memory["monthly_income"] = None
            trace.append("[Memory Update] User has no regular income.")
        if p["no_credit"]:
            self.memory["no_credit"] = True
            trace.append("[Memory Update] User has no credit history/score.")
        if p.get("credit_score"):
            self.memory["credit_score"] = p["credit_score"]
            self.memory["no_credit"] = False
            trace.append(f"[Memory Update] Stored credit score: {int(p['credit_score'])}")

        parts: List[str] = []
        income = self.memory["monthly_income"]
        last = self.memory["last_request"]

        # --- decide whether this is a calculation request ---
        amount = p.get("amount")
        rates, months_list = p["rates"], p["months"]
        specs = None
        assumed = []
        if amount is not None:
            rate = rates[0] if rates else None
            months = months_list[0] if months_list else None
            if rate is None:
                rate = DEFAULT_RATE
                assumed.append(f"interest rate {DEFAULT_RATE}%")
            if months is None:
                months = DEFAULT_MONTHS
                assumed.append(f"tenure {fmt_tenure(DEFAULT_MONTHS)}")
            if len(months_list) > 1:
                specs = [(amount, rate, mo) for mo in months_list]
            elif len(rates) > 1:
                specs = [(amount, rt, months) for rt in rates]
            else:
                specs = [(amount, rate, months)]
        elif last and (rates or months_list):
            amount = last["amount"]
            if len(months_list) > 1:
                specs = [(amount, rates[0] if rates else last["rate"], mo) for mo in months_list]
            elif len(rates) > 1:
                specs = [(amount, rt, months_list[0] if months_list else last["months"]) for rt in rates]
            else:
                specs = [(amount, rates[0] if rates else last["rate"],
                          months_list[0] if months_list else last["months"])]
            trace.append(f"[Memory Use] Re-using earlier loan amount {inr(amount)}.")

        # --- Path A: calculation ---
        if specs:
            bad = [s for s in specs if not (1000 <= s[0] <= 1e10 and 0 <= s[1] <= 60 and 1 <= s[2] <= 480)]
            if bad:
                return finish("Those numbers look unusual. Please give an amount (e.g. *20 lakh*), "
                              "an annual rate between 0-60% and a tenure up to 40 years.")
            trace.append("[Plan] Calculation request -> compute_emi for each scenario, then compare_options.")
            if last and abs(last["amount"] - specs[0][0]) > 0.01:
                self.memory["computed_options"].clear()
                trace.append("[Memory Update] New loan amount -> started a fresh comparison.")
            for a, rt, mo in specs:
                res = self.execute_tool("compute_emi", {"amount": a, "rate_annual": rt, "months": mo})
                trace.append(f"[Tool Call] compute_emi({inr(a)}, {rt}%, {mo}m) -> EMI {inr(res['emi'])}")
            self.memory["last_request"] = {"amount": specs[-1][0], "rate": specs[-1][1], "months": specs[-1][2]}
            comp = self.execute_tool("compare_options", {"monthly_income": income})
            trace.append("[Tool Call] compare_options() executed.")
            parts.append(self._format_comparison_response(comp, assumed))

            if self.memory["no_income"] or p["no_income"]:
                parts.append(self._no_income_note(text))
            elif income is None:
                parts.append("💡 *Tell me your monthly income and I'll check whether this EMI is affordable.*")
            return finish("\n\n".join(parts))

        # --- Path B: knowledge / guidance topics ---
        topics = self._detect_topics(low, p)
        if topics:
            trace.append(f"[Plan] Conversational request -> topics: {', '.join(topics)}")
            for t in topics:
                if t == "eligibility":
                    parts.append(self._eligibility_answer(income))
                elif t == "no_income":
                    parts.append(KB["no_income"])
                    self.memory["no_income_guidance_shown"] = True
                else:
                    parts.append(KB[t])
            if last and ("no_income" in topics or "no_credit" in topics):
                parts.append(f"*Your earlier request was for {inr(last['amount'])}. Once you have a co-applicant, "
                             f"collateral or income, share the details and I'll recompute the EMI.*")
            return finish("\n\n".join(parts))

        # --- Path C: compare / affordability on stored options ---
        wants_compare = re.search(r"compare|afford|which (one )?is (better|best)|recommend|best option|suitable|can i", low)
        if self.memory["computed_options"] and (wants_compare or p.get("income")):
            trace.append("[Plan] Evaluating stored options against current income.")
            comp = self.execute_tool("compare_options", {"monthly_income": income})
            trace.append("[Tool Call] compare_options() executed.")
            parts.append(self._format_comparison_response(comp, []))
            return finish("\n\n".join(parts))

        # --- Path D: income/credit info only, no loan yet ---
        if p.get("income") or p["no_income"] or p["no_credit"] or p.get("credit_score"):
            trace.append("[Plan] Profile info received; loan details still missing.")
            if p.get("income"):
                parts.append(f"Got it, I've noted your monthly income as **{inr(p['income'])}**.")
                parts.append(self._eligibility_answer(p["income"]))
            if p["no_income"]:
                parts.append(KB["no_income"])
            if p["no_credit"]:
                parts.append(KB["no_credit"])
            if p.get("credit_score"):
                parts.append(f"Noted your credit score of **{int(p['credit_score'])}**.")
            parts.append("What loan amount do you need? (e.g. *'20 lakh at 9% for 5 years'*)")
            return finish("\n\n".join(parts))

        # --- Fallbacks ---
        is_loan = any(w in low for w in LOAN_WORDS)
        if is_loan:
            trace.append("[Plan] Loan-related but details missing -> ask user.")
            return finish("I need a few details to help. Please tell me:\n\n"
                          "* the **loan amount** (e.g. *20 lakh*)\n"
                          "* optionally the **interest rate** and **tenure** (I'll assume "
                          f"{DEFAULT_RATE}% and {DEFAULT_MONTHS // 12} years if you don't say)\n"
                          "* your **monthly income**, so I can check affordability\n\n"
                          "You can also ask things like *'what is EMI?'*, *'types of loans'*, or *'how to improve credit score?'*")
        trace.append("[Plan] Non-financial query -> reject gracefully.")
        return finish("I'm a specialised **EMI & Loan Advisor**. I can calculate EMIs, check affordability, "
                      "compare tenures and explain loan concepts. Please ask a loan-related question!")

    # ---------- helpers ----------
    def _detect_topics(self, low: str, p: Dict[str, Any]) -> List[str]:
        t: List[str] = []
        if self.memory["no_income"] and (p["no_income"] or re.search(r"how|process|option|possible|apply|get|help|can i", low)):
            t.append("no_income")
        if p["no_credit"] and (re.search(r"how|process|option|possible|apply|get|help|can i|without", low) or True):
            t.append("no_credit")
        if re.search(r"eligib|qualify|how much (loan )?(can|could|will) i|max(imum)? loan|loan i can (get|take)", low):
            if "no_income" not in t:
                t.append("eligibility")
        if re.search(r"what (is|are) (a |an )?loans?\b|define loan|meaning of loan|explain loan", low):
            t.append("what_is_loan")
        if re.search(r"types? of loans?|kinds? of loans?|different loans?|loan types?", low):
            t.append("types")
        if re.search(r"what (is|are) (an? )?emis?\b|emi mean|how (is|does) emi|emi formula|explain emi", low):
            t.append("what_is_emi")
        if re.search(r"(credit|cibil)", low) and not p["no_credit"] and not p.get("credit_score") \
                and re.search(r"what|how|improve|build|increase|check|minimum|why|important", low):
            t.append("credit_score")
        if re.search(r"(reduce|lower|cut|save|less|minimi[sz]e)\b.*interest|interest.*(reduce|lower|less|save)", low):
            t.append("reduce_interest")
        if re.search(r"prepay|foreclos|part.?payment|pre-?close", low):
            t.append("prepayment")
        if re.search(r"fixed.*floating|floating.*fixed|fixed rate|floating rate", low):
            t.append("fixed_floating")
        if not t and re.search(r"document|paperwork|kyc|procedure|how (can|do) i (get|apply|process)|apply for", low):
            t.append("documents")
        # de-duplicate, keep order
        return list(dict.fromkeys(t))

    def _eligibility_answer(self, income: Optional[float]) -> str:
        if not income:
            return "To estimate how much you can borrow, please tell me your **monthly income**."
        max_emi = income * AFFORDABILITY_LIMIT / 100
        r = DEFAULT_RATE / 100 / 12
        n = DEFAULT_MONTHS
        f = math.pow(1 + r, n)
        principal = max_emi * (f - 1) / (r * f)
        return (f"With a monthly income of **{inr(income)}**, a safe EMI is up to **{inr(max_emi)}** "
                f"({AFFORDABILITY_LIMIT:.0f}% rule). At an assumed {DEFAULT_RATE}% for {n // 12} years, "
                f"that supports a loan of roughly **{inr(principal)}**. Actual eligibility depends on your "
                f"credit score, existing EMIs and the lender.")

    def _no_income_note(self, text: str) -> str:
        if not self.memory["no_income_guidance_shown"] or re.search(r"how|process|option|possible|can i", text.lower()):
            self.memory["no_income_guidance_shown"] = True
            return "⚠️ **Since you mentioned you're not working:**\n\n" + KB["no_income"]
        return "⚠️ *Reminder: with no income, lenders will need a co-applicant, collateral or other income proof.*"

    def _format_comparison_response(self, comp: Dict[str, Any], assumed: List[str]) -> str:
        opts = comp["compared_options"]
        out = "### EMI & Loan Recommendation Summary\n\n"
        if assumed:
            out += f"*Assumed (you didn't specify): {', '.join(assumed)}. Tell me the actual values and I'll recalculate.*\n\n"
        out += "| Option | Amount | Tenure | Rate | EMI | Total Interest | Total Payable | Affordability |\n"
        out += "|---|---|---|---|---|---|---|---|\n"
        for i, item in enumerate(opts, 1):
            o = item["loan_details"]
            out += (f"| {i} | {inr(o['amount'])} | {fmt_tenure(o['months'])} | {o['rate_annual']}% | "
                    f"{inr(o['emi'])} | {inr(o['total_interest'])} | {inr(o['total_payment'])} | {item['note']} |\n")

        out += "\n**Analysis & Decision:**\n"
        li, le, rec = comp["lowest_interest_index"], comp["lowest_emi_index"], comp["recommended_index"]
        if comp["status"] == "ok":
            o = opts[rec]["loan_details"]
            out += (f"- **Recommended:** Option {rec + 1} (EMI {inr(o['emi'])}, {fmt_tenure(o['months'])} @ {o['rate_annual']}%). "
                    "It's the affordable option with the lowest total interest.\n")
        elif comp["status"] == "none_affordable":
            cheapest = opts[le]
            out += (f"- **None of these fit the {AFFORDABILITY_LIMIT:.0f}% rule.** The lowest EMI ({inr(cheapest['loan_details']['emi'])}) "
                    f"needs an income of about {inr(cheapest['required_income'])}/month. Try a smaller amount, longer tenure or a co-applicant.\n")
        else:
            out += "- **Affordability can't be judged yet** because income isn't known (see the last column for income needed).\n"

        if len(opts) > 1:
            if li != le:
                a, b = opts[le]["loan_details"], opts[li]["loan_details"]
                out += (f"- **Trade-off:** Option {le + 1} has the lowest EMI ({inr(a['emi'])}) but Option {li + 1} saves you "
                        f"{inr(a['total_interest'] - b['total_interest'])} in interest.\n")
            else:
                out += f"- Option {li + 1} has both the lowest EMI and the lowest total interest.\n"
        else:
            o = opts[0]["loan_details"]
            out += (f"- You'll repay **{inr(o['total_payment'])}** in total, of which **{inr(o['total_interest'])}** is interest.\n")
        return out
