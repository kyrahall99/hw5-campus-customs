import type { AgentName, AgentReport, TicketResolution } from '../api'
import { AGENTS, AGENT_ORDER } from '../agents'

// After the run: one index card per agent that worked the ticket, Boss's call on top.
export function Summary({ results }: { results: Partial<Record<AgentName, AgentReport | TicketResolution>> }) {
  const boss = results.boss as TicketResolution | undefined
  const crew = AGENT_ORDER.filter(a => a !== 'boss' && results[a]) as AgentName[]
  const skipped = AGENT_ORDER.filter(a => a !== 'boss' && !results[a])

  return (
    <div className="summary">
      <div className="feed-head"><h3>Who did what</h3><span>{crew.length} specialist{crew.length === 1 ? '' : 's'} called</span></div>
      {boss && (
        <div className="card boss-card" style={{ '--ink': AGENTS.boss.color, '--tint': AGENTS.boss.tint } as React.CSSProperties}>
          <div className="card-who">★ Boss · final call <span className={`status-tag ${boss.status}`}>{boss.status.replace('_', ' ')}</span></div>
          <p className="decision">{boss.decision}</p>
          <p className="reasoning">{boss.reasoning}</p>
          {boss.next_steps.length > 0 && <ul>{boss.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>}
        </div>
      )}
      <div className="cards">
        {crew.map(name => {
          const a = AGENTS[name]
          const r = results[name] as AgentReport
          return (
            <div key={name} className="card" style={{ '--ink': a.color, '--tint': a.tint } as React.CSSProperties}>
              <div className="card-who">{a.glyph} {a.label}</div>
              <p>{r.summary}</p>
              {r.actions_taken?.length > 0 && <ul className="did">{r.actions_taken.slice(0, 4).map((x, i) => <li key={i}>{x}</li>)}</ul>}
              {r.blockers?.length > 0 && <div className="blocker">⚠ {r.blockers[0]}</div>}
            </div>
          )
        })}
      </div>
      {skipped.length > 0 && (
        <p className="skipped">Not needed on this ticket: {skipped.map(a => AGENTS[a].label).join(', ')}.</p>
      )}
    </div>
  )
}
