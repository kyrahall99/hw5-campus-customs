import type { AgentName } from './api'

export interface AgentLook {
  name: AgentName
  label: string
  role: string
  glyph: string
  color: string // ink color for this agent's voice
  tint: string // paper tint behind their lines
  voice: 'command' | 'ledger' | 'stock' | 'building' | 'letter'
}

// Each agent gets its own ink, glyph, and "voice" so you can tell who is talking at a glance.
export const AGENTS: Record<AgentName, AgentLook> = {
  boss: { name: 'boss', label: 'Boss', role: 'Makes the final call', glyph: '★', color: '#13306b', tint: '#e7edf8', voice: 'command' },
  inventory: { name: 'inventory', label: 'Inventory', role: 'Stock · vendors · restock', glyph: '▦', color: '#0e6b62', tint: '#e2f2ef', voice: 'stock' },
  accounting: { name: 'accounting', label: 'Accounting', role: 'Cash · invoices · margins', glyph: '$', color: '#7a5a00', tint: '#f7efd9', voice: 'ledger' },
  facilities: { name: 'facilities', label: 'Facilities', role: 'Lease · rent · the shop', glyph: '⌂', color: '#a2421f', tint: '#f8e8e0', voice: 'building' },
  customer_service: { name: 'customer_service', label: 'Customer Service', role: 'Drafts every message', glyph: '✉', color: '#7b3584', tint: '#f3e6f4', voice: 'letter' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TICKET_KIND: Record<string, { label: string; glyph: string }> = {
  customer_order: { label: 'Customer order', glyph: '👕' },
  rent_notice: { label: 'Rent notice', glyph: '🏠' },
  price_override: { label: 'Discount request', glyph: '🏷️' },
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

export const toolLabel = (tool: string) => tool.replace(/_/g, ' ')
