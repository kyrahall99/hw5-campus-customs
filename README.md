# Campus Customs Multi-Agent Operations (HW5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works the Campus Customs ticket board. Three pieces talk to each other:

- **MCP server** (`mcp_server/`) — FastMCP tools over the shop database; the only way agents touch shop data.
- **FastAPI backend** (`backend/`) — PydanticAI agents on `gpt-6-luna` via Portkey, plus routes for the dashboard. Every agent step is appended to `output/audit_trail.json`.
- **React board** (`frontend/`) — watch agents work a ticket and approve payments. Agents only *prepare* payments; a human click is the only thing that moves cash.

## Setup (once)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```

## Databases

- `data/campus_customs.db` — the **original** shop database. Never modified.
- `data/campus_customs_new.db` — the **working copy** that the MCP server, agents, and backend read and write.

### Copy the original to the working copy (clean run)

Whenever you want to start clean, copy the original over the working copy:

```bash
.venv/bin/python -m backend.reset_db
```

(Equivalent to `cp data/campus_customs.db data/campus_customs_new.db`.) This clears every payment, purchase order, draft, and ticket update from earlier runs and puts checking back to **$3,400.00**. The audit trail is kept — it is append-only.

## 1. Start the MCP server

```bash
.venv/bin/python mcp_server/server.py
```

It speaks MCP over stdio. You usually don't need to start it by hand:

- **Claude Code** starts it from `.mcp.json` (approve the `campus-customs` server when asked).
- **The backend** starts its own copy automatically when it launches.

Running the command above is a quick way to check it starts; stop it with `Ctrl+C`. Tool list: `mcp_server/README.md`.

## 2. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

The backend is now at http://localhost:8000 (route list in `output/harness.md`; try http://localhost:8000/tickets). It allows the board's origin, http://localhost:5173.

## 3. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

This opens the desk at http://localhost:5173. Pick a ticket on the left, click **Hand to the team →**, watch the agents on the floor, and approve or decline anything that lands in the in-tray. The cash register in the top bar drops when a payment is approved.

## 4. Reset the database before a full 3-ticket run

Always start a full run of tickets 101, 102, and 103 from the original data, so the cash math starts at $3,400.00. Do **one** of:

- Click **↺ New day** in the board's top bar, or
- `curl -X POST http://localhost:8000/reset`, or
- stop the backend and run `.venv/bin/python -m backend.reset_db`.

The reset route refuses while an agent run is in progress. After resetting, run 101, 102, and 103 on the board and approve each request when the team asks for it.

## Shop rules the system enforces

- Today is `desk.date_today` (2026-08-31), not the real date.
- A vendor with an open unpaid invoice will not ship; the purchase-order tool refuses.
- Every payment needs human approval; payment amounts come from the database, not the model.
- No negative balances — the pay step refuses if cash is short. Cash only goes out.
- Messages are drafts on the board; nothing is emailed or sent.
- Only `gpt-6-luna` is used, for every agent.

## Where things are

| Path | What |
|---|---|
| `mcp_server/server.py` | All MCP tools |
| `backend/agents.py` | The five agents, agent loop, delegation, limits |
| `backend/prompts/*.md` | One prompt per agent |
| `backend/models.py` | Data types |
| `backend/main.py` | FastAPI routes |
| `frontend/src/` | React board |
| `output/harness.md` | Tables, tools, agents, routes, dashboard, safety |
| `output/desk_tickets.html` | Plan vs. actual per ticket, cash, reflection |
| `output/resolved_tickets.json`, `output/resolved_board.html` | Results of the full run |
| `output/audit_trail.json` | Every agent step, append-only |
| `AI_prompts.md` | Every prompt typed into Claude Code |
