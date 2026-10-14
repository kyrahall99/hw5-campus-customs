// Thin client for the FastAPI backend (backend/main.py).
export const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface TicketSummary {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  resolved: boolean
}

export interface Draft {
  id: number
  ticket_id: number
  audience: string
  recipient: string
  subject: string
  body: string
  author: string
  created_at: string
}

export interface PaymentRequest {
  id: number
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number
  amount: number
  account: string
  ticket_id: number | null
  reason: string
  requested_by: string
  status: 'pending' | 'paid' | 'rejected' | 'refused'
  decided_by: string | null
  decision_note: string | null
}

export interface TicketDetail {
  found: boolean
  ticket: TicketSummary & { sku: string | null; size: string | null; qty: number | null; notes: string | null; created_at: string; lease_id: number | null; invoice_id: number | null }
  lease?: Record<string, unknown> | null
  invoice?: Record<string, unknown> | null
  drafts: Draft[]
  payment_requests: PaymentRequest[]
  purchase_orders: Record<string, unknown>[]
}

export interface ToolUse {
  tool: string
  args?: unknown
  result?: unknown
}

export interface AgentEvent {
  index: number
  run_id: string | null
  ticket_id: number | null
  agent: AgentName | 'human' | 'system'
  depth: number | null
  event: string
  logged_at: string
  to?: AgentName | null
  said: string[]
  tools: ToolUse[]
  output?: AgentReport | TicketResolution | null
}

export interface AgentReport {
  agent: AgentName
  summary: string
  facts: string[]
  actions_taken: string[]
  needs_human_approval: number[]
  blockers: string[]
  recommendation: string | null
}

export interface TicketResolution {
  ticket_id: number
  decision: string
  agents_used: AgentName[]
  status: string
  pending_payment_request_ids: number[]
  purchase_order_ids: number[]
  draft_ids: number[]
  reasoning: string
  next_steps: string[]
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_requests_total: number
  balance_if_all_pending_approved: number
  payments_made: { id: number; kind: string; ref_id: number; amount: number; paid_at: string; approved_by: string }[]
}

export interface Run {
  run_id: string
  ticket_id: number
  status: 'running' | 'done' | 'error'
  result: TicketResolution | null
  error: string | null
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const msg = typeof detail === 'string' ? detail : detail?.error ?? `${res.status} ${res.statusText}`
    throw new Error(msg)
  }
  return body as T
}

export const api = {
  tickets: () => call<TicketSummary[]>('/tickets'),
  ticket: (id: number) => call<TicketDetail>(`/tickets/${id}`),
  run: (id: number) => call<{ run_id: string }>(`/tickets/${id}/run`, { method: 'POST' }),
  runs: () => call<Run[]>('/runs'),
  runStatus: (runId: string) => call<Run>(`/runs/${runId}`),
  events: (params: { since?: number; ticket_id?: number; limit?: number }) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v !== undefined && q.set(k, String(v)))
    return call<{ events: AgentEvent[]; next: number }>(`/events?${q}`)
  },
  pending: () => call<PaymentRequest[]>('/payment_requests?status=pending'),
  approve: (id: number, by: string) =>
    call<{ ok: boolean; new_balance: number; amount: number }>(`/payment_requests/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ by }),
    }),
  reject: (id: number, by: string, note: string) =>
    call(`/payment_requests/${id}/reject`, { method: 'POST', body: JSON.stringify({ by, note }) }),
  cash: () => call<Cash>('/cash'),
  reset: () => call<{ ok: boolean }>('/reset', { method: 'POST' }),
}
