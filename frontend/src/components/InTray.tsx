import { useState } from 'react'
import type { Cash, Draft, PaymentRequest } from '../api'
import { AGENTS, money } from '../agents'
import type { AgentName } from '../api'

const KIND: Record<PaymentRequest['kind'], string> = {
  invoice: 'Vendor invoice',
  rent: 'Rent',
  purchase_order: 'Purchase order',
}

// The in-tray: everything waiting for a human signature, plus the drafts nobody has sent.
export function InTray({ pending, selected, drafts, cash, onDecide }: {
  pending: PaymentRequest[]
  selected: number | null
  drafts: Draft[]
  cash: Cash | null
  onDecide: (r: PaymentRequest, approve: boolean) => Promise<void>
}) {
  const [busy, setBusy] = useState<number | null>(null)
  const [stamped, setStamped] = useState<number | null>(null)
  const sorted = [...pending].sort((a, b) => Number(b.ticket_id === selected) - Number(a.ticket_id === selected))

  const act = async (r: PaymentRequest, approve: boolean) => {
    setBusy(r.id)
    if (approve) setStamped(r.id)
    await onDecide(r, approve)
    setBusy(null); setStamped(null)
  }

  return (
    <aside className="tray">
      <div className="tray-section">
        <div className="rail-head"><h3>In-tray</h3><span>{pending.length} awaiting signature</span></div>
        {pending.length === 0 && <div className="tray-empty">Nothing to sign. Agents can only <i>prepare</i> payments — they land here for you.</div>}
        {sorted.map(r => {
          const over = cash != null && r.amount > cash.balance
          const who = AGENTS[r.requested_by as AgentName]
          return (
            <div key={r.id} className={`cheque ${r.ticket_id === selected ? 'mine' : ''} ${stamped === r.id ? 'stamping' : ''}`}>
              <div className="cheque-top">
                <span>{KIND[r.kind]} · req #{r.id}</span>
                {r.ticket_id && <span className="tag">ticket #{r.ticket_id}</span>}
              </div>
              <div className="cheque-amount">{money(r.amount)}</div>
              <div className="cheque-reason">{r.reason}</div>
              <div className="cheque-by">prepared by {who ? <b style={{ color: who.color }}>{who.glyph} {who.label}</b> : r.requested_by}</div>
              {over && <div className="warn">Checking has only {money(cash!.balance)} — the till will refuse this.</div>}
              <div className="cheque-actions">
                <button className="approve" disabled={busy != null} onClick={() => act(r, true)}>Approve & pay</button>
                <button className="ghost small" disabled={busy != null} onClick={() => act(r, false)}>Decline</button>
              </div>
              {stamped === r.id && <div className="paid-stamp">Approved</div>}
            </div>
          )
        })}
      </div>

      <div className="tray-section">
        <div className="rail-head"><h3>Outbox</h3><span>drafts · never sent</span></div>
        {drafts.length === 0 && <div className="tray-empty">No drafts for this ticket yet.</div>}
        {drafts.map(d => (
          <details key={d.id} className="envelope">
            <summary>
              <span className="env-to">To: {d.recipient}</span>
              <span className="env-subj">{d.subject}</span>
              <span className="env-flag">DRAFT</span>
            </summary>
            <p>{d.body}</p>
            <small>written by {AGENTS[d.author as AgentName]?.label ?? d.author}</small>
          </details>
        ))}
      </div>
    </aside>
  )
}
