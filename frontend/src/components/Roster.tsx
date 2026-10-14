import { AGENTS, AGENT_ORDER } from '../agents'
import type { AgentName } from '../api'

export type AgentState = 'idle' | 'working' | 'speaking' | 'done'

const STATE_TEXT: Record<AgentState, string> = {
  idle: 'at their desk',
  working: 'on it',
  speaking: 'working now',
  done: 'reported back',
}

// Five desk lamps: an agent's lamp lights when they're pulled in, glows while they work.
export function Roster({ states }: { states: Record<AgentName, AgentState> }) {
  return (
    <div className="roster">
      {AGENT_ORDER.map(name => {
        const a = AGENTS[name]
        const s = states[name]
        return (
          <div key={name} className={`lamp ${s}`} style={{ '--ink': a.color, '--tint': a.tint } as React.CSSProperties}>
            <div className="lamp-glyph">{a.glyph}</div>
            <div>
              <div className="lamp-name">{a.label}</div>
              <div className="lamp-state">{s === 'idle' ? a.role : STATE_TEXT[s]}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
