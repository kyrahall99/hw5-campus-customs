# Campus Customs Agent Harness

Working database: `data/campus_customs_new.db` (copy of the untouched original `data/campus_customs.db`).

## Database tables

### desk
- Fields: `date_today`, `notes`
- Why it matters: `date_today` is the shop's "today"; every agent uses it to decide what is due or overdue.

### tickets
- Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
- Why it matters: the work queue — Boss reads each open ticket and routes it, using the linked SKU/lease/invoice to pick agents.

### inventory
- Fields: `sku`, `name`, `size`, `qty`, `location` (primary key: `sku` + `size`)
- Why it matters: Inventory checks stock by SKU and size here to spot shortfalls for orders.

### pricing
- Fields: `sku`, `unit_cost`, `list_price`
- Why it matters: Accounting uses cost vs. list price to check margins on discounts and to price restock purchase orders.

### vendors
- Fields: `id`, `name`, `specialty`, `lead_days`
- Why it matters: Inventory picks the right vendor by specialty and uses `lead_days` to promise restock dates.

### leases
- Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
- Why it matters: Facilities reads rent amounts and due dates to handle rent tickets.

### cash_accounts
- Fields: `name`, `balance`, `date`
- Why it matters: Accounting checks the balance before any payment; the pay tool must refuse if it would go negative.

### payments
- Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
- Why it matters: the record of every human-approved payment; written when a payment is made.

### invoices
- Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
- Why it matters: an open unpaid invoice blocks that vendor from shipping, so Accounting and Inventory must check it before restocking.

### Work-product tables (created by the MCP server in the working copy)
- `purchase_orders` — `id`, `vendor_id`, `sku`, `size`, `qty`, `unit_cost`, `total`, `ticket_id`, `status`, `expected_date`, `created_by`, `created_at`. Restock orders Inventory drafts; `ordered` + `expected_date` (shop date + `lead_days`) once a human pays.
- `payment_requests` — `id`, `kind`, `ref_id`, `amount`, `account`, `ticket_id`, `reason`, `requested_by`, `status`, `decided_by`, `decision_note`, `created_at`, `decided_at`. Everything an agent wants paid; only a human moves it to `paid` / `rejected` (or the till marks it `refused`).
- `drafts` — `id`, `ticket_id`, `audience`, `recipient`, `subject`, `body`, `author`, `created_at`. Messages that stay on the board; never sent.

## Agents (backend/agents.py, prompts in backend/prompts/)

All five agents run on **gpt-6-luna** through Portkey (Responses API), get their shop tools only from the campus-customs MCP server, and can call `delegate(to, task)` to hand work to any other agent (full connectivity).

| Agent | Prompt | Role | Output type |
|---|---|---|---|
| Boss | `boss.md` | Reads each ticket, routes it to teammates, weighs cash across the whole board, makes the final call, updates the ticket | `TicketResolution` |
| Inventory | `inventory.md` | Stock by SKU/size, shortfall, vendor by specialty, blocked-vendor check, ETA from `lead_days`, drafts purchase orders | `AgentReport` |
| Accounting | `accounting.md` | Cash position, invoices/overdue, margin and discount math, files payment requests for human approval, prioritizes spend | `AgentReport` |
| Facilities | `facilities.md` | Lease facts, rent due dates, gets rent requested on time, landlord drafts | `AgentReport` |
| Customer Service | `customer_service.md` | Drafts customer / student-org / landlord / vendor messages; never sends | `AgentReport` |

**Agent loop:** `Team.run_agent` steps through `agent.iter()` node by node (user prompt → model request → model response/tool calls → ... → end). Every step is appended to `output/audit_trail.json` with run id, ticket id, agent, delegation depth and chain, step number, tool calls with arguments, tool returns, model text, and running token usage. Delegations and each agent's final structured output are logged as their own records. The file is append-only; it is never wiped.

## MCP tools (mcp_server/server.py)

Every tool reads/writes `data/campus_customs_new.db` and returns only stored values. Tools added in Problem 5 are marked *new*.

### Core ticket tools (from Problem 3)

**check_stock(sku, size)**
- Reads: `inventory` (row matching `sku` + `size`)
- Unlocks: **Ticket 103** (Yale AI Club, 20 × CC-HOOD-NAVY size M) — also used for 101
- Why: Ticket 103 asks for 20 hoodies in size M, and `check_stock("CC-HOOD-NAVY", "M")` returns qty 8, which tells Inventory the exact 12-unit shortfall that must be restocked before Accounting can price a bulk discount; for 101 it confirms CC-TEE-WHITE size S is at qty 0.

**get_vendor_open_invoices(vendor_id)**
- Reads: `vendors` (name, specialty, `lead_days`), `invoices` (open rows for that vendor), `desk` (`date_today` for overdue)
- Unlocks: **Ticket 101** (Tauhid Zaman, 1 × CC-TEE-WHITE size S, linked to invoice 501)
- Why: The tee is out of stock and the only apparel vendor, Bulldog Print Co (vendor 1), has open invoice 501 for $840 due 2026-08-28 — overdue against today 2026-08-31 — so this tool returns `can_ship: false`, proving 501 must be paid (with human approval) before the reprint can ship, and gives the 5-day lead time for the customer's ETA.

**get_lease(lease_id)**
- Reads: `leases` (rent, landlord, `next_due`), `desk` (`date_today`)
- Unlocks: **Ticket 102** (Elm City Properties rent notice, `lease_id` 1)
- Why: Ticket 102's email only says "rent due in 2 days," and `get_lease(1)` turns that into verified facts from the database — $2,400 for the Chapel Street shop due 2026-09-02, `days_until_due` = 2 — so Facilities and Accounting pay the real amount and not a guessed one.

### All tools
| Tool | Tables | Used for |
|---|---|---|
| `check_stock(sku, size)` | `inventory` | Ticket 103: CC-HOOD-NAVY M has 8 → shortfall of 12. Ticket 101: CC-TEE-WHITE S has 0 |
| `get_vendor_open_invoices(vendor_id)` | `vendors`, `invoices`, `desk` | Ticket 101: Bulldog Print Co has overdue invoice 501 ($840) → `can_ship: false`; lead time 5 days |
| `get_lease(lease_id)` | `leases`, `desk` | Ticket 102: $2,400 due 2026-09-02, 2 days out |
| `get_shop_date()` *new* | `desk` | "Today" for every due/overdue call |
| `list_open_tickets()` *new* | `tickets` | Boss's view of the whole board |
| `list_tickets()` *new (P7)* | `tickets` | Every ticket, any status, for the dashboard |
| `get_ticket(ticket_id)` *new* | `tickets`, `leases`, `invoices`, `drafts`, `payment_requests`, `purchase_orders` | One ticket plus everything linked to it |
| `list_stock(sku)` *new* | `inventory` | Other sizes for alternatives |
| `get_pricing(sku)` *new* | `pricing` | Unit cost, list price, unit margin |
| `quote_discount(sku, qty, discount_pct)` *new* | `pricing` | Ticket 103 bulk-discount margin math |
| `list_vendors()` *new* | `vendors`, `invoices` | Pick vendor by specialty; who can ship |
| `get_invoice(invoice_id)` *new* | `invoices`, `vendors`, `desk` | Ticket 101's linked invoice 501, overdue flag |
| `get_cash_position()` *new* | `cash_accounts`, `payment_requests`, `payments` | Balance, pending requests, balance if all approved |
| `list_payment_requests(status)` *new* | `payment_requests` | What is waiting on a human |
| `create_purchase_order(...)` *new* | `vendors`, `invoices`, `inventory`, `pricing` → writes `purchase_orders`, `payment_requests` | Restock; refuses if vendor has an open invoice; files a payment request |
| `request_payment(kind, ref_id, ...)` *new* | `invoices` / `leases`, `cash_accounts` → writes `payment_requests` | Invoice 501 (101), rent (102); amount taken from DB, duplicates refused |
| `save_draft(...)` *new* | `tickets` → writes `drafts` | Customer/landlord/vendor messages, never sent |
| `update_ticket(ticket_id, status, note, agent)` *new* | `tickets` | Status + signed note |
| `approve_payment(request_id, approved_by)` *new, human-only* | `payment_requests`, `cash_accounts` → writes `payments`; updates `invoices` / `leases` / `purchase_orders` | Pays after human approval; **refuses if cash would go negative** |
| `reject_payment(request_id, rejected_by, note)` *new, human-only* | `payment_requests`, `purchase_orders` | Human declines a request |

`purchase_orders`, `payment_requests`, and `drafts` are work-product tables the server creates in the working copy; resetting from `campus_customs.db` clears them.

## Backend routes (backend/main.py)

Start from `backend/`: `uvicorn main:app --reload --port 8000` → http://localhost:8000. Every route reads or changes shop data through the campus-customs MCP server.

- `GET /tickets` — all tickets with `status` and a `resolved` true/false flag.
- `GET /tickets/{id}` — one ticket with its linked lease/invoice, drafts, payment requests, and purchase orders.
- `POST /tickets/{id}/run` — starts the agent team (Boss first) on that ticket in the background; returns a `run_id`; when the run finishes the ticket is marked `resolved` (the Boss's own status and any pending payment ids go in the ticket note).
- `GET /runs` · `GET /runs/{run_id}` — run status (`running` / `done` / `error`) and the Boss's `TicketResolution`.
- `GET /events?since=&ticket_id=&run_id=` — recent agent events from `audit_trail.json`: agent, what it said, tools called/returned; poll with `next`.
- `GET /payment_requests?status=pending` — payments and purchase orders the agents prepared, waiting on a human.
- `POST /payment_requests/{id}/approve` — human approval; the **only** route that moves cash (calls `approve_payment`, refuses if cash would go negative).
- `POST /payment_requests/{id}/reject` — human rejects a request; no money moves.
- `GET /cash` — current checking balance from `cash_accounts`, pending total, and payments made.
- `POST /reset` — copies `data/campus_customs.db` over `data/campus_customs_new.db` (refused while a run is active; audit trail kept).
- `GET /health` — liveness check.

## Dashboard (frontend/)

React 19 + Vite + TypeScript. Start with `cd frontend && npm run dev` → http://localhost:5173; it calls the backend at `http://localhost:8000` (`VITE_API_URL`), which allows that origin via CORS. Design rationale is in `output/design.md`.

- **On the spike (left):** the three tickets as paper slips from `GET /tickets`; a red RESOLVED stamp when a run finishes.
- **The floor (center):** **Hand to the team →** calls `POST /tickets/{id}/run`; five agent "lamps" light up as each agent is pulled in and show ✓ when it reports back; the live feed polls `GET /events` every 1.2 s and shows each agent's words, sticky-note delegations, and tool-call chips with results; afterward **Who did what** shows the Boss's decision and one card per specialist (and who was not needed).
- **In-tray (right):** pending payment / purchase-order requests from `GET /payment_requests?status=pending` as cheques; **Approve & pay** calls `POST /payment_requests/{id}/approve` (the only way cash changes) and **Decline** calls `/reject`; the outbox lists drafts for the ticket, marked as never sent.
- **Top bar:** the shop date and a cash register showing checking from `GET /cash`, which counts down and flashes when a payment is approved; "Signing as" fills `payments.approved_by`; **↺ New day** calls `POST /reset`.

## Running a full resolve

1. `.venv/bin/python -m backend.reset_db` (or **↺ New day** / `POST /reset`) — working DB back to the original, checking $3,400.
2. `cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000`
3. `cd frontend && npm run dev`
4. For each ticket, **Hand to the team →**, watch the floor, approve or decline what lands in the in-tray. Results of the Problem 9 run: `output/desk_tickets.html` (Actual + Cash tabs), `output/resolved_tickets.json`, `output/resolved_board.html`, `output/audit_trail.json`.

## Safety

**Guardrails for real customers and real money**
- **Human approval for every payment.** Agents can only file requests; `approve_payment`/`reject_payment` are filtered out of every agent's tool list and are called only by the human (dashboard).
- **Amounts come from the database**, not from the model: `request_payment` reads the invoice or rent amount; POs are priced from `pricing.unit_cost`.
- **No negative balances.** `approve_payment` refuses and records the refusal if cash is short.
- **Business rules enforced in code, not just prompts:** blocked vendors cannot get POs, duplicate pending requests are refused, only open invoices can be requested.
- **Nothing leaves the shop.** Messages are drafts on the board; there is no email/phone tool.
- **Single source of truth.** All shop facts go through MCP over the working DB; the original DB is never written.
- **Full audit trail** of every model call, tool call, argument, and result, append-only, so any decision can be traced.
- **Human signature on every payment is recorded** in `payments.approved_by` and `payment_requests.decided_by`, and the dashboard warns when a request is larger than the cash in checking.
- **Least privilege:** agents see only the tools their job needs; a real deployment would also scope tools per role and require two-person approval above a dollar threshold.

**Token / cost limits**
- One model only (gpt-6-luna) for every agent.
- `UsageLimits` per ticket: 60 requests, 80 tool calls, 250k total tokens, shared across the whole delegation chain.
- `max_tokens` 2,000 per model response.
- Delegation depth capped at 3 and 8 delegations per ticket; agents cannot delegate to themselves.
- Long tool outputs are truncated in the audit log; prompts tell agents not to re-ask teammates for facts already reported.
