import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type AgentEvent, type AgentName, type AgentReport, type Cash, type PaymentRequest, type TicketDetail, type TicketResolution, type TicketSummary } from './api'
import { AGENTS, AGENT_ORDER, TICKET_KIND, money } from './agents'
import { CashRegister } from './components/CashRegister'
import { Feed } from './components/Feed'
import { InTray } from './components/InTray'
import { Roster, type AgentState } from './components/Roster'
import { Summary } from './components/Summary'
import { TicketRail } from './components/TicketRail'

const POLL_MS = 1200

interface LiveRun { runId: string; ticketId: number; startedAt: number }

export default function App() {
  const [tickets, setTickets] = useState<TicketSummary[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [pending, setPending] = useState<PaymentRequest[]>([])
  const [live, setLive] = useState<LiveRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [signer, setSigner] = useState(() => localStorage.getItem('cc-signer') ?? 'Desk manager')
  const [now, setNow] = useState(Date.now())
  const cursor = useRef(0)
  const liveRef = useRef<LiveRun | null>(null)
  liveRef.current = live

  const flash = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3800) }

  const refreshBoard = useCallback(async () => {
    try {
      const [t, c, p] = await Promise.all([api.tickets(), api.cash(), api.pending()])
      setTickets(t); setCash(c); setPending(p); setError(null)
      setSelected(s => s ?? t.find(x => !x.resolved)?.id ?? t[0]?.id ?? null)
    } catch (e) {
      setError(`Can't reach the backend at localhost:8000 — is uvicorn running? (${(e as Error).message})`)
    }
  }, [])

  const refreshDetail = useCallback(async (id: number) => {
    try { setDetail(await api.ticket(id)) } catch { /* board-level error already shown */ }
  }, [])

  // Load the most recent run's events for a ticket (so history is visible after a reload).
  const loadHistory = useCallback(async (id: number) => {
    const { events: evs, next } = await api.events({ ticket_id: id, limit: 2000 })
    cursor.current = next
    const l = liveRef.current
    const lastRun = l && l.ticketId === id ? l.runId : [...evs].reverse().find(e => e.run_id)?.run_id
    setEvents(lastRun ? evs.filter(e => e.run_id === lastRun) : [])
  }, [])

  useEffect(() => { refreshBoard(); const t = setInterval(refreshBoard, 4000); return () => clearInterval(t) }, [refreshBoard])

  useEffect(() => {
    if (selected == null) return
    refreshDetail(selected)
    loadHistory(selected)
  }, [selected, refreshDetail, loadHistory])

  // While a run is live: stream new events and watch for the finish.
  useEffect(() => {
    if (!live) return
    let stop = false
    const tick = async () => {
      if (stop) return
      setNow(Date.now())
      try {
        const { events: evs, next } = await api.events({ since: cursor.current, ticket_id: live.ticketId })
        cursor.current = next
        const mine = evs.filter(e => e.run_id === live.runId)
        if (mine.length && selected === live.ticketId) setEvents(prev => [...prev, ...mine])
        const run = await api.runStatus(live.runId)
        if (run.status !== 'running') {
          setLive(null)
          liveRef.current = null
          await Promise.all([refreshBoard(), refreshDetail(live.ticketId)])
          if (selected === live.ticketId) await loadHistory(live.ticketId)
          if (run.status === 'error') setError(`Run failed: ${run.error}`)
          else flash(`Ticket #${live.ticketId} resolved — check the in-tray for anything that needs your signature.`)
        }
      } catch (e) { setError((e as Error).message) }
    }
    const t = setInterval(tick, POLL_MS)
    return () => { stop = true; clearInterval(t) }
  }, [live, selected, refreshBoard, refreshDetail, loadHistory])

  const start = async () => {
    if (selected == null) return
    try {
      setEvents([]); setError(null)
      const { next } = await api.events({ since: 0, limit: 1 })
      cursor.current = next
      const { run_id } = await api.run(selected)
      setLive({ runId: run_id, ticketId: selected, startedAt: Date.now() })
    } catch (e) { setError((e as Error).message) }
  }

  const decide = async (req: PaymentRequest, approve: boolean) => {
    try {
      if (approve) {
        const r = await api.approve(req.id, signer)
        flash(`Paid ${money(r.amount)} — checking now ${money(r.new_balance)}.`)
      } else {
        await api.reject(req.id, signer, 'Declined at the desk')
        flash(`Request #${req.id} declined. No money moved.`)
      }
    } catch (e) {
      setError(`Request #${req.id}: ${(e as Error).message}`)
    }
    await refreshBoard()
    if (selected != null) refreshDetail(selected)
  }

  const reset = async () => {
    if (!confirm('Reset the working database to the original shop data? Payments, drafts and ticket notes from earlier runs will be cleared (the audit trail is kept).')) return
    try {
      await api.reset(); setEvents([]); setDetail(null)
      await refreshBoard(); if (selected != null) refreshDetail(selected)
      flash('Fresh day at the desk — database reset to the original values.')
    } catch (e) { setError((e as Error).message) }
  }

  // Derive each agent's state from the event stream.
  const states = useMemo(() => {
    const s = Object.fromEntries(AGENT_ORDER.map(a => [a, 'idle'])) as Record<AgentName, AgentState>
    for (const e of events) {
      if (!(e.agent in AGENTS)) continue
      const a = e.agent as AgentName
      if (e.event === 'agent_start') s[a] = 'working'
      if (e.event === 'agent_result') s[a] = 'done'
    }
    if (live) {
      const last = [...events].reverse().find(e => e.agent in AGENTS && s[e.agent as AgentName] === 'working')
      if (last) s[last.agent as AgentName] = 'speaking'
    }
    return s
  }, [events, live])

  const results = useMemo(() => {
    const r: Partial<Record<AgentName, AgentReport | TicketResolution>> = {}
    for (const e of events) if (e.event === 'agent_result' && e.output && e.agent in AGENTS) r[e.agent as AgentName] = e.output
    return r
  }, [events])

  const current = tickets.find(t => t.id === selected)
  const running = live?.ticketId === selected
  const busyElsewhere = !!live && !running
  const elapsed = live ? Math.round((now - live.startedAt) / 1000) : 0

  return (
    <div className="desk">
      <header className="topbar">
        <div className="brand">
          <span className="crest">CC</span>
          <div>
            <h1>Campus Customs</h1>
            <p>Operations Desk · Chapel Street, New Haven</p>
          </div>
        </div>
        <div className="shopdate">
          <span>Shop date</span>
          <b>{cash?.as_of ?? '—'}</b>
        </div>
        <CashRegister cash={cash} />
        <div className="desk-controls">
          <label className="signer">
            <span>Signing as</span>
            <input value={signer} onChange={e => { setSigner(e.target.value); localStorage.setItem('cc-signer', e.target.value) }} />
          </label>
          <button className="ghost" onClick={reset} disabled={!!live} title="Copy campus_customs.db over the working copy">↺ New day</button>
        </div>
      </header>

      {error && <div className="banner" onClick={() => setError(null)}>{error}<span>dismiss</span></div>}

      <main className="surface">
        <TicketRail tickets={tickets} selected={selected} live={live?.ticketId ?? null} onSelect={setSelected} />

        <section className="floor">
          {current ? (
            <>
              <div className="floor-head">
                <div>
                  <div className="eyebrow">{TICKET_KIND[current.type]?.glyph} {TICKET_KIND[current.type]?.label ?? current.type} · #{current.id}</div>
                  <h2>{current.subject}</h2>
                  <p className="from">from <b>{current.requester}</b>{detail?.ticket.sku && <> · {detail.ticket.qty} × {detail.ticket.sku} ({detail.ticket.size})</>}</p>
                  {detail?.ticket.notes && <p className="ticket-note">“{detail.ticket.notes.split('\n')[0]}”</p>}
                </div>
                <div className="run-box">
                  {running ? (
                    <div className="running-pill"><span className="dot" /> Team at work · {elapsed}s</div>
                  ) : (
                    <button className="primary" onClick={start} disabled={busyElsewhere}>
                      {busyElsewhere ? `Team busy on #${live!.ticketId}` : current.resolved ? 'Run the team again' : 'Hand to the team →'}
                    </button>
                  )}
                  <small>Boss reads it first and decides who helps.</small>
                </div>
              </div>

              <Roster states={states} />
              <Feed events={events} running={running} />
              {!running && Object.keys(results).length > 0 && <Summary results={results} />}
            </>
          ) : (
            <div className="empty">Pick a ticket from the spike.</div>
          )}
        </section>

        <InTray pending={pending} selected={selected} drafts={detail?.drafts ?? []} onDecide={decide} cash={cash} />
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
