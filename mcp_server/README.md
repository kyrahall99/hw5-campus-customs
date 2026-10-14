# Campus Customs MCP Server

A [FastMCP](https://gofastmcp.com) server that gives every Campus Customs agent (Boss, Inventory, Accounting, Facilities, Customer Service) a shared set of tools for the shop database. It is the only way agents touch shop data. Tools only return data stored in the database; they never invent values.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never touched; reset with `.venv/bin/python -m backend.reset_db`.

The server adds three work-product tables to the working copy on first use: `purchase_orders`, `payment_requests`, and `drafts`.

## Tools

### Read
| Tool | Reads | Purpose |
|---|---|---|
| `get_shop_date()` | `desk` | The shop's "today" |
| `list_tickets()` | `tickets` | Every ticket, any status |
| `list_open_tickets()` | `tickets` | All unresolved tickets |
| `get_ticket(ticket_id)` | `tickets`, `leases`, `invoices`, `drafts`, `payment_requests`, `purchase_orders` | A ticket and everything linked to it |
| `check_stock(sku, size)` | `inventory` | On-hand qty and location for one SKU/size |
| `list_stock(sku?)` | `inventory` | All sizes of a SKU (or all stock) |
| `get_pricing(sku)` | `pricing` | Unit cost, list price, margin |
| `quote_discount(sku, qty, discount_pct)` | `pricing` | Bulk-discount revenue, cost, margin |
| `list_vendors()` | `vendors`, `invoices` | Vendors, lead times, whether each can ship |
| `get_vendor_open_invoices(vendor_id)` | `vendors`, `invoices`, `desk` | A vendor's unpaid invoices (overdue flagged) and `can_ship` |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | One invoice with overdue flag |
| `get_lease(lease_id)` | `leases`, `desk` | Rent, landlord, next due, days until due |
| `get_cash_position()` | `cash_accounts`, `payment_requests`, `payments` | Balances, pending requests, payments made |
| `list_payment_requests(status?)` | `payment_requests` | Requests by status |

### Write (agents)
| Tool | Writes | Purpose |
|---|---|---|
| `create_purchase_order(vendor_id, sku, size, qty, ticket_id, created_by)` | `purchase_orders`, `payment_requests` | Restock PO + payment request; refuses if the vendor has an open invoice |
| `request_payment(kind, ref_id, ticket_id, reason, requested_by, account?)` | `payment_requests` | Request to pay an invoice or rent; amount comes from the DB |
| `save_draft(ticket_id, audience, recipient, subject, body, author)` | `drafts` | Message draft on the board; never sent |
| `update_ticket(ticket_id, status, note, agent)` | `tickets` | Status + signed note |

### Human only (hidden from agents)
| Tool | Writes | Purpose |
|---|---|---|
| `approve_payment(payment_request_id, approved_by)` | `cash_accounts`, `payments`, `invoices` / `leases` / `purchase_orders`, `payment_requests` | Executes an approved payment; **refuses if cash would go negative** |
| `reject_payment(payment_request_id, rejected_by, note)` | `payment_requests`, `purchase_orders` | Declines a request |

## Run

```bash
.venv/bin/python mcp_server/server.py
```

Claude Code connects through `.mcp.json` at the project root.
