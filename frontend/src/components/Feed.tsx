import { useEffect, useRef } from 'react'
import type { AgentEvent, AgentName, AgentReport, TicketResolution, ToolUse } from '../api'
import { AGENTS, toolLabel } from '../agents'

const look = (a: string) => AGENTS[a as AgentName]

function brief(v: unknown, max = 150): string {
  if (v == null) return ''
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > max ? s.slice(0, max) + '…' : s
}

function argText(args: unknown): string {
  if (!args || typeof args !== 'object') return ''
  return Object.entries(args as Record<string, unknown>)
    .filter(([k]) => !['created_by', 'requested_by', 'author', 'agent', 'body'].includes(k))
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}

function ToolChip({ t }: { t: ToolUse }) {
  if (t.tool === 'delegate') return null // shown as a passed note instead
  if ('args' in t) {
    if (t.tool === 'final_result') return <span className="chip filing">✎ files report</span>
    return <span className="chip call" title={brief(t.args, 600)}>⚙ {toolLabel(t.tool)}<i>{brief(argText(t.args), 70)}</i></span>
  }
  if (t.tool === 'delegate' || t.tool === 'final_result') return null
  return <span className="chip result" title={brief(t.result, 1200)}>↳ {toolLabel(t.tool)} → <i>{brief(t.result, 90)}</i></span>
}

function Line({ e }: { e: AgentEvent }) {
  const a = look(e.agent)
  if (!a) return null
  const style = { '--ink': a.color, '--tint': a.tint, '--indent': `${(e.depth ?? 0) * 18}px` } as React.CSSProperties

  if (e.event === 'delegate' && e.to) {
    const to = look(e.to)
    return (
      <div className="note-pass" style={style}>
        <div className="note-route"><b style={{ color: a.color }}>{a.glyph} {a.label}</b> passes a note to <b style={{ color: to.color }}>{to.glyph} {to.label}</b></div>
        <div className="note-body">{e.said[0]?.replace(/^→ [a-z_]+: /, '')}</div>
      </div>
    )
  }

  if (e.event === 'agent_result' && e.output) {
    const o = e.output as AgentReport & TicketResolution
    const isBoss = e.agent === 'boss'
    return (
      <div className={`said ${isBoss ? 'verdict' : 'report'} voice-${a.voice}`} style={style}>
        <div className="who"><span className="glyph">{a.glyph}</span>{a.label}<small>{isBoss ? 'final call' : 'reports back'}</small></div>
        <p>{isBoss ? o.decision : o.summary}</p>
      </div>
    )
  }

  const texts = e.said.filter(Boolean)
  const tools = e.tools.filter(t => t.tool !== 'delegate')
  if (e.event === 'agent_start') return null
  if (!texts.length && !tools.length) return null

  return (
    <div className={`said voice-${a.voice}`} style={style}>
      <div className="who"><span className="glyph">{a.glyph}</span>{a.label}</div>
      {texts.map((t, i) => <p key={i}>{t}</p>)}
      {tools.length > 0 && <div className="chips">{tools.map((t, i) => <ToolChip key={i} t={t} />)}</div>}
    </div>
  )
}

export function Feed({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { if (running) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [events.length, running])

  return (
    <div className="feed">
      <div className="feed-head">
        <h3>The floor</h3>
        <span>{running ? 'live' : events.length ? 'last run' : 'quiet'}</span>
      </div>
      {events.length === 0 && (
        <div className="feed-empty">
          {running ? 'The Boss is reading the ticket…' : 'Nobody has worked this ticket yet. Hand it to the team to watch them think out loud.'}
        </div>
      )}
      {events.map(e => <Line key={e.index} e={e} />)}
      {running && <div className="typing"><span /><span /><span /></div>}
      <div ref={end} />
    </div>
  )
}
