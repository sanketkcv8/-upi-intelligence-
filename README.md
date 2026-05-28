# 💳 UPI Spending Intelligence

Upload any Indian bank statement PDF → Claude extracts every transaction → categorises into 15 Indian spending categories → generates personalised insights.

Works with ANY bank: HDFC, SBI, ICICI, Axis, Kotak, and more.

---

## What it does

1. **Reads any bank PDF** — Claude extracts transactions regardless of bank format. No bank-specific rules needed.
2. **Categorises everything** — 15 categories tuned for India: Swiggy → Food & Dining, Zepto → Groceries, Groww → Investments, etc.
3. **Generates insights** — Claude finds patterns: overspending categories, subscription drain, monthly spikes, savings rate vs benchmarks.
4. **Interactive dashboard** — Filter transactions, view charts, compare months.

---

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run dashboard.py
```

Open: **http://localhost:8501**

---

## Getting your bank statement PDF

| Bank | How to download |
|---|---|
| HDFC | NetBanking → My Accounts → View Statement → Download PDF |
| SBI | OnlineSBI → e-Statement → Download |
| ICICI | iMobile / NetBanking → Account Statement → PDF |
| Axis | NetBanking → Accounts → Statement → Download PDF |
| Kotak | NetBanking → Account Statement → PDF |

---

## 15 spending categories

Food & Dining · Groceries · Transport · Shopping · Entertainment · Utilities · Health · Education · EMI & Loans · Insurance · Investments · Transfers · Cash · Income · Others

---

## Files

```
upi_intelligence/
├── dashboard.py    ← Streamlit UI (run this)
├── config.py       ← 15 categories for India
├── parser.py       ← PDF extraction via Claude
├── categoriser.py  ← Transaction labelling via Claude
├── insights.py     ← Spending analysis via Claude
├── database.py     ← SQLite storage
└── requirements.txt
```
