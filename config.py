# config.py
# ---------
# Spending categories tuned for Indian UPI/bank transactions.
# Includes the most common UPI merchants, apps, and payment patterns.

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# 15 categories that cover virtually all Indian consumer spending
CATEGORIES = {
    "Food & Dining": {
        "icon":  "🍔",
        "color": "#E8734A",
        "desc":  "Restaurants, Swiggy, Zomato, cafes, canteens",
        "examples": ["swiggy", "zomato", "eatsure", "restaurant", "hotel", "dhaba", "cafe", "dominos", "mcdonalds", "kfc"],
    },
    "Groceries": {
        "icon":  "🛒",
        "color": "#4CAF50",
        "desc":  "Supermarkets, Blinkit, Zepto, BigBasket, DMart",
        "examples": ["blinkit", "zepto", "bigbasket", "dmart", "reliance fresh", "more", "grofers", "jiomart", "supermarket"],
    },
    "Transport": {
        "icon":  "🚗",
        "color": "#2196F3",
        "desc":  "Ola, Uber, Metro, petrol, auto, train tickets",
        "examples": ["ola", "uber", "rapido", "metro", "irctc", "petrol", "fuel", "bpcl", "hpcl", "iocl", "fastag"],
    },
    "Shopping": {
        "icon":  "🛍️",
        "color": "#9C27B0",
        "desc":  "Amazon, Flipkart, Myntra, Meesho, offline retail",
        "examples": ["amazon", "flipkart", "myntra", "meesho", "nykaa", "ajio", "tata cliq", "snapdeal", "shopclues"],
    },
    "Entertainment": {
        "icon":  "🎬",
        "color": "#FF5722",
        "desc":  "Netflix, Hotstar, movies, gaming, concerts",
        "examples": ["netflix", "hotstar", "prime video", "spotify", "youtube", "bookmyshow", "pvr", "inox", "gaana", "jiosaavn"],
    },
    "Utilities": {
        "icon":  "⚡",
        "color": "#FFC107",
        "desc":  "Electricity, water, gas, internet, mobile recharge",
        "examples": ["electricity", "bescom", "msedcl", "tata power", "airtel", "jio", "vi", "bsnl", "gas", "piped", "broadband"],
    },
    "Health": {
        "icon":  "🏥",
        "color": "#00BCD4",
        "desc":  "Pharmacies, hospitals, doctors, Apollo, Practo",
        "examples": ["apollo", "medplus", "1mg", "netmeds", "practo", "pharmeasy", "hospital", "clinic", "doctor", "lab", "diagnostic"],
    },
    "Education": {
        "icon":  "📚",
        "color": "#607D8B",
        "desc":  "School fees, courses, Byju's, Unacademy, books",
        "examples": ["byju", "unacademy", "coursera", "udemy", "school", "college", "tuition", "coaching", "books", "stationery"],
    },
    "EMI & Loans": {
        "icon":  "🏦",
        "color": "#795548",
        "desc":  "EMI payments, loan repayments, BNPL",
        "examples": ["emi", "loan", "bajaj", "hdfc emi", "icici emi", "bnpl", "simpl", "lazypay", "slice", "repayment"],
    },
    "Insurance": {
        "icon":  "🛡️",
        "color": "#009688",
        "desc":  "LIC, health insurance, vehicle insurance premiums",
        "examples": ["lic", "insurance", "premium", "policy", "star health", "niva bupa", "hdfc life", "max life", "tata aia"],
    },
    "Investments": {
        "icon":  "📈",
        "color": "#1D9E75",
        "desc":  "Mutual funds, SIPs, stocks, Groww, Zerodha, NPS",
        "examples": ["groww", "zerodha", "kuvera", "paytm money", "sip", "mutual fund", "nps", "ppf", "stocks", "demat"],
    },
    "Transfers": {
        "icon":  "↔️",
        "color": "#3F51B5",
        "desc":  "UPI P2P transfers to friends and family",
        "examples": ["transfer", "sent to", "received from", "upi", "neft", "imps", "rtgs", "p2p"],
    },
    "Cash": {
        "icon":  "💵",
        "color": "#8BC34A",
        "desc":  "ATM withdrawals, cash deposits",
        "examples": ["atm", "cash withdrawal", "cdm", "cash deposit"],
    },
    "Income": {
        "icon":  "💰",
        "color": "#4CAF50",
        "desc":  "Salary credits, freelance payments, refunds received",
        "examples": ["salary", "credit", "refund", "cashback", "reward", "freelance", "payment received"],
    },
    "Others": {
        "icon":  "📦",
        "color": "#9E9E9E",
        "desc":  "Anything that doesn't fit the above",
        "examples": [],
    },
}

CATEGORY_NAMES = list(CATEGORIES.keys())

# Debit transaction types (money going out)
DEBIT_KEYWORDS = ["dr", "debit", "paid", "purchase", "withdrawal", "sent", "transfer to"]

# Credit transaction types (money coming in)
CREDIT_KEYWORDS = ["cr", "credit", "received", "refund", "cashback", "salary", "transfer from"]
