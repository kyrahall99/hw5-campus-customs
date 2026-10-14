# Campus Customs Operations Desk — Design

The dashboard is built as a **physical desk**: a dark felt blotter with paper on it. Tickets are order slips on a spike, agents pass sticky notes to each other, payments wait as cheques in an in-tray, and cash lives in a glowing till. Every element is something a shop manager already knows from a real counter, so the board can be read without learning a new interface. It also makes the work feel like a small team busy behind the counter, not a log file scrolling past.

## Layout

Three columns under a top bar, laid out the way a person scans a desk: what's waiting on the left, the work happening in front of you in the middle, and what needs your hand on the right.

| Zone | What it holds | Why |
|---|---|---|
| **Top bar** | Shop crest, the shop date (`desk.date_today`), the **cash register**, a "Signing as" name, and a **↺ New day** reset button | The things that are true for the whole shop stay in view at all times. The shop date is shown because it's the date every agent reasons from, not today's real date. |
| **Left: "On the spike"** | One paper slip per ticket, with its number, kind, subject, requester and status | A familiar picture for a queue. Each slip is tilted slightly differently, so the stack looks hand-placed and not like a spreadsheet. |
| **Center: "The floor"** | The selected ticket's header and its **Hand to the team →** button, the **agent roster**, the **live feed**, and, after a run, **"Who did what"** | This is where you watch the team think. It's the largest area because it's the main thing to look at. |
| **Right: "In-tray" and "Outbox"** | Payment and purchase-order requests waiting for a human, and the drafts saved for the selected ticket | Everything that needs a human sits in one place, and only there. Agents can only *prepare* actions; this is where a person signs off. |

On narrower screens, the tray moves under the floor as a two-column strip, so the feed never gets squeezed.

## How agents read differently

Each agent has its own **ink color, symbol and voice**, and they appear the same way everywhere: roster, feed, summary cards, cheques and envelopes.

| Agent | Symbol | Ink | Voice in the feed |
|---|---|---|---|
| Boss | ★ | Yale navy | Serif, larger type. The final call is a **solid navy card with brass**, the one dark message on a paper page, so the decision stands out from the discussion. |
| Inventory | ▦ | Teal | Plain, factual lines of stock and vendor checks |
| Accounting | $ | Ledger gold | Numbers in tabular figures so dollar amounts line up like a ledger |
| Facilities | ⌂ | Brick | Building and lease work |
| Customer Service | ✉ | Plum | Italic, like a handwritten note, since its job is writing letters |

- **The roster works like five desk lamps.** An agent's badge is grey and faded until it's pulled onto the ticket. It lights in its own color when it starts work, glows and lifts while it's the one currently working, and shows a ✓ "reported back" when it's done. Agents the Boss never called stay grey, so you can see at a glance that the Boss didn't send everyone to every ticket.
- **Hand-offs are sticky notes.** When one agent delegates, a yellow note slides in reading "★ Boss passes a note to ▦ Inventory", with the exact task in serif type. Agent-to-agent hand-offs, such as Inventory to Accounting, appear the same way, which shows the team can connect any agent to any other.
- **Indentation shows the chain.** Lines are indented by delegation depth, so it's clear who is working for whom.
- **Tools show up as chips.** A call looks like `⚙ check stock sku: CC-TEE-WHITE, size: S`, and its result appears underneath in dashed outline as `↳ check stock → {"qty":0…}`. Hovering over a chip shows the full arguments or result. Anyone can trace a claim back to the MCP tool that produced it, without the feed turning into a JSON dump.
- **Three bouncing dots** show while the team is still working, and the feed scrolls along with the action.

## How resolved tickets show up

- When a run finishes, the backend marks the ticket `resolved` and the slip gets a **red rubber "RESOLVED" stamp** that lands with a small animation. The slip also turns a slightly darker cream, like paper that's been handled.
- The floor then shows **"Who did what"**:
  - the Boss's card on top, with the decision, the reasoning, the next steps, and a status tag (amber "waiting approval" or green "resolved");
  - one index card for each specialist who worked, with its summary, what it did and any blocker;
  - a line saying who wasn't needed, for example "Not needed on this ticket: Facilities."
- A ticket's last run is reloaded from the audit trail, so the story is still there after a page refresh.
- **Drafts** appear in the Outbox as envelopes with a red **DRAFT** mark. You can open one to read the full message. Nothing is ever sent, and the label says so.

## How cash shows up

- **The till.** Checking is a green number on a dark screen, like an old cash register, in large monospace digits.
- When a payment is approved, the number **counts down** to the new balance, flashes red, and the register gives a little jolt, so you can see and almost feel the money leave. The register strip underneath records the last payment (for example "last out: −$840.00 · invoice #501").
- If checking drops below $500, the number turns **amber** as a warning.
- When requests are pending, a small gold line reads **"after pending: $X"**. It shows where the balance would land if you approved everything, because the shop has no incoming money.

## Approving money

- Each pending request is a **cheque** in the in-tray, showing:
  - the kind (vendor invoice, rent or purchase order) and the request number;
  - the amount in large type;
  - the agent's reason;
  - which agent prepared it, in that agent's color;
  - a gold tag linking it to its ticket.
- Cheques for the ticket you're looking at rise to the top with a brass outline.
- **Approve & pay** stamps a green **APPROVED** on the cheque and starts the till countdown. **Decline** just removes it without moving money.
- If a cheque is bigger than the money in checking, it warns in advance that "the till will refuse this". If you click anyway, the backend's refusal appears in a banner. The no-negative-balance rule is visible, not just enforced quietly.
- **"Signing as"** puts your name into the `approved_by` column of `payments`, so every payment can be traced to a person.

## Why these choices

- **A familiar setting beats a dashboard.** Slips, notes, cheques and stamps carry their meaning already. Nobody has to learn what a yellow sticky note being handed over means.
- **Paper on felt** gives strong contrast without harsh white, and the serif and sans pairing (Fraunces and Inter, with JetBrains Mono for numbers and tools) makes it feel like a well-made shop, not an admin panel.
- **Motion only where something actually happened:** a note sliding in, a lamp lighting, a stamp landing, the till counting down. Each animation marks a real change, so the board can be glanced at from across the room.
- **Money is the most serious thing on the page.** It has its own instrument (the till) and its own physical step (signing a cheque), and it's the only place a human click changes the database. That puts the "human approves every payment" rule right into the layout.
- **The details are there when you want them.** The surface shows plain sentences, and hovering a chip or opening an envelope shows the exact arguments, results and full drafts.

## Tech

React 19, Vite and TypeScript in `frontend/`, using the fonts `@fontsource-variable/fraunces`, `inter` and `jetbrains-mono` and no other UI libraries. The app talks to the FastAPI backend at `http://localhost:8000` (`VITE_API_URL`), and the backend allows the Vite origin `http://localhost:5173` through CORS. While a run is live, the board checks for new events every 1.2 seconds; otherwise it refreshes tickets, cash and the in-tray every 4 seconds.

Start it with `cd frontend && npm run dev`, which opens the desk in your browser.
