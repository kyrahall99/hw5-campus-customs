"""Campus Customs agent team: Boss, Inventory, Accounting, Facilities, Customer Service.

Every agent:
  * runs on gpt-6-luna through Portkey (the only model used anywhere),
  * gets its shop tools from the campus-customs MCP server (no other tools layer),
  * can delegate to any other agent (full connectivity) via the `delegate` tool,
  * logs every agent-loop step to output/audit_trail.json.
"""

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from . import audit
from .models import AGENT_NAMES, AgentName, AgentReport, TeamDeps, TicketResolution

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
load_dotenv(ROOT / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = "gpt-6-luna"  # the only model allowed in this assignment
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# Guardrails on cost and runaway delegation.
MAX_DELEGATION_DEPTH = 3     # boss -> a -> b -> c, then no further hand-offs
MAX_DELEGATIONS_PER_TICKET = 8
TICKET_USAGE_LIMITS = UsageLimits(request_limit=60, tool_calls_limit=80, total_tokens_limit=250_000)
AGENT_MAX_TOKENS = 2_000     # cap on each model response

# Tools only a human may call (exposed by the MCP server, hidden from every agent).
HUMAN_ONLY_TOOLS = {"approve_payment", "reject_payment"}


def build_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Add it to hw5/.env.")
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key="portkey",  # unused by Portkey; auth is the header below
        default_headers={"x-portkey-api-key": api_key},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def build_mcp_toolset() -> MCPToolset:
    """Connect to the campus-customs MCP server over stdio (same server Claude Code uses)."""
    transport = StdioTransport(
        command=str(ROOT / ".venv" / "bin" / "python"),
        args=[str(ROOT / "mcp_server" / "server.py")],
        cwd=str(ROOT),
    )
    return MCPToolset(transport, id="campus-customs")


class Team:
    """The five agents, sharing one model and one MCP connection."""

    def __init__(self) -> None:
        self.model = build_model()
        self.mcp = build_mcp_toolset()
        agent_tools = self.mcp.filtered(lambda ctx, tool: tool.name not in HUMAN_ONLY_TOOLS)
        self.agents: dict[AgentName, Agent[TeamDeps, AgentReport | TicketResolution]] = {}
        for name in AGENT_NAMES:
            agent = Agent(
                self.model,
                name=name,
                deps_type=TeamDeps,
                output_type=TicketResolution if name == "boss" else AgentReport,
                instructions=(PROMPTS_DIR / f"{name}.md").read_text(),
                toolsets=[agent_tools],
                model_settings={"max_tokens": AGENT_MAX_TOKENS},
                retries=2,
            )
            agent.tool(self._delegate_tool(name))
            self.agents[name] = agent

    @asynccontextmanager
    async def connected(self):
        """Hold the MCP server open for the whole team run."""
        async with self.mcp:
            yield self

    def _delegate_tool(self, me: AgentName):
        async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> str:
            """Hand a specific task to another teammate and get their report back.

            Args:
                to: one of boss, inventory, accounting, facilities, customer_service.
                task: exactly what you need, including the ticket id and the SKU/size/qty,
                    lease id, or invoice id involved.
            """
            deps = ctx.deps
            if to == me:
                return "Refused: you cannot delegate to yourself."
            if deps.depth + 1 > MAX_DELEGATION_DEPTH:
                return f"Refused: delegation depth limit ({MAX_DELEGATION_DEPTH}) reached. Finish with what you have."
            if deps.delegations[0] >= MAX_DELEGATIONS_PER_TICKET:
                return f"Refused: delegation budget ({MAX_DELEGATIONS_PER_TICKET}) for this ticket is used up."
            deps.delegations[0] += 1
            child = TeamDeps(
                run_id=deps.run_id,
                ticket_id=deps.ticket_id,
                depth=deps.depth + 1,
                chain=[*deps.chain, to],
                delegations=deps.delegations,
            )
            audit.append({"run_id": deps.run_id, "ticket_id": deps.ticket_id, "agent": me, "depth": deps.depth,
                          "event": "delegate", "to": to, "task": task})
            report = await self.run_agent(to, task, child, usage=ctx.usage)
            return report.model_dump_json()

        delegate.__name__ = "delegate"
        return delegate

    async def run_agent(self, name: AgentName, task: str, deps: TeamDeps, usage=None):
        """The agent loop: step through model calls and tool calls, logging every step."""
        agent = self.agents[name]
        base = {"run_id": deps.run_id, "ticket_id": deps.ticket_id, "agent": name, "depth": deps.depth,
                "chain": deps.chain}
        audit.append({**base, "event": "agent_start", "model": MODEL_NAME, "task": task})
        step = 0
        async with agent.iter(task, deps=deps, usage=usage, usage_limits=TICKET_USAGE_LIMITS) as run:
            async for node in run:
                step += 1
                record = {**base, "step": step, "node": type(node).__name__}
                if Agent.is_model_request_node(node):
                    record["event"] = "model_request"
                    record["inputs"] = _describe_request(node.request.parts)
                elif Agent.is_call_tools_node(node):
                    record["event"] = "model_response"
                    record["outputs"] = _describe_response(node.model_response.parts)
                elif Agent.is_end_node(node):
                    record["event"] = "agent_end"
                else:
                    record["event"] = "user_prompt"
                u = run.usage
                record["usage"] = {"requests": u.requests, "input_tokens": u.input_tokens,
                                   "output_tokens": u.output_tokens, "tool_calls": u.tool_calls}
                audit.append(record)
            output = run.result.output
        audit.append({**base, "event": "agent_result", "output": output.model_dump()})
        return output

    async def work_ticket(self, ticket_id: int, run_id: str | None = None) -> TicketResolution:
        """Boss takes one ticket end to end."""
        deps = TeamDeps(run_id=run_id or uuid.uuid4().hex[:12], ticket_id=ticket_id, chain=["boss"])
        task = (f"Work ticket {ticket_id}. Read it, involve the right teammates, make the final call, "
                f"update the ticket, and return your TicketResolution.")
        return await self.run_agent("boss", task, deps)


def _describe_request(parts) -> list[dict]:
    out = []
    for p in parts:
        if isinstance(p, ToolReturnPart):
            out.append({"type": "tool_return", "tool": p.tool_name, "tool_call_id": p.tool_call_id,
                        "output": audit._clip(p.content)})
        elif isinstance(p, RetryPromptPart):
            out.append({"type": "retry", "tool": p.tool_name, "output": audit._clip(str(p.content))})
        elif isinstance(p, UserPromptPart):
            out.append({"type": "user_prompt", "text": audit._clip(str(p.content))})
    return out


def _describe_response(parts) -> list[dict]:
    out = []
    for p in parts:
        if isinstance(p, ToolCallPart):
            out.append({"type": "tool_call", "tool": p.tool_name, "tool_call_id": p.tool_call_id,
                        "args": audit._clip(p.args_as_dict())})
        elif isinstance(p, TextPart):
            out.append({"type": "text", "text": audit._clip(p.content)})
    return out


async def work_tickets(ticket_ids: list[int]) -> list[TicketResolution]:
    team = Team()
    results = []
    async with team.connected():
        for tid in ticket_ids:
            results.append(await team.work_ticket(tid))
    return results


if __name__ == "__main__":
    import asyncio
    import sys

    ids = [int(a) for a in sys.argv[1:]] or [101, 102, 103]
    for r in asyncio.run(work_tickets(ids)):
        print(r.model_dump_json(indent=2))
