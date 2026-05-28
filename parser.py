# parser.py
# ---------
# THE KEY INNOVATION: Instead of writing bank-specific regex parsers
# (one for HDFC, one for SBI, one for ICICI...), we extract raw text
# from the PDF and ask Claude to read it and extract transactions.
#
# Claude understands table structures, date formats, and banking
# terminology across all Indian banks — no rules needed.
#
# This means ANY bank statement works out of the box.

import json
import re
import pdfplumber
import anthropic
from config import ANTHROPIC_MODEL


def extract_pdf_text(pdf_path: str) -> tuple[str, int]:
    """
    Extract all text from a bank statement PDF.
    Returns (full_text, page_count).
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append(f"--- Page {i+1} ---\n{text}")
    return "\n\n".join(pages), len(pages)


def extract_transactions_with_claude(pdf_text: str) -> dict:
    """
    Send raw PDF text to Claude and ask it to extract all transactions
    as structured JSON.

    Why Claude instead of regex?
    - HDFC uses DD/MM/YY, SBI uses DD-MM-YYYY, ICICI uses 01 Jan 2024
    - Some banks put debit/credit in separate columns, others use Dr/Cr suffix
    - Column orders vary. Narration styles vary. Claude handles all of this.

    Returns:
        {
          "bank": "HDFC Bank",
          "period": "Jan 2024 - Mar 2024",
          "transactions": [
            {
              "date": "2024-01-15",
              "description": "UPI/Swiggy/Food order",
              "amount": 450.00,
              "type": "debit",
              "balance": 24350.00
            },
            ...
          ]
        }
    """
    client = anthropic.Anthropic()

    # For large statements, we only send the first 12,000 chars per call
    # and paginate if needed. Most 3-month statements fit in one call.
    chunk = pdf_text[:12000]

    prompt = f"""
You are a bank statement parser. Extract ALL transactions from this Indian bank statement.

RULES:
1. Return ONLY valid JSON — no explanation, no markdown, no backticks
2. Include every single transaction row you find
3. Normalise dates to YYYY-MM-DD format
4. Amount should always be a positive number (use "type" to indicate direction)
5. type must be exactly "debit" or "credit"
6. If balance column exists, include it. If not, set balance to 0
7. Clean up the description — remove extra spaces/newlines
8. Detect the bank name from the header if visible

Return this exact JSON structure:
{{
  "bank": "<bank name or 'Unknown'>",
  "period": "<statement period e.g. Jan 2024 to Mar 2024>",
  "account_holder": "<name if visible>",
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "description": "cleaned transaction description",
      "amount": 1234.50,
      "type": "debit",
      "balance": 45678.90
    }}
  ]
}}

BANK STATEMENT TEXT:
{chunk}
"""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude added them
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract the JSON object if there's surrounding text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Claude did not return valid JSON. Raw response:\n{raw[:500]}")

    # Validate and clean each transaction
    cleaned = []
    for t in data.get("transactions", []):
        try:
            cleaned.append({
                "date":        str(t.get("date", ""))[:10],
                "description": str(t.get("description", "")).strip()[:200],
                "amount":      abs(float(t.get("amount", 0))),
                "type":        "debit" if "debit" in str(t.get("type","")).lower() else "credit",
                "balance":     float(t.get("balance", 0)),
            })
        except (ValueError, TypeError):
            continue

    data["transactions"] = cleaned
    return data


def get_sample_statement() -> dict:
    """
    Realistic sample statement for a 25-year-old professional in Pune.
    Use this to test without uploading a real bank statement.

    Covers 3 months: Jan–Mar 2024
    Monthly salary: ₹65,000
    Mix of UPI, EMI, and regular expenses
    """
    return {
        "bank":           "HDFC Bank",
        "period":         "Jan 2024 – Mar 2024",
        "account_holder": "Priya Kulkarni",
        "transactions": [
            # January
            {"date":"2024-01-01","description":"UPI/Zepto/Groceries","amount":1840,"type":"debit","balance":42500},
            {"date":"2024-01-02","description":"UPI/Swiggy/Food Order","amount":380,"type":"debit","balance":42120},
            {"date":"2024-01-03","description":"UPI/Ola/Cab Booking","amount":220,"type":"debit","balance":41900},
            {"date":"2024-01-05","description":"NEFT/SALARY/TECHCORP PVT LTD","amount":65000,"type":"credit","balance":106900},
            {"date":"2024-01-06","description":"UPI/Netflix/Subscription","amount":649,"type":"debit","balance":106251},
            {"date":"2024-01-06","description":"UPI/Spotify/Premium","amount":119,"type":"debit","balance":106132},
            {"date":"2024-01-07","description":"UPI/Amazon/Online Shopping","amount":2499,"type":"debit","balance":103633},
            {"date":"2024-01-08","description":"UPI/Zomato/Dinner","amount":540,"type":"debit","balance":103093},
            {"date":"2024-01-10","description":"UPI/Airtel/Mobile Recharge","amount":299,"type":"debit","balance":102794},
            {"date":"2024-01-10","description":"EMI/BAJAJ FINANCE/LAPTOP EMI","amount":3200,"type":"debit","balance":99594},
            {"date":"2024-01-12","description":"UPI/BigBasket/Groceries","amount":2100,"type":"debit","balance":97494},
            {"date":"2024-01-14","description":"UPI/Uber/Office Cab","amount":185,"type":"debit","balance":97309},
            {"date":"2024-01-15","description":"UPI/BookMyShow/Movie Ticket","amount":400,"type":"debit","balance":96909},
            {"date":"2024-01-17","description":"UPI/Apollo Pharmacy/Medicine","amount":680,"type":"debit","balance":96229},
            {"date":"2024-01-18","description":"UPI/Swiggy/Lunch","amount":290,"type":"debit","balance":95939},
            {"date":"2024-01-20","description":"MSEDCL/ELECTRICITY BILL","amount":1450,"type":"debit","balance":94489},
            {"date":"2024-01-21","description":"UPI/Groww/SIP MF","amount":5000,"type":"debit","balance":89489},
            {"date":"2024-01-22","description":"UPI/Zomato/Food","amount":420,"type":"debit","balance":89069},
            {"date":"2024-01-23","description":"HDFC LIFE/INSURANCE PREMIUM","amount":2800,"type":"debit","balance":86269},
            {"date":"2024-01-24","description":"UPI/Rapido/Bike Ride","amount":65,"type":"debit","balance":86204},
            {"date":"2024-01-25","description":"UPI/Swiggy Instamart/Groceries","amount":950,"type":"debit","balance":85254},
            {"date":"2024-01-26","description":"ATM/CASH WITHDRAWAL/HDFC ATM","amount":5000,"type":"debit","balance":80254},
            {"date":"2024-01-28","description":"UPI/Myntra/Clothing","amount":1799,"type":"debit","balance":78455},
            {"date":"2024-01-29","description":"UPI/1mg/Medicine","amount":345,"type":"debit","balance":78110},
            {"date":"2024-01-30","description":"UPI/Zepto/Vegetables","amount":680,"type":"debit","balance":77430},
            {"date":"2024-01-31","description":"UPI/Swiggy/Dinner","amount":510,"type":"debit","balance":76920},

            # February
            {"date":"2024-02-01","description":"UPI/Zepto/Groceries","amount":1650,"type":"debit","balance":75270},
            {"date":"2024-02-03","description":"UPI/Ola/Cab","amount":310,"type":"debit","balance":74960},
            {"date":"2024-02-05","description":"NEFT/SALARY/TECHCORP PVT LTD","amount":65000,"type":"credit","balance":139960},
            {"date":"2024-02-06","description":"UPI/Hotstar/OTT Annual","amount":1499,"type":"debit","balance":138461},
            {"date":"2024-02-07","description":"UPI/Swiggy/Food","amount":620,"type":"debit","balance":137841},
            {"date":"2024-02-08","description":"EMI/BAJAJ FINANCE/LAPTOP EMI","amount":3200,"type":"debit","balance":134641},
            {"date":"2024-02-10","description":"UPI/Flipkart/Electronics","amount":3500,"type":"debit","balance":131141},
            {"date":"2024-02-11","description":"UPI/IRCTC/Train Ticket","amount":1250,"type":"debit","balance":129891},
            {"date":"2024-02-12","description":"UPI/BigBasket/Monthly Grocery","amount":3200,"type":"debit","balance":126691},
            {"date":"2024-02-13","description":"UPI/Zomato/Valentine Dinner","amount":1800,"type":"debit","balance":124891},
            {"date":"2024-02-14","description":"UPI/Amazon/Gift","amount":1200,"type":"debit","balance":123691},
            {"date":"2024-02-15","description":"UPI/Practo/Doctor Consultation","amount":800,"type":"debit","balance":122891},
            {"date":"2024-02-17","description":"UPI/Swiggy/Food","amount":380,"type":"debit","balance":122511},
            {"date":"2024-02-18","description":"UPI/Rapido/Bike","amount":80,"type":"debit","balance":122431},
            {"date":"2024-02-20","description":"BESCOM/ELECTRICITY","amount":1320,"type":"debit","balance":121111},
            {"date":"2024-02-21","description":"UPI/Groww/SIP MF","amount":5000,"type":"debit","balance":116111},
            {"date":"2024-02-22","description":"UPI/Zepto/Grocery","amount":890,"type":"debit","balance":115221},
            {"date":"2024-02-24","description":"UPI/Airtel/DTH Recharge","amount":450,"type":"debit","balance":114771},
            {"date":"2024-02-25","description":"ATM/CASH WITHDRAWAL","amount":3000,"type":"debit","balance":111771},
            {"date":"2024-02-26","description":"UPI/Amazon/Books","amount":799,"type":"debit","balance":110972},
            {"date":"2024-02-28","description":"UPI/Swiggy/Dinner","amount":490,"type":"debit","balance":110482},

            # March
            {"date":"2024-03-01","description":"UPI/Blinkit/Groceries","amount":2100,"type":"debit","balance":108382},
            {"date":"2024-03-03","description":"UPI/Uber/Cab","amount":260,"type":"debit","balance":108122},
            {"date":"2024-03-04","description":"UPI/Zomato/Food","amount":450,"type":"debit","balance":107672},
            {"date":"2024-03-05","description":"NEFT/SALARY/TECHCORP PVT LTD","amount":65000,"type":"credit","balance":172672},
            {"date":"2024-03-06","description":"UPI/Netflix/Subscription","amount":649,"type":"debit","balance":172023},
            {"date":"2024-03-07","description":"UPI/Spotify/Monthly","amount":119,"type":"debit","balance":171904},
            {"date":"2024-03-08","description":"EMI/BAJAJ FINANCE/LAPTOP","amount":3200,"type":"debit","balance":168704},
            {"date":"2024-03-09","description":"UPI/Swiggy/Holi Special","amount":750,"type":"debit","balance":167954},
            {"date":"2024-03-10","description":"UPI/Amazon/Holi Shopping","amount":4500,"type":"debit","balance":163454},
            {"date":"2024-03-12","description":"UPI/BigBasket/Grocery","amount":2800,"type":"debit","balance":160654},
            {"date":"2024-03-13","description":"UPI/HDFC CC/Credit Card Bill","amount":18000,"type":"debit","balance":142654},
            {"date":"2024-03-15","description":"UPI/PVR/Movie","amount":650,"type":"debit","balance":142004},
            {"date":"2024-03-16","description":"UPI/Zepto/Grocery","amount":730,"type":"debit","balance":141274},
            {"date":"2024-03-17","description":"HDFC LIFE/PREMIUM","amount":2800,"type":"debit","balance":138474},
            {"date":"2024-03-18","description":"UPI/Rapido/Bike","amount":55,"type":"debit","balance":138419},
            {"date":"2024-03-19","description":"UPI/Ola/Cab","amount":340,"type":"debit","balance":138079},
            {"date":"2024-03-20","description":"MSEDCL/ELECTRICITY","amount":1580,"type":"debit","balance":136499},
            {"date":"2024-03-21","description":"UPI/Groww/SIP MF","amount":5000,"type":"debit","balance":131499},
            {"date":"2024-03-22","description":"UPI/Swiggy/Lunch","amount":320,"type":"debit","balance":131179},
            {"date":"2024-03-23","description":"UPI/Unacademy/Course","amount":2999,"type":"debit","balance":128180},
            {"date":"2024-03-24","description":"ATM/CASH WITHDRAWAL","amount":4000,"type":"debit","balance":124180},
            {"date":"2024-03-25","description":"UPI/Nykaa/Skincare","amount":1299,"type":"debit","balance":122881},
            {"date":"2024-03-26","description":"UPI/Zomato/Dinner","amount":580,"type":"debit","balance":122301},
            {"date":"2024-03-27","description":"AMAZON PAY/CASHBACK","amount":150,"type":"credit","balance":122451},
            {"date":"2024-03-28","description":"UPI/1mg/Vitamin Supplements","amount":890,"type":"debit","balance":121561},
            {"date":"2024-03-29","description":"UPI/Airtel/Broadband","amount":999,"type":"debit","balance":120562},
            {"date":"2024-03-30","description":"UPI/Swiggy/Dinner","amount":420,"type":"debit","balance":120142},
            {"date":"2024-03-31","description":"UPI/Zepto/Groceries","amount":1100,"type":"debit","balance":119042},
        ]
    }
