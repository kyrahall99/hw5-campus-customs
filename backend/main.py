"""Campus Customs backend: FastAPI routes for the React dashboard.

Start from the backend/ folder:
    uvicorn main:app --reload --port 8000

Shop data is read and changed only through the campus-customs MCP server. The
agents prepare payments; the /approve route (a human click) is the only thing
that moves cash.
"""

import asyncio
import json
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `backend.*` imports work when run as `uvicorn main:app` from backend/

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StdioTransport  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import audit  # noqa: E402
from backend.agents import Team  # noqa: E402

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"

team: Team | None = None
mcp_client: Client | None = None
runs: dict[str, dict] = {}  # run_id -> {ticket_id, status, result | error}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global team, mcp_client
    team = Team()
    mcp_client = Client(StdioTransport(
        command=str(ROOT / ".venv" / "bin" / "python"),
        args=[str(ROOT / "mcp_server" / "server.py")],
        cwd=str(ROOT),
    ))
    async with team.connected(), mcp_client:
        yield


app = FastAPI(title="Campus Customs Ops", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, **args):
    result = await mcp_client.call_tool(tool, args, raise_on_error=False)
    if result.is_error:
        raise HTTPException(502, f"MCP tool {tool} failed: {result.content}")
    return result.structured_content.get("result", result.structured_content) \
        if result.structured_content is not None else result.data


def _active_runs() -> list[dict]:
    return [{"run_id": rid, **r} for rid, r in runs.items() if r["status"] == "running"]


# ------------------------------------------------------------------ tickets


@app.get("/tickets")
async def list_tickets():
    """All tickets with an open/resolved flag."""
    tickets = await mcp("list_tickets")
    return [
        {"id": t["id"], "type": t["type"], "requester": t["requester"], "subject": t["subject"],
         "status": t["status"], "resolved": t["status"] == "resolved"}
        for t in tickets
    ]


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    """One ticket with its linked lease/invoice, drafts, payment requests, and purchase orders."""
    t = await mcp("get_ticket", ticket_id=ticket_id)
    if not t.get("found"):
        raise HTTPException(404, f"ticket {ticket_id} not found")
    return t


async def _run(run_id: str, ticket_id: int) -> None:
    try:
        result = await team.work_ticket(ticket_id, run_id=run_id)
        # The run is finished, so the ticket leaves the open queue. Anything still waiting on a
        # human (payment requests) stays visible on the board and in the note.
        pending = result.pending_payment_request_ids
        note = (f"Agent run {run_id} finished. Boss status: {result.status}."
                + (f" Pending human approval: payment request(s) {pending}." if pending else ""))
        await mcp("update_ticket", ticket_id=ticket_id, status="resolved", note=note, agent="system")
        runs[run_id].update(status="done", result=result.model_dump())
    except Exception as e:  # surface failures to the dashboard and the audit trail
        runs[run_id].update(status="error", error=f"{type(e).__name__}: {e}")
        audit.append({"run_id": run_id, "ticket_id": ticket_id, "agent": "system", "event": "run_error",
                      "text": runs[run_id]["error"]})


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int):
    """Start the agent team on a ticket in the background; poll /runs/{run_id} and /events."""
    t = await mcp("get_ticket", ticket_id=ticket_id)
    if not t.get("found"):
        raise HTTPException(404, f"ticket {ticket_id} not found")
    if any(r["ticket_id"] == ticket_id for r in _active_runs()):
        raise HTTPException(409, f"ticket {ticket_id} is already being worked")
    run_id = uuid.uuid4().hex[:12]
    runs[run_id] = {"ticket_id": ticket_id, "status": "running", "result": None, "error": None}
    asyncio.create_task(_run(run_id, ticket_id))
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "running"}


@app.get("/runs")
async def list_runs():
    return [{"run_id": rid, **r} for rid, r in runs.items()]


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    if run_id not in runs:
        raise HTTPException(404, "unknown run")
    return {"run_id": run_id, **runs[run_id]}


# ------------------------------------------------------------------- events


def _summarize(rec: dict) -> dict:
    """Flatten one audit record into what the board shows: who, what they said, which tools."""
    said, tools = [], []
    for o in rec.get("outputs", []):
        if o["type"] == "text":
            said.append(o["text"])
        elif o["type"] == "tool_call":
            tools.append({"tool": o["tool"], "args": o.get("args")})
    for i in rec.get("inputs", []):
        if i["type"] == "tool_return":
            tools.append({"tool": i["tool"], "result": i.get("output")})
    if rec.get("event") == "delegate":
        said.append(f"→ {rec['to']}: {rec['task']}")
    elif rec.get("event") == "agent_start":
        said.append(rec.get("task", ""))
    elif rec.get("event") == "agent_result":
        said.append(json.dumps(rec.get("output"), default=str))
    elif rec.get("event") == "run_error":
        said.append(rec.get("text", ""))
    return {"run_id": rec.get("run_id"), "ticket_id": rec.get("ticket_id"), "agent": rec.get("agent"),
            "depth": rec.get("depth"), "event": rec.get("event"), "logged_at": rec.get("logged_at"),
            "to": rec.get("to"), "said": said, "tools": tools,
            "output": rec.get("output") if rec.get("event") == "agent_result" else None}


@app.get("/events")
async def events(since: int = 0, limit: int = 200, ticket_id: int | None = None, run_id: str | None = None):
    """Agent events from output/audit_trail.json after index `since` (use `next` to poll)."""
    trail = json.loads(audit.AUDIT_PATH.read_text()) if audit.AUDIT_PATH.exists() else []
    out = []
    for idx in range(since, len(trail)):
        rec = trail[idx]
        if ticket_id is not None and rec.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and rec.get("run_id") != run_id:
            continue
        if rec.get("event") in ("user_prompt", "agent_end"):
            continue  # no content for the board
        out.append({"index": idx, **_summarize(rec)})
    return {"events": out[-limit:], "next": len(trail)}


# --------------------------------------------------------------- payments


class Decision(BaseModel):
    by: str = "human"
    note: str = ""


@app.get("/payment_requests")
async def payment_requests(status: str | None = None):
    """Payment and purchase-order requests the agents prepared (filter with ?status=pending)."""
    return await mcp("list_payment_requests", **({"status": status} if status else {}))


@app.post("/payment_requests/{request_id}/approve")
async def approve(request_id: int, decision: Decision = Decision()):
    """Human approval: the only route that changes cash. Refuses if cash would go negative."""
    result = await mcp("approve_payment", payment_request_id=request_id, approved_by=decision.by)
    audit.append({"run_id": None, "ticket_id": None, "agent": "human", "event": "payment_approved"
                  if result.get("ok") else "payment_refused", "payment_request_id": request_id,
                  "by": decision.by, "output": result})
    if not result.get("ok"):
        raise HTTPException(409, result)
    return result


@app.post("/payment_requests/{request_id}/reject")
async def reject(request_id: int, decision: Decision = Decision()):
    """Human rejection: no money moves."""
    result = await mcp("reject_payment", payment_request_id=request_id, rejected_by=decision.by,
                       note=decision.note or "rejected by human")
    audit.append({"run_id": None, "ticket_id": None, "agent": "human", "event": "payment_rejected",
                  "payment_request_id": request_id, "by": decision.by, "output": result})
    if not result.get("ok"):
        raise HTTPException(409, result)
    return result


# ------------------------------------------------------------------- cash


@app.get("/cash")
async def cash():
    """Current checking balance from cash_accounts, plus pending requests."""
    pos = await mcp("get_cash_position")
    checking = next((a for a in pos["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "no checking account")
    return {"account": "checking", "balance": checking["balance"], "as_of": checking["date"],
            "pending_requests_total": checking["pending_requests_total"],
            "balance_if_all_pending_approved": checking["balance_if_all_pending_approved"],
            "payments_made": pos["payments_made"]}


# ------------------------------------------------------------------ reset


@app.post("/reset")
async def reset():
    """Copy data/campus_customs.db over the working copy. The audit trail is kept (append-only)."""
    if _active_runs():
        raise HTTPException(409, "an agent run is in progress; wait for it to finish")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    runs.clear()
    audit.append({"run_id": None, "ticket_id": None, "agent": "human", "event": "db_reset",
                  "text": "data/campus_customs_new.db reset from data/campus_customs.db"})
    return {"ok": True, "message": "Working database reset to original values."}


@app.get("/health")
async def health():
    return {"ok": True}
