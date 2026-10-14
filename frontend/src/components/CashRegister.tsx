import { useEffect, useRef, useState } from 'react'
import type { Cash } from '../api'
import { money } from '../agents'

// The till: the balance rolls to its new value and flashes red when cash goes out.
export function CashRegister({ cash }: { cash: Cash | null }) {
  const target = cash?.balance ?? 0
  const [shown, setShown] = useState(target)
  const [dropped, setDropped] = useState(false)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    const from = prev.current ?? target
    prev.current = target
    if (from === target) { setShown(target); return }
    if (target < from) { setDropped(true); setTimeout(() => setDropped(false), 2200) }
    const t0 = performance.now()
    let raf = 0
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 1100)
      const ease = 1 - Math.pow(1 - k, 3)
      setShown(from + (target - from) * ease)
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, cash])

  const last = cash?.payments_made.at(-1)
  const low = cash != null && cash.balance < 500

  return (
    <div className={`register ${dropped ? 'dropped' : ''} ${low ? 'low' : ''}`}>
      <div className="register-label">
        <span>Checking</span>
        {cash && cash.pending_requests_total > 0 && (
          <em title="Balance if every pending request were approved">
            after pending: {money(cash.balance_if_all_pending_approved)}
          </em>
        )}
      </div>
      <div className="register-display">{cash ? money(shown) : '— — —'}</div>
      <div className="register-tape">
        {last ? <>last out: −{money(last.amount)} · {last.kind.replace('_', ' ')} #{last.ref_id}</> : 'no money out yet today'}
      </div>
    </div>
  )
}
