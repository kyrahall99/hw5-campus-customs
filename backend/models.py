"""Data types shared by the Campus Customs agent team."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")


class AgentReport(BaseModel):
    """What a specialist hands back to whoever delegated to it."""

    agent: AgentName
    ticket_id: int | None = None
    summary: str = Field(description="One or two sentences: what you found and did.")
    facts: list[str] = Field(
        default_factory=list,
        description="Facts you verified with MCP tools, each citing the number from the database.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Database changes you made via tools (payment request ids, PO ids, draft ids, ticket updates).",
    )
    needs_human_approval: list[int] = Field(
        default_factory=list, description="payment_requests.id values waiting on a human."
    )
    blockers: list[str] = Field(default_factory=list, description="Anything stopping the work.")
    recommendation: str | None = Field(default=None, description="Your suggestion for the Boss's final call.")


class TicketResolution(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    decision: str = Field(description="The final call in plain words.")
    agents_used: list[AgentName] = Field(default_factory=list)
    status: Literal["in_progress", "waiting_approval", "resolved"] = Field(
        description="waiting_approval if any payment request is pending a human."
    )
    pending_payment_request_ids: list[int] = Field(default_factory=list)
    purchase_order_ids: list[int] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list)
    reasoning: str = Field(description="Why, citing the database facts the team relied on.")
    next_steps: list[str] = Field(default_factory=list)


@dataclass
class TeamDeps:
    """Per-run state passed to every agent in a delegation chain."""

    run_id: str
    ticket_id: int | None = None
    depth: int = 0
    chain: list[AgentName] = field(default_factory=list)
    delegations: list[int] = field(default_factory=lambda: [0])  # shared counter (list so it's shared by reference)
