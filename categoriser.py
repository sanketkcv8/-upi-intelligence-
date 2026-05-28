# categoriser.py
# --------------
# Labels every transaction with:
#   - category    (Food & Dining, Groceries, Transport, ...)
#   - subcategory (e.g. "Food Delivery" under Food & Dining)
#   - merchant    (cleaned merchant name, e.g. "Swiggy")
#
# HOW IT WORKS:
# We batch transactions (50 at a time) and ask Claude to label them all
# in one API call. This is fast and cheap — one call per ~50 transactions.
#
# We give Claude the full category list + Indian UPI merchant context
# so it correctly identifies "UPI/Zepto" as Groceries, not Others.

import json
import re
import anthropic
from config import ANTHROPIC_MODEL, CATEGORY_NAMES


def categorise_transactions(transactions: list) -> list:
    """
    Categorise all transactions using Claude.
    Batches 50 at a time to minimise API calls.

    Returns the same list with category, subcategory, merchant added.
    """
    if not transactions:
        return []

    results = []
    batch_size = 50

    for i in range(0, len(transactions), batch_size):
        batch = transactions[i : i + batch_size]
        labelled = _categorise_batch(batch)
        results.extend(labelled)

    return results


def _categorise_batch(batch: list) -> list:
    """Send a batch of transactions to Claude for labelling."""

    # Format transactions as a simple numbered list for Claude
    tx_lines = "\n".join(
        f"{i+1}. [{t['type'].upper()}] ₹{t['amount']:.0f} — {t['description']}"
        for i, t in enumerate(batch)
    )

    categories_list = "\n".join(f"- {c}" for c in CATEGORY_NAMES)

    prompt = f"""
You are categorising Indian bank/UPI transactions.

CATEGORIES (pick exactly one per transaction):
{categories_list}

INDIAN CONTEXT you must know:
- Swiggy, Zomato, EatSure = Food & Dining
- Blinkit, Zepto, BigBasket, DMart, Swiggy Instamart = Groceries
- Ola, Uber, Rapido, IRCTC, Metro, Fastag, Petrol/BPCL/HPCL/IOCL = Transport
- Amazon, Flipkart, Myntra, Meesho, Nykaa, AJIO = Shopping
- Netflix, Hotstar, Spotify, Gaana, JioSaavn, BookMyShow, PVR, INOX = Entertainment
- Airtel, Jio, Vi, BSNL, electricity boards (BESCOM/MSEDCL/TATA POWER), gas, broadband = Utilities
- Apollo, 1mg, Netmeds, Practo, PharmEasy, hospitals, labs, doctors = Health
- Byju's, Unacademy, Coursera, Udemy, school/college fees = Education
- EMI, loan repayment, BNPL (Simpl, LazyPay, Slice) = EMI & Loans
- LIC, insurance premiums, policy payments = Insurance
- Groww, Zerodha, Kuvera, SIP, mutual fund, NPS, PPF, stocks = Investments
- UPI P2P transfers to a person's name (not a merchant) = Transfers
- ATM withdrawal, cash deposit = Cash
- SALARY, salary credit, refund, cashback received = Income
- Anything else = Others

TRANSACTIONS:
{tx_lines}

Return ONLY a JSON array (no markdown, no explanation) with one object per transaction:
[
  {{
    "index": 1,
    "category": "Food & Dining",
    "subcategory": "Food Delivery",
    "merchant": "Swiggy"
  }},
  ...
]

subcategory should be a short descriptive label (2–3 words).
merchant should be the clean brand/merchant name only (no UPI/ prefix, no amount).
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        labels = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        labels = json.loads(match.group()) if match else []

    # Map labels back to transactions
    label_map = {item["index"]: item for item in labels}

    labelled = []
    for i, tx in enumerate(batch):
        label = label_map.get(i + 1, {})
        labelled.append({
            **tx,
            "category":    label.get("category",    "Others"),
            "subcategory": label.get("subcategory", ""),
            "merchant":    label.get("merchant",    ""),
        })

    return labelled
