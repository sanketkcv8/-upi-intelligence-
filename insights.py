# insights.py
# -----------
# Uses Claude to generate personalised spending insights from categorised transactions.
#
# Claude doesn't just summarise — it finds patterns a human might miss:
# - "You spent 34% of your income on food, well above the 15% ideal"
# - "You have 4 active streaming subscriptions costing ₹2,066/month"
# - "Your grocery spend spiked 40% in March — possibly Holi shopping"
# - "You withdrew ₹12,000 cash with no visible spending pattern — consider going digital"

import anthropic
from config import ANTHROPIC_MODEL, CATEGORIES
from collections import defaultdict


def generate_insights(transactions: list, statement_meta: dict) -> str:
    """
    Generate rich spending insights from categorised transactions.

    Args:
        transactions:   List of categorised transactions
        statement_meta: {bank, period, account_holder}

    Returns:
        Plain-English insights as a formatted string
    """
    if not transactions:
        return "No transactions found to analyse."

    summary = _build_summary(transactions)
    prompt  = _build_prompt(summary, statement_meta)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


def _build_summary(transactions: list) -> dict:
    """
    Pre-aggregate the data before sending to Claude.
    Reduces tokens and gives Claude clean numbers to reason over.
    """
    debits  = [t for t in transactions if t["type"] == "debit"]
    credits = [t for t in transactions if t["type"] == "credit"]

    total_spent    = sum(t["amount"] for t in debits)
    total_income   = sum(t["amount"] for t in credits
                         if any(k in t["description"].lower()
                                for k in ["salary","neft cr","credit"]))

    # Category totals
    by_category = defaultdict(float)
    by_category_count = defaultdict(int)
    for t in debits:
        cat = t.get("category", "Others")
        by_category[cat]       += t["amount"]
        by_category_count[cat] += 1

    # Monthly breakdown
    by_month = defaultdict(float)
    for t in debits:
        month = t["date"][:7]  # YYYY-MM
        by_month[month] += t["amount"]

    # Top merchants
    by_merchant = defaultdict(float)
    for t in debits:
        m = t.get("merchant", "").strip()
        if m and m.lower() not in ("", "unknown", "upi"):
            by_merchant[m] += t["amount"]
    top_merchants = sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:10]

    # Subscriptions (recurring monthly charges)
    subscription_keywords = ["netflix","spotify","hotstar","prime","youtube",
                              "gaana","jiosaavn","zee5","sonyliv","airtel",
                              "jio","vi ","bsnl","amazon prime"]
    subscriptions = []
    seen_subs = set()
    for t in debits:
        desc_lower = t["description"].lower()
        for kw in subscription_keywords:
            if kw in desc_lower and kw not in seen_subs:
                subscriptions.append({
                    "name":   t.get("merchant") or kw.title(),
                    "amount": t["amount"],
                })
                seen_subs.add(kw)
                break

    # Large single transactions (top 5)
    large_txns = sorted(debits, key=lambda x: x["amount"], reverse=True)[:5]

    return {
        "total_spent":       round(total_spent, 2),
        "total_income":      round(total_income, 2),
        "savings":           round(total_income - total_spent, 2),
        "savings_rate":      round((total_income - total_spent) / total_income * 100, 1) if total_income > 0 else 0,
        "transaction_count": len(debits),
        "by_category":       dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "by_category_count": dict(by_category_count),
        "by_month":          dict(sorted(by_month.items())),
        "top_merchants":     top_merchants,
        "subscriptions":     subscriptions,
        "large_transactions":[(t["description"], t["amount"], t["date"]) for t in large_txns],
    }


def _build_prompt(summary: dict, meta: dict) -> str:
    name   = meta.get("account_holder", "the user")
    period = meta.get("period", "the statement period")
    bank   = meta.get("bank", "the bank")

    # Format category breakdown
    cat_lines = "\n".join(
        f"  {cat}: ₹{amt:,.0f} ({summary['by_category_count'].get(cat,0)} txns)"
        for cat, amt in summary["by_category"].items()
    )

    # Format monthly totals
    month_lines = "\n".join(
        f"  {month}: ₹{amt:,.0f}"
        for month, amt in summary["by_month"].items()
    )

    # Subscriptions
    sub_lines = "\n".join(
        f"  {s['name']}: ₹{s['amount']:,.0f}/month"
        for s in summary["subscriptions"]
    ) or "  None detected"

    # Top merchants
    merchant_lines = "\n".join(
        f"  {m}: ₹{a:,.0f}"
        for m, a in summary["top_merchants"]
    )

    return f"""
You are a personal finance advisor analysing Indian spending patterns.
Write a clear, friendly, and specific spending insights report for {name}.

STATEMENT: {bank} | {period}

FINANCIAL SUMMARY:
  Total income (credits):  ₹{summary['total_income']:,.0f}
  Total spent (debits):    ₹{summary['total_spent']:,.0f}
  Net savings:             ₹{summary['savings']:,.0f}
  Savings rate:            {summary['savings_rate']:.1f}%
  Total transactions:      {summary['transaction_count']}

SPENDING BY CATEGORY:
{cat_lines}

MONTHLY SPENDING:
{month_lines}

TOP MERCHANTS:
{merchant_lines}

ACTIVE SUBSCRIPTIONS DETECTED:
{sub_lines}

LARGE TRANSACTIONS (top 5):
{chr(10).join(f"  {d}: ₹{a:,.0f} on {dt}" for d, a, dt in summary["large_transactions"])}

YOUR TASK:
Write a personalised financial insights report with these sections:

1. **Overall picture** (2–3 sentences on income, spending, savings rate vs ideal 20–30%)

2. **Top 3 spending patterns** (specific observations — percentages, comparisons to benchmarks, trends across months)

3. **Subscriptions audit** (total monthly subscription cost, is it worth it?)

4. **3 actionable savings tips** (specific, with estimated monthly saving in ₹ per tip)

5. **What you're doing well** (1–2 genuine positives)

RULES:
- Use ₹ symbol for all amounts
- Be specific — use the actual numbers from the data
- Be friendly, not preachy
- Indian context — reference Indian spending norms
- Keep total length under 400 words
- Do NOT start with "Sure!" or "Certainly!"
"""
