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


def generate_amortization_schedule(amount: float, rate_annual: float, months: int) -> List[Dict[str, Any]]:
    """Generates a month-by-month payment schedule showing Principal vs Interest."""
    schedule = []
    r = (rate_annual / 100) / 12
    res = compute_emi(amount, rate_annual, months)
    if "error" in res:
        return []
    
    emi = res["emi"]
    balance = amount
    
    for month in range(1, months + 1):
        interest_payment = balance * r if r > 0 else 0
        principal_payment = emi - interest_payment
        balance = max(0.0, balance - principal_payment)
        
        schedule.append({
            "Month": month,
            "EMI": round(emi, 2),
            "Principal Paid": round(principal_payment, 2),
            "Interest Paid": round(interest_payment, 2),
            "Remaining Balance": round(balance, 2)
        })
    return schedule


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
