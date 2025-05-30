# inventory_api_main.py
"""A minimal inventory management REST API (v1) using Flask + SQLite.

# /Users/nishiokakeisuke/work/AWS/inventory_api_main.py

Implements five endpoints:
1. POST   /v1/stocks        – create or add stock for a product
2. GET    /v1/stocks[/name] – check stock (all or single)
3. POST   /v1/sales         – sell a product and record turnover
4. GET    /v1/sales         – check accumulated sales since last reset
5. DELETE /v1/stocks        – delete *all* stocks and sales (reset)

All request/response bodies are JSON．Input is strictly validated and errors
return {"message": "ERROR"} with HTTP 400．
"""
from __future__ import annotations

import math
import re
import sqlite3
from contextlib import closing
from decimal import Decimal, ROUND_UP
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import Flask, jsonify, request, url_for

app = Flask(__name__)
DB_PATH = Path("inventory.db")
NAME_PATTERN = re.compile(r"^[A-Za-z]{1,8}$")  # 1–8 alphabetic chars (ASCII)

###############################################################################
# DB helpers                                                                  #
###############################################################################

def init_db() -> None:
    """Create tables on first run and ensure a single sales row exists．"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS stocks (
                   name   TEXT PRIMARY KEY,
                   amount INTEGER NOT NULL CHECK(amount >= 0)
               )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS sales (
                   id    INTEGER PRIMARY KEY CHECK (id = 1),
                   total REAL NOT NULL
               )"""
        )
        cur.execute("INSERT OR IGNORE INTO sales (id, total) VALUES (1, 0)")
        conn.commit()
        
        
# ---- in init_db() 直後 ------------
cur.execute(
    """CREATE TABLE IF NOT EXISTS logs (
           id        INTEGER PRIMARY KEY AUTOINCREMENT,
           name      TEXT,
           action    TEXT CHECK(action IN ('add','sale')),
           amount    INTEGER,
           timestamp TEXT DEFAULT CURRENT_TIMESTAMP
       )"""
)

def log_event(name: str, action: str, amount: int) -> None:
    exec_sql(
        "INSERT INTO logs (name, action, amount) VALUES (?, ?, ?)",
        (name, action, amount),
    )


def exec_sql(sql: str, params: Tuple | Dict[str, Any] = ()) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(sql, params)
        conn.commit()


def query_one(sql: str, params: Tuple | Dict[str, Any] = ()) -> Any:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def query_all(sql: str, params: Tuple | Dict[str, Any] = ()) -> list[Tuple[Any, ...]]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


###############################################################################
# Utility                                                                     #
###############################################################################

def validate_name(name: Any) -> str | None:
    if isinstance(name, str) and NAME_PATTERN.fullmatch(name):
        return name
    return None


def validate_positive_int(value: Any, default: int | None = None) -> int | None:
    if value is None and default is not None:
        return default
    if isinstance(value, int) and value > 0:
        return value
    return None


def validate_positive_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def error_response():
    return jsonify({"message": "ERROR"}), 400


def ceil_two_decimals(x: float) -> float:
    d = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_UP)
    return float(d)


###############################################################################
# Endpoints                                                                   #
###############################################################################

@app.route("/v1/stocks", methods=["POST"])
def add_stock():
    data = request.get_json(silent=True) or {}
    name = validate_name(data.get("name"))
    amount = validate_positive_int(data.get("amount"), default=1)
    if name is None or amount is None:
        return error_response()

    # upsert to stocks table
    existing = query_one("SELECT amount FROM stocks WHERE name = ?", (name,))
    if existing:
        exec_sql("UPDATE stocks SET amount = amount + ? WHERE name = ?", (amount, name))
    else:
        exec_sql("INSERT INTO stocks (name, amount) VALUES (?, ?)", (name, amount))

    location = url_for("get_stock", name=name, _external=True)
    return (
        jsonify({"name": name, "amount": amount}),
        200,
        {"Location": location},
    )


@app.route("/v1/stocks", methods=["GET"])
@app.route("/v1/stocks/<name>", methods=["GET"])
def get_stock(name: str | None = None):
    if name is not None:
        valid_name = validate_name(name)
        if valid_name is None:
            return error_response()
        row = query_one("SELECT amount FROM stocks WHERE name = ?", (valid_name,))
        amount = row[0] if row else 0
        return jsonify({valid_name: amount})

    # no name: list all with amount > 0 sorted by name
    rows = query_all("SELECT name, amount FROM stocks WHERE amount > 0 ORDER BY name ASC")
    return jsonify({r[0]: r[1] for r in rows})


@app.route("/v1/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True) or {}
    name = validate_name(data.get("name"))
    amount = validate_positive_int(data.get("amount"), default=1)
    price = (
        validate_positive_number(data.get("price")) if "price" in data else None
    )
    if name is None or amount is None:
        return error_response()

    # check stock availability
    row = query_one("SELECT amount FROM stocks WHERE name = ?", (name,))
    current = row[0] if row else 0
    if current < amount:
        return error_response()  # cannot oversell

    exec_sql("UPDATE stocks SET amount = amount - ? WHERE name = ?", (amount, name))

    # update sales total if price provided
    if price is not None:
        increment = price * amount
        exec_sql("UPDATE sales SET total = total + ? WHERE id = 1", (increment,))

    location = url_for("create_sale", name=name, _external=True)
    return (
        jsonify({"name": name, "amount": amount}),
        200,
        {"Location": location},
    )


@app.route("/v1/sales", methods=["GET"])
def get_sales():
    row = query_one("SELECT total FROM sales WHERE id = 1")
    total = row[0] if row else 0.0
    return jsonify({"sales": ceil_two_decimals(total)})


@app.route("/v1/stocks", methods=["DELETE"])
def reset():
    exec_sql("DELETE FROM stocks")
    exec_sql("UPDATE sales SET total = 0 WHERE id = 1")
    return "", 204  # No Content


###############################################################################
# Startup                                                                     #
###############################################################################

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
