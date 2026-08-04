# Applied AI — Systems, Practice, and Ethos

*Theodore Simmons — working reference for AI-native / Anthropic / OpenAI applications, interviews, and self-description. Last updated 2026-08-03.*

This is not a resume. It's a description of the practice: how the work gets built, how Claude Code itself gets managed as an operating layer, and the systems and projects that came out of it.

---

## 1. Ethos

- **Force multiplier, not solo builder.** Everything is built to be handed off and run without him in the room. The question is never "does this work," it's "does this scale, does this replicate."
- **First principles under pressure.** Is this problem worth solving? Did we make our own weather? Ask WHY 3-4 times, then go find the person 6-7 levels deep in the org who actually knows.
- **Blank spaces as first-class output.** The design principle behind temet (below): what a system *doesn't know* is more important than what it does know, surfaced as a structured answer, not an error. Generalizes to a broader distrust of confident-sounding coverage — build systems that say "here's what I can't prove" out loud.
- **Judgment over novelty.** Repeatedly reverted a more "impressive" solution (speaker diarization in Trace, a full MCP-server swap-in for sc-demo) for one that actually fit the real usage distribution. Optimizes for the honest architecture, not the one that sounds better in a design doc.
- **Extreme ownership + playbook thinking.** When something works once, the next question is "how does this become repeatable." Three of the systems below (workshop-factory, the sc-demo pattern library, temet) exist specifically because a one-off success needed to become infrastructure.
- **Comfortable at the edge, not chasing hype.** Builds on the frontier — agentic MCP servers, multi-agent orchestration, RAG blank-space detection — because the work requires it, not because "AI" is the pitch. The model is instrumental to a real operational problem in every case below.
- **Token/cost discipline as an engineering value.** Built shared infrastructure specifically to route generation through the right-sized model instead of paying for it the expensive way by default.

---

## 2. How projects — and Claude Code itself — get built and managed

This is the part that doesn't show up in a list of shipped projects. Claude Code isn't a chat window here — it's the operating system for a one-person engineering practice running roughly ten concurrent initiatives at once (enterprise demos, workshop programs, internal tooling, personal apps), and real infrastructure has been built around the tool itself to make that possible.

**Persistent, typed memory system.** A semantic memory architecture — user, feedback, project, and reference memory types — that compounds across sessions instead of resetting each time a conversation ends. An index file plus individually cross-linked notes, read at the start of relevant work so context never has to be rebuilt from scratch. Memories carry provenance and staleness signals (age, explicit "verify before trusting" flags) — the same blank-space-honesty principle behind temet, applied to his own working memory rather than a customer's CMDB.

**Explicit model-tiering discipline.** Haiku for read-only research and exploration, Sonnet for reasoning and code, Opus reserved for tasks that genuinely demand it — applied consistently across dozens of subagents and skills. This is real cost/latency resource management in daily practice, not "always reach for the biggest model because it's available."

**Multi-agent workflows for high-stakes review.** For review- or audit-shaped work — code review, plan review, compliance checks — uses structured fan-out: parallel finders searching from different angles, adversarial verification panels that have to actively refute a finding before it survives, judge panels for comparing design alternatives. Deliberately opted into for work where being wrong is expensive, not applied by default to everything.

**Project isolation by design.** Maintains separate per-project session-context files rather than one shared scratch file — a direct structural fix after cross-project state bleed cost real time once (two unrelated initiatives silently overwriting each other's working notes). The fix was architectural — one file per project, re-read whenever context is ambiguous — not "just be more careful next time."

**A self-authored skill ecosystem.** Builds and maintains a suite of production Claude Code skills: a customer-demo generation factory used across a global field organization, a package-management toolchain, a workshop-conversion pipeline, lab-authoring tooling. Each documents its own failure modes and gotchas, and each is composed from structural patterns deliberately mined from Anthropic's own reference plugin repositories (financial-services, healthcare, life-sciences verticals) — pulled and reviewed on a recurring schedule rather than copied once and left to drift.

**Checkpoint-before-autonomy discipline.** Commits changes (or explicitly enumerates the files about to change, outside a git repo) before kicking off any unattended or multi-step agentic run, and treats a bad autonomous run as "revert and restart clean," never "patch mid-flight." The same operational caution a real production agent deployment needs, self-imposed on a personal practice long before it was forced by an incident.

**Verification-before-done culture.** Never calls a task complete without actually running the build, test, or lint step; holds work to "would a staff engineer approve this"; runs a separate adversarial evaluator pass on non-trivial changes before considering them finished, rather than trusting the first pass that looks right.

**A working self-improvement loop.** Corrections get written back into a standing lessons record and re-read before related work resumes. Not aspirational — an actual mechanism with a visible history of rule changes, each traceable to the specific incident that caused it.

**Parallel execution as the default for independent work.** Runs unrelated workstreams as separate background agent sessions, each auto-isolated in its own git worktree, instead of serializing everything through a single context window or juggling terminal tabs by hand.

**Cost economics as a first-class constraint.** Built and wired in an internal LLM-routing utility specifically to separate "text a human reads" from "tokens the orchestrating agent burns," and actively manages context-window cost — compacting mid-task, clearing on task switch — rather than letting a session run until performance degrades.

**The pitch:** this isn't just heavy Claude Code usage — it's the infrastructure layer (memory, orchestration, verification, cost control) that most teams eventually have to build once agentic tools stop being "occasionally helpful" and become the primary way work gets done. That's the same problem an AI-native company's own customers hit at scale, seen firsthand from the builder's side of it.

---

## 3. Enterprise agentic systems (built solo, ServiceNow context)

These are field/production-adjacent systems, not lab exercises — each shipped, was demoed to real technical stakeholders (CTOs, regulators, field engineers), or ran against live data. What they show: applied agent-system judgment — architecture, model selection, failure handling, MCP tool design — at enterprise scale.

### temet — a self-aware MCP server
Built an MCP server for ServiceNow that models its own knowledge gaps as a first-class output. Most RAG/agent systems answer confidently or fail silently; temet's core primitive is the **blank space** — a structured, severity-ranked statement of what the system cannot currently prove, surfaced alongside every answer. Built for a real question a customer CTO asked (financial-services sector): "Can we prove our DORA compliance posture to BaFin?" Answer against live data: *"No — 44.6% chain completeness, 56 broken CI-to-business-capability chains, CRITICAL blank space."* That's the differentiated answer: a system that states the honest limits of its own certainty instead of its best guess.

- **Architecture:** a graph traversal cache over ServiceNow's native CMDB/task tables (no new schema for the base case) + a compliance-lens layer (DORA now, SOX next) that reinterprets out-of-the-box data rather than requiring custom fields + a learning store (query patterns, vocabulary, profile history) that improves scope-check speed with repeated use.
- **Judgment calls:** capped query-plan revision at 2 attempts before returning a blank-space block instead of retrying indefinitely; wrapped the entire plan→validate→execute path in structured failure handling so an unhandled exception returns a typed `plan_failed` block at HTTP 200, not a crash; staleness detection diffs the CMDB audit log to invalidate cached state rather than trusting a blind TTL.
- **Competitive framing:** not aware of another MCP server that combines graph traversal + compliance lenses + blank-space-as-answer + a learning store — `UNVERIFIED` beyond the adjacent products checked (Glean, Atlan/Collibra, Databricks Genie), each of which does one piece.
- **Proof points:** live end-to-end smoke test on real instance data, 6 MCP tools shipped, 46+3 automated tests passing, narrative answers generated in ~5 seconds.

### Zeroform — multi-agent ITSM/ITOM prediction system
**Status: prototype, shelved.** Built for a company-wide hackathon, then shelved after the event once the immediate goal (the hackathon submission) was met — preserved here for the architecture and build patterns, not as an ongoing system.

Built a predictive-incident system, not reactive triage: ITOM signals get correlated into predicted incident groups *before* they fire, target Mean-Time-To-Predict under 5 minutes. Full stack: Express/TypeScript API, Next.js/React front end, Postgres + pgvector, two-tier model routing (Sonnet for triage reasoning, Haiku for the high-volume worker loop).

- **Agent design ("Sentinel"):** a 6-step autonomous remediation persona — assign → triage (cross-references CMDB, related outages, knowledge base) → diagnose via work notes → take a live remediation action (endpoint script or O365 API call against the real system, with local fallback on failure) → update and resolve → author a new knowledge article if the fix wasn't already documented.
- **Judgment call:** moved event correlation from a 5-minute poll to an event-driven trigger fired immediately on signal ingest, turning a "check every 5 minutes" MTTP into a sub-second one — a latency problem solved architecturally, not by tuning a timer.

### ZTSD (Zero Touch Support) capability expansion
Extended a shared platform's own out-of-the-box autonomous-agent product across three capability tracks: web search grounding, remediation via workflow-designer subflow tools, and semantic discovery of customer-built agents/workflows through the AI Search RAG layer already wired into the product's Research Agent. Self-imposed design constraint: **no custom script tools, no embedded JavaScript in agent tool definitions** — every capability added by configuring the platform's own agent/tool/search primitives, the harder and more durable path versus bolting on custom code. Also diagnosed and worked around a semantic-indexing pipeline bug (a stuck ingestion queue silently blocking RAG confidence scoring below the product's own threshold) that would otherwise have quietly degraded every grounded answer.

### Demo Factory + MCP server evaluation
Built and maintains an agentic "demo factory" skill used across a global field organization: customer brief → decision-tree routing → data-loader trigger → live-data adaptation (renaming CIs, personas, branding to a specific customer's world). Composed structural patterns pulled directly from Anthropic's own vertical-plugin reference repos (a life-sciences decision-tree skill, a healthcare waypoint architecture, a financial-services MCP-connector pattern) into a reusable pattern library rather than reinventing the composition layer from scratch.

Separately evaluated a community-built platform MCP server (~130+ tools spanning core CRUD, CPQ, and SDK operations) against the one in production use — found and documented a live bug in its highest-value feature (a setup tool posting to database tables that don't exist on any live instance) before recommending against blind adoption, then staged a deliberate alongside-install rather than a swap that would have destabilized the production skill.

### Build-vs-Buy ROI experiment
Ran a 200-call empirical experiment comparing two agentic support designs — a lighter one at 3.0 average LLM calls per interaction, a heavier one at 9.1 — to produce a real build-vs-buy cost model instead of a synthetic estimate: 96.5% AI-resolved (autonomous + deflected), 0 errors, projected to real deployment scale (~89,000 calls/month) at roughly $1,361/month in inference cost against $803K/month in labor savings — a 590x annualized ROI, with the full cost/latency/resolution-rate methodology documented and reproducible.

### Shared model-routing infrastructure
Built and now maintains a shared CLI that routes all generative text (demo copy, incident narratives, lab content, talk tracks) through an internal LLM proxy instead of every project regenerating it ad hoc or paying for it as agent output tokens — a deliberate piece of cost/architecture discipline: separate "the text a user reads" from "the tokens the orchestrating agent spends," and centralize model/endpoint choice in one place instead of six.

### Workshop-conversion pipeline
Designed and shipped a 4-stage pipeline (build → go/no-go → workshop conversion → adversarial hardening) after a real incident: a customer lab workshop's customizations were scattered across roughly a dozen auto-created default configuration containers, discovered only after a multi-day reverse-engineering effort. The fix was structural, not a one-time cleanup — front-loaded configuration-management discipline into the build step itself, made adversarial review a required gate (a bug existed across 3 separate business rules before independent review caught all of them), and built idempotent re-seeding since the target environment provisions fresh every time rather than persisting state.

---

## 4. Personal AI projects

Four apps, deliberately different shapes. The throughline: building tools he actually uses, with the judgment calls about *where* to put an LLM — and where not to — as the thing he cares most about defending in an interview.

### Captions — Real-time JA→EN speech translation overlay (macOS)
Swift · Python · OpenAI Whisper. A personal tool used on live video calls with Japanese colleagues. Chose Whisper's `translations` endpoint over a chained ASR→MT pipeline — one model call for detect + translate, lower latency, a single failure surface instead of two. An RMS-based voice-activity detector hits the API at natural sentence boundaries rather than fixed time windows. A bounded, drop-oldest queue (`maxsize=2`) absorbs backpressure when a request stalls, so the overlay stays current instead of lagging further behind. Model failures and audio-hardware failures are surfaced to the UI as distinguishable states, not collapsed into one generic error. ~550 LOC, ~2s end-to-end latency, dogfooded weekly.

**Why it matters here:** not a research artifact — a working tool with a real user. The judgment calls (right API surface for the job, a queue that fails gracefully when the model is the slow part, distinguishable failure modes) are the same calls that scale to customer deployments.

### Trace — Personal AI meeting recall + brief generation (macOS)
Swift · Python · Claude Opus · whisper.cpp · sqlite-vec. An on-device tool that surfaces relevant moments from past calls with the same customer *while the current call is happening* — a working-memory prosthetic, not a post-hoc summarizer like the commercial alternatives. That single product requirement reshapes the whole architecture: transcription has to be local and fast, embeddings cheap, the corpus queryable in under 100ms while another thread is still recording.

Mixed-model pipeline with explicit per-stage reasoning: local `whisper.cpp large-v3` for transcription (privacy plus latency — no reason to send every customer call to a third party), local MiniLM embeddings for recall (sentence-level similarity search doesn't need a frontier embedding model), and Claude Opus reserved for the one genuine quality problem — turning a 60-minute transcript into a structured, voice-matched brief. Reverted a more sophisticated per-speaker diarization model to a simpler audio-source heuristic after the actual usage data showed the fancier model was earning its cost only about a quarter of the time — the more impressive solution was the worse outcome. Reliability details: only counterparty utterances get embedded (self-talk doesn't need to be recallable, which roughly halves index churn); atomic single-transaction database inserts so the recall index can't desync from the transcript log on a mid-meeting crash; the transcript is saved before brief generation so a failed model call never loses the meeting. ~3,900 LOC, in active use.

**Why it matters here:** the project with real model-selection decisions and real latency consequences to defend — frontier model where quality matters, small local model where latency matters, a non-AI heuristic where the AI option wasn't pulling its weight.

### Mirage — Chrome extension for capturing enterprise-software flows as interactive HTML demos
JavaScript · Chrome Extensions (MV3) · Shadow DOM traversal. No AI — included because the bug surface is exactly what an applied AI engineer ends up debugging in real customer deployments: a platform that doesn't behave like the documentation says it should. Handles a target platform's web components at 10-12 levels of shadow-DOM nesting, where off-the-shelf demo-recording tools fail outright. Records live clicks, captures screenshots plus accessibility metadata, and exports a single standalone HTML file that replays as an interactive demo with invisible input overlays. ~1,070 LOC, in active use for customer demos.

### Teleprompter — macOS floating teleprompter for video calls and recordings
Swift · WKWebView · a hand-built JS↔Swift bridge. The smallest and most honest of the four — a personal tool used every week, built because commercial alternatives cost a monthly fee, watermark output, or show up in screen recordings; this one does none of that. Not Applied AI. What it demonstrates: comfort below the framework line — no Electron, `swift build` produces the app directly, and every rough edge (drag regions that silently no-op in WKWebView, text-selection CSS breaking the Return key, a keyboard shortcut hijacking the wrong element) got fixed because it was felt firsthand, not filed as a ticket.

---

## 5. Applied AI credential path

- **Target:** Claude Certified Architect (CCA) Foundations — 60 questions, 120 minutes, proctored.
- **Progress:** foundational coursework complete (10/10). Daily Claude Code practitioner — already strong on configuration and agentic workflows in practice; the remaining formal gaps are agentic architecture/orchestration terminology and MCP-as-builder framing, both of which the enterprise systems in Section 3 are direct, non-coursework evidence against.
- **Framing:** not "learning AI" — closing the last formal-certification gap on a stack already used daily to ship production agentic systems.

---

## Changelog

### 2026-08-03

- Added: none (governance-only pass).
- Updated: temet entry — genericized the named customer to "a customer CTO (financial-services sector)"; softened the competitive claim to an explicit `UNVERIFIED` hedge instead of an absolute "no MCP server" statement. Zeroform entry — added an explicit `Status: prototype, shelved` line so the entry doesn't read as an ongoing system.
- Corrected: none.
- Evidence added: none.
- Claims still requiring verification: temet's "not aware of another MCP server that combines..." claim remains `UNVERIFIED` — flagged, not resolved; would need an actual competitive scan to upgrade to a verified claim.

---

*Working copy also maintained in Claude Code's memory system for reuse across sessions. Update both when either changes.*
