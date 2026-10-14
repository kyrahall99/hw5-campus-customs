"""Campus Customs MCP server.

Exposes tools over the working database data/campus_customs_new.db.
Every tool returns only what is stored in the database -- nothing is invented.

Money never moves without a human: agents can only *request* payments.
`approve_payment` / `reject_payment` are human-only (tagged "human") and the
backend hides them from every agent.
"""

import sqlite3
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs")

TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved"]

# Work-product tables the agents write to. They start empty, so resetting the
# working copy from campus_customs.db also clears them.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    size TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_cost REAL NOT NULL,
    total REAL NOT NULL,
    ticket_id INTEGER,
    status TEXT NOT NULL,          -- pending_approval | ordered | rejected | payment_refused
    expected_date TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,            -- invoice | rent | purchase_order
    ref_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    ticket_id INTEGER,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,          -- pending | paid | rejected | refused
    decided_by TEXT,
    decision_note TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    audience TEXT NOT NULL,        -- customer | vendor | landlord | internal
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _now(conn: sqlite3.Connection) -> str:
    # Shop time is desk.date_today; never the machine clock.
    return _today(conn)


def _rows(cursor) -> list[dict]:
    return [dict(r) for r in cursor]


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    today = _today(conn)
    return [
        {**dict(r), "overdue": r["due_date"] < today}
        for r in conn.execute(
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
            (vendor_id,),
        )
    ]


# ---------------------------------------------------------------- read tools


@mcp.tool
def get_shop_date() -> dict:
    """Return desk.date_today, the shop's 'today'. Use it for every due/overdue decision."""
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    return dict(row)


@mcp.tool
def list_open_tickets() -> list[dict]:
    """Return every ticket that is not resolved, oldest first."""
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at"))


@mcp.tool
def list_tickets() -> list[dict]:
    """Return every ticket (any status), oldest first."""
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM tickets ORDER BY created_at"))


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket with its linked lease/invoice rows and any drafts or payment requests already filed for it."""
    with _connect() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"found": False, "ticket_id": ticket_id}
        out = {"found": True, "ticket": dict(t)}
        if t["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            out["lease"] = dict(lease) if lease else None
        if t["invoice_id"] is not None:
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (t["invoice_id"],)).fetchone()
            out["invoice"] = dict(inv) if inv else None
        out["drafts"] = _rows(conn.execute("SELECT * FROM drafts WHERE ticket_id = ?", (ticket_id,)))
        out["payment_requests"] = _rows(
            conn.execute("SELECT * FROM payment_requests WHERE ticket_id = ?", (ticket_id,))
        )
        out["purchase_orders"] = _rows(
            conn.execute("SELECT * FROM purchase_orders WHERE ticket_id = ?", (ticket_id,))
        )
    return out


@mcp.tool
def check_stock(sku: str, size: str) -> dict:
    """Return the on-hand quantity and location for one SKU in one size."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku, "size": size}
    return {"found": True, **dict(row)}


@mcp.tool
def list_stock(sku: str | None = None) -> list[dict]:
    """Return inventory rows for one SKU (all sizes), or every row if sku is omitted."""
    with _connect() as conn:
        if sku:
            return _rows(conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY size", (sku,)))
        return _rows(conn.execute("SELECT * FROM inventory ORDER BY sku, size"))


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Return unit_cost and list_price for a SKU, plus the per-unit margin at list price."""
    with _connect() as conn:
        row = conn.execute("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        return {"found": False, "sku": sku}
    margin = row["list_price"] - row["unit_cost"]
    return {
        "found": True,
        **dict(row),
        "unit_margin": round(margin, 2),
        "margin_pct": round(100 * margin / row["list_price"], 2),
    }


@mcp.tool
def quote_discount(sku: str, qty: int, discount_pct: float) -> dict:
    """Price a bulk order of `qty` units at `discount_pct` off list, using pricing.unit_cost/list_price.

    Returns the discounted unit price, order revenue, order cost, and margin so a
    discount can be checked before anyone agrees to it.
    """
    if qty <= 0 or not 0 <= discount_pct < 100:
        return {"ok": False, "error": "qty must be > 0 and discount_pct in [0, 100)"}
    with _connect() as conn:
        row = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        return {"ok": False, "error": f"no pricing for {sku}"}
    unit_price = round(row["list_price"] * (1 - discount_pct / 100), 2)
    revenue = round(unit_price * qty, 2)
    cost = round(row["unit_cost"] * qty, 2)
    margin = round(revenue - cost, 2)
    return {
        "ok": True,
        "sku": sku,
        "qty": qty,
        "discount_pct": discount_pct,
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
        "discounted_unit_price": unit_price,
        "order_revenue": revenue,
        "order_cost": cost,
        "order_margin": margin,
        "margin_pct": round(100 * margin / revenue, 2) if revenue else None,
        "list_order_revenue": round(row["list_price"] * qty, 2),
    }


@mcp.tool
def list_vendors() -> list[dict]:
    """Return every vendor with specialty, lead_days, and whether it can ship (no open invoices)."""
    with _connect() as conn:
        vendors = _rows(conn.execute("SELECT * FROM vendors ORDER BY id"))
        for v in vendors:
            v["open_invoice_ids"] = [i["id"] for i in _open_invoices(conn, v["id"])]
            v["can_ship"] = not v["open_invoice_ids"]
    return vendors


@mcp.tool
def get_vendor_open_invoices(vendor_id: int) -> dict:
    """Return a vendor's details and any unpaid invoices, flagged overdue against desk.date_today.

    A vendor with an open invoice will not ship new product.
    """
    with _connect() as conn:
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            return {"found": False, "vendor_id": vendor_id}
        today = _today(conn)
        invoices = _open_invoices(conn, vendor_id)
    return {
        "found": True,
        "vendor": dict(vendor),
        "date_today": today,
        "open_invoices": invoices,
        "can_ship": not invoices,
    }


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Return one invoice with its vendor name and whether it is overdue against desk.date_today."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "invoice_id": invoice_id}
        today = _today(conn)
    return {"found": True, **dict(row), "date_today": today,
            "overdue": row["status"] == "open" and row["due_date"] < today}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Return a lease's rent amount and next due date, with days until due from desk.date_today."""
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"found": False, "lease_id": lease_id}
        today = _today(conn)
        days = conn.execute(
            "SELECT CAST(julianday(?) - julianday(?) AS INTEGER) AS d", (lease["next_due"], today)
        ).fetchone()["d"]
    return {"found": True, **dict(lease), "date_today": today, "days_until_due": days}


@mcp.tool
def get_cash_position() -> dict:
    """Return each cash account balance, the total of pending payment requests, and cash left if all were approved."""
    with _connect() as conn:
        accounts = _rows(conn.execute("SELECT name, balance, date FROM cash_accounts"))
        pending = _rows(conn.execute(
            "SELECT id, kind, ref_id, amount, account, ticket_id FROM payment_requests WHERE status = 'pending'"
        ))
        payments = _rows(conn.execute("SELECT * FROM payments ORDER BY id"))
    for a in accounts:
        committed = sum(p["amount"] for p in pending if p["account"] == a["name"])
        a["pending_requests_total"] = round(committed, 2)
        a["balance_if_all_pending_approved"] = round(a["balance"] - committed, 2)
    return {"accounts": accounts, "pending_requests": pending, "payments_made": payments}


@mcp.tool
def list_payment_requests(status: str | None = None) -> list[dict]:
    """Return payment requests, optionally filtered by status (pending, paid, rejected, refused)."""
    with _connect() as conn:
        if status:
            return _rows(conn.execute("SELECT * FROM payment_requests WHERE status = ? ORDER BY id", (status,)))
        return _rows(conn.execute("SELECT * FROM payment_requests ORDER BY id"))


# ------------------------------------------------------- agent write tools


@mcp.tool
def create_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int, created_by: str) -> dict:
    """Draft a restock purchase order and file a payment request for it (needs human approval).

    Refuses if the vendor has an open unpaid invoice (it will not ship) or if the
    SKU/size does not exist. Cost comes from pricing.unit_cost; the expected date
    is filled in from vendors.lead_days when the human approves payment.
    """
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive"}
    with _connect() as conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"ok": False, "error": f"vendor {vendor_id} not found"}
        if not conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone():
            return {"ok": False, "error": f"{sku} size {size} is not a stocked item"}
        blocking = _open_invoices(conn, vendor_id)
        if blocking:
            return {"ok": False, "error": f"{vendor['name']} has open invoice(s) and will not ship",
                    "open_invoice_ids": [i["id"] for i in blocking]}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"ok": False, "error": f"no pricing for {sku}"}
        total = round(price["unit_cost"] * qty, 2)
        now = _now(conn)
        po_id = conn.execute(
            "INSERT INTO purchase_orders (vendor_id, sku, size, qty, unit_cost, total, ticket_id, status, "
            "created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?, ?)",
            (vendor_id, sku, size, qty, price["unit_cost"], total, ticket_id, created_by, now),
        ).lastrowid
        req_id = conn.execute(
            "INSERT INTO payment_requests (kind, ref_id, amount, account, ticket_id, reason, requested_by, "
            "status, created_at) VALUES ('purchase_order', ?, ?, 'checking', ?, ?, ?, 'pending', ?)",
            (po_id, total, ticket_id, f"PO {po_id}: {qty} x {sku} {size} from {vendor['name']}", created_by, now),
        ).lastrowid
    return {"ok": True, "purchase_order_id": po_id, "payment_request_id": req_id, "total": total,
            "vendor": vendor["name"], "lead_days": vendor["lead_days"], "status": "pending_approval"}


@mcp.tool
def request_payment(kind: Literal["invoice", "rent"], ref_id: int, ticket_id: int, reason: str,
                    requested_by: str, account: str = "checking") -> dict:
    """File a payment request for an open invoice (ref_id = invoices.id) or rent (ref_id = leases.id).

    The amount is taken from the database, never from the caller. Nothing is paid
    until a human approves the request. Duplicate pending requests are refused.
    """
    with _connect() as conn:
        if kind == "invoice":
            row = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"ok": False, "error": f"invoice {ref_id} not found"}
            if row["status"] != "open":
                return {"ok": False, "error": f"invoice {ref_id} is {row['status']}, not open"}
            amount = row["amount"]
        else:
            row = conn.execute("SELECT monthly_rent FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"ok": False, "error": f"lease {ref_id} not found"}
            amount = row["monthly_rent"]
        if not conn.execute("SELECT 1 FROM cash_accounts WHERE name = ?", (account,)).fetchone():
            return {"ok": False, "error": f"no cash account named {account}"}
        dup = conn.execute(
            "SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'", (kind, ref_id)
        ).fetchone()
        if dup:
            return {"ok": False, "error": "a pending request already exists", "payment_request_id": dup["id"]}
        req_id = conn.execute(
            "INSERT INTO payment_requests (kind, ref_id, amount, account, ticket_id, reason, requested_by, "
            "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (kind, ref_id, amount, account, ticket_id, reason, requested_by, _now(conn)),
        ).lastrowid
    return {"ok": True, "payment_request_id": req_id, "kind": kind, "ref_id": ref_id,
            "amount": amount, "status": "pending"}


@mcp.tool
def save_draft(ticket_id: int, audience: Literal["customer", "vendor", "landlord", "internal"],
               recipient: str, subject: str, body: str, author: str) -> dict:
    """Save a message draft on the board for a ticket. Drafts are never sent."""
    with _connect() as conn:
        if not conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            return {"ok": False, "error": f"ticket {ticket_id} not found"}
        draft_id = conn.execute(
            "INSERT INTO drafts (ticket_id, audience, recipient, subject, body, author, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, audience, recipient, subject, body, author, _now(conn)),
        ).lastrowid
    return {"ok": True, "draft_id": draft_id, "sent": False}


@mcp.tool
def update_ticket(ticket_id: int, status: TicketStatus, note: str, agent: str) -> dict:
    """Set a ticket's status and append a signed note to tickets.notes (existing notes are kept)."""
    with _connect() as conn:
        t = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "error": f"ticket {ticket_id} not found"}
        notes = (t["notes"] or "") + f"\n[{agent}] {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes.strip(), ticket_id))
    return {"ok": True, "ticket_id": ticket_id, "status": status}


# ------------------------------------------------------ human-only tools


@mcp.tool(tags={"human"})
def approve_payment(payment_request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Pay an approved request: refuse if cash would go negative, otherwise
    debit the account, write a payments row, and update the invoice/lease/PO it pays."""
    with _connect() as conn:
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (payment_request_id,)).fetchone()
        if req is None:
            return {"ok": False, "error": f"payment request {payment_request_id} not found"}
        if req["status"] != "pending":
            return {"ok": False, "error": f"request is {req['status']}, not pending"}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (req["account"],)).fetchone()
        now = _now(conn)
        if acct is None or acct["balance"] < req["amount"]:
            balance = acct["balance"] if acct else None
            conn.execute(
                "UPDATE payment_requests SET status = 'refused', decided_by = ?, decision_note = ?, decided_at = ? "
                "WHERE id = ?",
                (approved_by, f"insufficient cash: balance {balance}, needed {req['amount']}", now, req["id"]),
            )
            if req["kind"] == "purchase_order":
                conn.execute("UPDATE purchase_orders SET status = 'payment_refused' WHERE id = ?", (req["ref_id"],))
            return {"ok": False, "error": "insufficient cash; payment refused", "balance": balance,
                    "amount": req["amount"]}
        new_balance = round(acct["balance"] - req["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                     (new_balance, now, req["account"]))
        payment_id = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], req["ref_id"], req["amount"], req["account"], now, approved_by),
        ).lastrowid
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
        elif req["kind"] == "rent":
            conn.execute("UPDATE leases SET next_due = date(next_due, '+1 month') WHERE id = ?", (req["ref_id"],))
        elif req["kind"] == "purchase_order":
            conn.execute(
                "UPDATE purchase_orders SET status = 'ordered', expected_date = "
                "date(?, '+' || (SELECT lead_days FROM vendors WHERE id = purchase_orders.vendor_id) || ' days') "
                "WHERE id = ?",
                (now, req["ref_id"]),
            )
        conn.execute(
            "UPDATE payment_requests SET status = 'paid', decided_by = ?, decided_at = ? WHERE id = ?",
            (approved_by, now, req["id"]),
        )
    return {"ok": True, "payment_id": payment_id, "amount": req["amount"], "account": req["account"],
            "new_balance": new_balance}


@mcp.tool(tags={"human"})
def reject_payment(payment_request_id: int, rejected_by: str, note: str) -> dict:
    """HUMAN ONLY. Reject a pending payment request; no money moves."""
    with _connect() as conn:
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (payment_request_id,)).fetchone()
        if req is None or req["status"] != "pending":
            return {"ok": False, "error": "no pending request with that id"}
        now = _now(conn)
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decision_note = ?, decided_at = ? "
            "WHERE id = ?",
            (rejected_by, note, now, payment_request_id),
        )
        if req["kind"] == "purchase_order":
            conn.execute("UPDATE purchase_orders SET status = 'rejected' WHERE id = ?", (req["ref_id"],))
    return {"ok": True, "payment_request_id": payment_request_id, "status": "rejected"}


if __name__ == "__main__":
    mcp.run(show_banner=False)
