# database.py
# -----------
# Stores uploaded statements and extracted transactions in SQLite.
# Each upload gets its own statement record — so you can compare months.

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

# On Streamlit Cloud the filesystem is ephemeral.
# Use /tmp so it survives within a session. Locally saves next to this file.
_is_cloud = os.environ.get("HOME") == "/home/appuser"
DB_PATH = Path("/tmp/upi_intelligence.db") if _is_cloud \
          else Path(__file__).parent / "upi_intelligence.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS statements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            bank        TEXT,
            period      TEXT,
            uploaded_at TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            stmt_id     INTEGER,
            date        TEXT,
            description TEXT,
            amount      REAL,
            type        TEXT,
            balance     REAL,
            category    TEXT,
            subcategory TEXT,
            merchant    TEXT,
            FOREIGN KEY(stmt_id) REFERENCES statements(id)
        );

        CREATE TABLE IF NOT EXISTS insights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            stmt_id     INTEGER,
            content     TEXT,
            created_at  TEXT,
            FOREIGN KEY(stmt_id) REFERENCES statements(id)
        );
    """)
    conn.commit()
    conn.close()


def save_statement(filename, bank, period) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO statements (filename, bank, period, uploaded_at) VALUES (?,?,?,?)",
        (filename, bank, period, datetime.utcnow().isoformat())
    )
    stmt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return stmt_id


def save_transactions(stmt_id: int, transactions: list):
    conn = get_conn()
    conn.executemany(
        """INSERT INTO transactions
           (stmt_id, date, description, amount, type, balance, category, subcategory, merchant)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [(stmt_id, t["date"], t["description"], t["amount"], t["type"],
          t.get("balance", 0), t.get("category","Others"),
          t.get("subcategory",""), t.get("merchant",""))
         for t in transactions]
    )
    conn.commit()
    conn.close()


def save_insights(stmt_id: int, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO insights (stmt_id, content, created_at) VALUES (?,?,?)",
        (stmt_id, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_transactions(stmt_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE stmt_id=? ORDER BY date", (stmt_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_statements() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM statements ORDER BY uploaded_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_insights(stmt_id: int) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT content FROM insights WHERE stmt_id=? ORDER BY created_at DESC LIMIT 1",
        (stmt_id,)
    ).fetchone()
    conn.close()
    return row["content"] if row else None


def delete_statement(stmt_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE stmt_id=?", (stmt_id,))
    conn.execute("DELETE FROM insights WHERE stmt_id=?", (stmt_id,))
    conn.execute("DELETE FROM statements WHERE id=?", (stmt_id,))
    conn.commit()
    conn.close()
