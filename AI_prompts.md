# AI Prompts Log — HW5: Campus Customs Multi-Agent Operations

A log of every prompt typed into Claude Code while working on this assignment, organized by problem.

---

## Setup (before Problem 1)

**Prompt 1:**
> We are doing Homework 5: Campus Customs Multi-Agent Operations for my AI class. Please make a folder called hw5 and put the rest of the work we do together there.

**Prompt 2:**
> Please read the attached screenshots to understand the background scenario and data setup for this assignment. I will download the data and upload it as a zip file.

**Prompt 3:**
> Also, while we work, this is the expected file layout for the finished product

**Prompt 4:**
> This is the data provided. Please unzip

---

## Problem 1: Vibe coder prompts

**Prompt 1:**
> Okay, let's start with Problem 1: Vibe coder prompts. Create AI_prompts.md and keep it updated as we work through this assignment. This will be the file log of all that I typed into Claude Code. Make one section for each problem. Each section must include the problem number and title and at least the initial prompt that I typed, providing guidance on the problem. I will let you know when we are moving on to the next problem so you can create the appropriate section title.

---

## Problem 2: Study the campus customs database

**Prompt 1:**
> Perfect. Let's move on to Problem 2: Study the campus customs database.
> Open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db (later problems will update that working copy). Study the three open tickets so you see how they link to other tables.

**Prompt 2:**
> Start output/harness.md. For each table, list the fields and one short line on why that table matters for the agents. We will keep growing this harness file in later problems.

---

## Problem 3: Build the MCP server

**Prompt 1:**
> Fantastic. Let's move on to Problem 3: Build the MCP server. Write an MCP server in MCP_server/using Fast MCP. It will talk to data/campus_customs_new.db. You do not need to connect or run it in this problem. Every agent in this homework uses the tools in this MCP server. You will add more tools to it later. For now, write three tools you know you will need for the tickets in the database. Keep the names clear. Never invent any data. Only use information in the database.

**Prompt 2 (edited version of Prompt 1, sent after interrupting):**
> Sorry I sent that last prompt too quickly. Edited version: Fantastic. Let's move on to Problem 3: Build the MCP server.
> Write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. You do not need to connect or run it in this problem. Every agent in this homework uses the tools in this MCP server. You will add more tools to it later. For now, write three tools you know you will need for the tickets in the database. Keep the names clear. Never invent any data. Only use information in the database.
>
> In output/harness.md, list each of your three MCP tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why that tool is the right one for that ticket. Don't be vague. Lines like "reads inventory" will score low when this assignment is graded. Tie the tool to the ticket.  Also, add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt 1:**
> Okay, great, let's move on to Problem 4: Add the MCP server to vibe coder and test each tool. In your vibe coder (Claude Code in this case), add your MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root, or however your vibe coder saves local MCP server lists. With your vibe coder connected, test each of your three MCP tools. Save the evidence in output/MCP_smoke.json. For every tool, include:
>
> * the prompt you asked the vibe coder
> * the tool name
> * the tool output (must match values in data/campus_customs_new.db)

**Prompt 2:**
> Can you move folder hw5 out of folder hw4?

**Prompt 3:**
> Can you go ahead and do that for me

**Prompt 4:**
> Now that we have moved the folder, continue Problem 4.

**Prompt 5:**
> Are we all caught up with the instructions I have provided now that we have changed folders?

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt 1:**
> Okay great, let's move on to Problem 5: Build the agent team and grow the MCP tools.  Build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. Put the agent prompts in backend/prompts/ (one file per agent). Put data types in backend/models.py, and the agent files under backend/ (your layout can vary as long as the five roles are clear). Use your PORTKEY_API_KEY and only gpt-6-luna for every agent. Write each prompt in your own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt.
> Add any tools the agents need to your MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db. Do not invent a second shop tools layer that bypasses MCP.
> Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step record enough to audit later. Append to this file, do not wipe it each run.
> In output/harness.md list each agent and each MCP tool, including ones you add in this problem, along with which table the tool uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.
> Update mcp_server/README.md so the tool list matches what you have now.

---

## Problem 6: Plan the three tickets

**Prompt 1:**
> Amazing. Let's move on to Problem 6: Plan the three tickets. Before you wire the backend write down what you expect the team to do on each open ticket.
> Build output/desk_tickets.html, a page you can double-click with one tab per ticket (101, 102, and 103). Also add empty Cash and Reflection tabs for later problems. You can leave them blank for now. On each ticket tab, fill an Expected section only. Leave room for an actual section you will fill after you run the agents.
> For each ticket's Expected section, write in your own words:
>
> * Who the boss should call first, and why
> * All the agent delegations you expect, (not "Boss calls everyone")
> * Which MCP tools you expect that run to use
>
> Graders for this assignment will grade plans that send every specialist on every ticket low - it should be more strategic and decisive than that. You will compare this plan to what actually happens when your agents resolve the three tickets.

---

## Problem 7: Backend routes

**Prompt 1:**
> Move on to Problem 7: Backend routes. Your React frontend dashboard (the next problem) needs a backend it can call. In backend/main.py, use FastAPI and add routes that do the following:
>
> * Return the three tickets and whether each is open or resolved
> * Take a ticket ID and run your agent team on that ticket
> * Return recent agent events - what each agent said and which tools they used - so the board can refresh
> * Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
> * Return the current checking balance from cash_accounts
> * Reset the database to the original values when you want to try a fresh run
>
> From the backend/ folder start the server with: uvicorn main:app --reload --port 8000
> This turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes. In output/harness.md, list each route in one line (what UR/what it does).

---

## Problem 8: Agent dashboard

**Prompt 1:**
> Great let's move on to Problem 8: Agent dashboard. Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes you built in Problem 7. At minimum the board should:
>
> * List all three tickets
> * Let you pick one ticket and start the agent team on it
> * Show each agent and what they are saying/doing while the ticket runs
> * Mark a ticket resolved when the run finishes
> * Show a short summary of what each agent did on that ticket
> * Let a human approve a pay or purchase when asked
> * Show the checking balance (it should drop after an approved pay)
>
> Make the dashboard look good. Be creative with the layout and feel - this is a real desk people would want to sit at so put thought into how it looks.
> Tell the frontend to talk to your backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with:
> npm run dev.
> This opens the React desk in your browser so you can pick tickets and watch agents. Write output/design.md with what you chose for the dashboard look: layout, how agents, read, differently, how resolved tickets and cash show up, and why — including the creative choices that make it feel special and something humans would actually enjoy using.

---

## Problem 9: Resolve the tickets

**Prompt 1:**
> Okay let's move on to Problem 9: Resolve the tickets. Before testing the agents on a flow run over the three tickets, reset the working database data/campus_customs_new.db again so you can start clean. Note the starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved.
> Open output/desk_tickets.html from Problem 6. On each ticket tab fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep your Expected section so you can compare the two.
> On the Cash tab of the same output/desk_tickets.html, itemize the money:
>
> * Starting checking balance (after the reset)
> * For each ticket: how cash changed when that ticket resolved, and why (which pay/purchase, dollar amount)
> * Ending checking balance - it must match cash_accounts in the working database.
>
> Wrong cash math will lose points from the grader even if the board shows every ticket resolved. Also save:
>
> * output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals.
> * output/resolved_board.html - a page you can double-click, with a screenshot of your React board for each resolved ticket (101, 102, and 103)
>
> Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

---

## Problem 10: Reflection

**Prompt 1:**
> Okay let's move on to Problem 10: Reflection. Open output/desk_tickets.html and fill the Reflection tab. Answer the following and be detailed and thorough:
>
> * How would you evaluate the performance of the agents on each ticket and why?
> * For each ticket how did actual compare to the expected plan you wrote earlier?
> * What would have been simpler as one agent with tools, and why?
> * Describe three new problems Campus Customs might face that this agent team could solve with the tools you built.
> * Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them.
>
> Make sure to tie every answer to this app and the three tickets you ran. Use the ticket tabs and Cash tab on the same page as your evidence. Generic AI essays without Campus Customs details will score low by the graders of this assignment.

**Prompt 2:**
> Can you confirm that the file path follow the layout I entered earlier?

**Prompt 3:**
> README should explain:
>
> * Copy original DB to the working copy when you need a clean run
> * Start MCP server
> * Start fast API backend
> * Start the React board
> * Reset the DB before a full 3-ticket run

---

## Problem 11: Submit to GitHub

**Prompt 1:**
> Okay let's move on to Problem 11: Submit to GitHub.
> Push your code to a public GitHub repository so the graders of this assignment can clone it. Put the repo URL in output/github_url.txt.
> Do not push your real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so the graders can run your app easily.
