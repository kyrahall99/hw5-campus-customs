import type { TicketSummary } from '../api'
import { TICKET_KIND } from '../agents'

// Tickets hang on the order spike like paper slips; resolved ones get a rubber stamp.
export function TicketRail({ tickets, selected, live, onSelect }: {
  tickets: TicketSummary[]
  selected: number | null
  live: number | null
  onSelect: (id: number) => void
}) {
  const open = tickets.filter(t => !t.resolved).length
  return (
    <aside className="rail">
      <div className="rail-head">
        <h3>On the spike</h3>
        <span>{open} open · {tickets.length - open} resolved</span>
      </div>
      {tickets.map((t, i) => {
        const kind = TICKET_KIND[t.type]
        return (
          <button
            key={t.id}
            className={`slip ${selected === t.id ? 'selected' : ''} ${t.resolved ? 'resolved' : ''} ${live === t.id ? 'live' : ''}`}
            style={{ '--tilt': `${[-1.2, 0.8, -0.4][i % 3]}deg` } as React.CSSProperties}
            onClick={() => onSelect(t.id)}
          >
            <div className="slip-top">
              <span className="slip-no">#{t.id}</span>
              <span className="slip-kind">{kind?.glyph} {kind?.label ?? t.type}</span>
            </div>
            <div className="slip-subject">{t.subject}</div>
            <div className="slip-from">{t.requester}</div>
            <div className="slip-status">
              {live === t.id ? <><span className="dot" /> team working</> : t.status.replace('_', ' ')}
            </div>
            {t.resolved && <div className="stamp">Resolved</div>}
          </button>
        )
      })}
    </aside>
  )
}
