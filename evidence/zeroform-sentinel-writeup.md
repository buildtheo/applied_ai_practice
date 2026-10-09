# ZeroForm + Sentinel — Historical Project Evidence

Added to TheoOS on 2026-10-09 from `zeroform-sentinel-writeup.md`, supplied by Theodore Simmons. This preserves historical project notes, not an independent verification of the code, runtime, metrics, or current instance state.

- **Evidence level:** written project notes; live-test claims and performance claims require their underlying logs or tests before reuse as measured outcomes.
- **Status:** ZeroForm is reported shelved on 2026-06-02. The standalone Sentinel worker state below is dated 2026-03-20 and has not been rechecked.
- **Two artifacts:** the Sentinel persona inside ZeroForm and the separate ServiceNow Sentinel worker must not be treated as one deployment.
- **Simulation boundary:** ZeroForm remediation tools can fall back to fake outputs on errors. A successful demo response alone does not prove live endpoint or O365 remediation. The described ServiceNow operations write incident work notes; actual device or Microsoft 365 changes are not established by these notes.
- **Confidentiality:** credentials removed. Remaining instance identifiers and internal architecture details need confidentiality review before external portfolio use.
- **Claims to verify:** sub-second MTTP, ML retraining, LTM activation, NAP approval behavior, and the historical explanation of ZTSD failures. Configuration flags alone do not prove runtime behavior.
- **Engineering lessons:** event-driven dispatch avoids polling delay; simulated fallback must be disclosed; approval UI and trigger activation are separate dependencies; preserve unresolved naming and architecture conflicts rather than silently reconciling them.

---

## ZeroForm — AutoIT 2026 Hackathon Build

**Repo:** servicenowtheo/hacktest | **Path:** `/Users/theodore.simmons/zeroform/`
**API:** localhost:3001 | **Web:** localhost:3000 | **Sim:** localhost:3002
**Stack:** Express + Next.js 16/React 19 + Prisma/Postgres 16 + pgvector 0.8 + OneLLM proxy
**LLM:** claude-sonnet-4-5 (portal/triage) + claude-haiku-4-5 (worker) via OneLLM

### Architecture Diagram
- HTML: `/tmp/zeroform-arch.html`
- PDF (shareable): `/Users/theodore.simmons/zeroform/zeroform-arch.pdf`
- PNG: `/Users/theodore.simmons/zeroform/zeroform-arch.png`

### MTTP (Mean Time To Predict) — Goal: < 5 min
**How:** ITOM signals → `POST /api/signals/new` → worker correlates → EventGroup(status=predicted)
**Fix applied (session 2):** `apps/api/src/routes/signals.ts` now calls `workerTick()` via `setImmediate` immediately on ITOM signal ingest — no longer waits for 5-min polling interval. MTTP now sub-second for correlation, not up to 5 min.
**Scoring:** Pass < 5min | Partial 5-10min | Fail > 10min (OWNER-tests.md)

### NOC Ops Features (session 2)

**Ack System**
- `PATCH /api/ops/:id/ack` — stamps `acknowledgedAt` + `acknowledgedBy` on EventGroup
- Prisma migration: `20260318035906_add_ack_fields` (fields: `acknowledgedAt DateTime?`, `acknowledgedBy String?`)
- Frontend: Ack button on EventCard + EventDetail; flips to green "✓ Acked" badge on press
- Escalation Timeline: 3-dot strip (Fired → Acked → Resolved) lights up as incident progresses

**Priority Labels (P1/P2/P3)**
- Frontend-only derived field — not stored in DB
- P1 = critical + firing | P2 = high+firing or critical+predicted | P3 = everything else
- `PriorityPill` component renders colored badge in EventCard header

**Admin Panel Additions**
- `NocMetricsRow`: P1/P2/P3 incident counts (15s poll) + MTTA card (30s) + Noise ratio (60s)
- `SignalSparklineCard`: 30-bucket SVG polyline sparkline, trend indicator, polls every 60s
- `OncallRosterCard`: primary/secondary/IC roster with inline edit, PATCH /api/admin/oncall

**New Admin API Endpoints**
- `GET /api/admin/signal-rate` — 30-bucket time series via `date_trunc('minute', createdAt)`
- `GET /api/admin/noise-ratio` — {total, noise, noisePercent} 24h window
- `GET /api/admin/mtta` — avg minutes createdAt→acknowledgedAt for today's acked events
- `GET /api/admin/oncall` + `PATCH /api/admin/oncall` — in-memory roster
- `GET /api/admin/incident-counts` — P1/P2/P3 from EventGroup severity+status

### Key Files
- `apps/api/src/index.ts` — adminRouter imported + mounted at /api/admin
- `apps/api/src/routes/signals.ts` — MTTP fix: immediate workerTick on ITOM ingest
- `apps/api/src/routes/ops.ts` — PATCH /:id/ack endpoint
- `apps/api/src/routes/admin.ts` — all 5 new NOC admin endpoints
- `apps/api/src/agent/worker.ts` — exports `workerTick()` (5-min poll + now also event-driven)
- `apps/api/src/agent/triage.ts` — correlateEvents() groups ITOM signals by service into EventGroups
- `apps/web/src/components/OpsView.tsx` — Ack, Priority, EscalationTimeline
- `apps/web/src/components/AdminPanel.tsx` — imports NocMetricsRow, SignalSparklineCard, OncallRosterCard
- `apps/web/src/components/admin/noc-metrics-row.tsx` — NEW
- `apps/web/src/components/admin/signal-sparkline-card.tsx` — NEW
- `apps/web/src/components/admin/oncall-roster-card.tsx` — NEW

### OWNER-tests.md Scenarios
- Scenario 1: VPN Cert Rotation — signals fire over 90s, expect predicted EventGroup within 120s
- Scenario 2: Kafka Degradation — expect predicted BEFORE lag=25000 threshold (T+6:00)
- MTTP score: 30 pts total
- Test runner: `apps/api/src/testing/events/`

### DB
- 44 TopologyNode records seeded for BFS blast radius
- Kafka → 10 downstream services | kubernetes → 7 services
- EventGroup has `acknowledgedAt` + `acknowledgedBy` fields (migration applied)

### Sentinel (Ravi) Agent — Session 3 Rewrite (inside ZeroForm)

**ravi-agent.ts — Sentinel 6-step persona**
**File:** `apps/api/src/agent/ravi-agent.ts`
- Renamed persona: "Sentinel" (from Ravi)
- 6-step system prompt: assign → triage (CMDB+outages+related+KB) → work note diagnosis → action (endpoint/O365) → portal update + resolve → create KB if not found
- New `RaviEvent` types: `assigned`, `action_taken`, `kb_created` (plus `kbNumber` field)
- Signature: `runRaviDemo(description, callerName, userReplies, incidentSysId?, incidentNumber?)`
  - New params default to `'unknown'`/`'INC0000001'` — backward compatible
- Mock path covers all 6 steps and passes `incident_sys_id` through to tool calls
- Generator handles new action types: `assigned`, `action_taken`, `kb_created`

**ravi-tools.ts — Live SN calls with fallback**
**File:** `apps/api/src/lib/ravi-tools.ts`
- `run_endpoint_script` case: calls `POST /api/now/v1/zf_remediate/endpoint` on Alectri, falls back to local `fakeEndpointOutput()` on error
- `o365_api` case: calls `POST /api/now/v1/zf_remediate/o365` on Alectri, falls back to local `fakeO365Output()` on error
- Both pass `{ incident_sys_id, action_type/operation, target/target_email }` to SN

**DemoDesk.tsx — New event handlers**
**File:** `apps/web/src/components/DemoDesk.tsx`
- Added `TOOL_ICON` entries for `run_endpoint_script` (⚡), `o365_api` (☁️), `create_kb_article` (📖)
- Added `EVENT_STYLE` entries for `assigned` (🎯), `action_taken` (⚡), `kb_created` (📖)
- SSE handlers wired for `assigned` and `kb_created` event types

**desk.ts route — Schema + call updated**
**File:** `apps/api/src/routes/desk.ts`
- `DemoStartSchema` now accepts `incident_sys_id` and `incident_number` (both optional)
- `runRaviDemo` call passes both optional fields through
- Tracks `incidentSysId` from both `incident_created` AND `assigned` events for reply injection

### Alectri SN Scripted REST API (LIVE)
**Instance:** https://demoalectriallwfzu142236.service-now.com
- **Namespace:** `now`, **Service ID:** `zf_remediate`
- **Definition sys_id:** `22460524937b76987601fa903603d683`
- **Version sys_id:** `aae70d64cff33a941366fd624d851c82` (version=1 numeric)
- **Endpoint op sys_id:** `4697c5a0cff33a941366fd624d851cec` → `POST /api/now/v1/zf_remediate/endpoint`
- **O365 op sys_id:** `0a9709a0cff33a941366fd624d851c70` → `POST /api/now/v1/zf_remediate/o365`

**Both ops:**
- Accept: `{ incident_sys_id, action_type/operation, target/target_email }`
- Write work note to SN incident: `inc.work_notes = '[SENTINEL-...] ...'` + `inc.update()`
- Return: `{ success: true, execution_id: string, output: string }`
- Verified live via curl tests — work notes confirmed in SN incident history

**SN Scripted REST API field name gotchas (for future ops):**
- `web_service_definition` (NOT `rest_api`) on `sys_ws_version`
- `version=1` as integer (NOT `api_version='v1'`)
- `operation_script` (NOT `script`) on `sys_ws_operation`
- `response.setBody(object)` — takes JS object, NOT `JSON.stringify(object)` pre-serialized

**ZeroForm status:** Shelved 2026-06-02. Memory preserved for build patterns and SN Scripted REST API learnings.

---

## Sentinel Autonomous Worker — demoalectriallwfzu127215

*(Note: this is a separate, ServiceNow-instance build — distinct from the "Sentinel" persona renamed inside the ZeroForm hackathon above. Same name, different artifact.)*

**Built:** 2026-03-20 | **Instance:** https://demoalectriallwfzu127215.service-now.com
**App scope:** `x_sntnl` (sys_id: `160572a0cff7bed81beab6734d851c01`)
**Scripts:** `~/Projects/kim/` and `~/Desktop/`

### Current State (2026-03-20)
- **Business rule:** INACTIVE (manually disabled — don't want autonomous action yet)
- **Sweep job:** INACTIVE
- **Use case mode:** `copilot` (supervised — requires human approval via NAP)
- **NAP:** `variable` glide_var still empty — needs `sys.scripts.do` fix before approvals show in UI
- **LTM:** enabled (3 of 4 properties set via REST; `episodic_memory` queued via scheduled job)

To re-enable fully autonomous: flip business rule + sweep job to active, set use case to `autopilot`.

### AI Worker Structure

```
sn_aia_worker: Sentinel  [0b6e68382f7bb65c0acb383fafa4e3ef]
└── worker_template: Sentinel Worker Template [216ea8f42f7bb65c0acb383fafa4e3c8]
    └── Sentinel Orchestrator  [7315baa0cff7bed81beab6734d851c19]  (primary agent)
        ├── Sentinel Triage Agent    [1a25fae0cff7bed81beab6734d851cc4]  (shared memory)
        ├── Sentinel Research Agent  [9225fae0cff7bed81beab6734d851ce4]  (shared memory)
        ├── Sentinel Action Agent    [783576e82fff325c0acb383fafa4e375]  (shared memory)
        ├── Sentinel Comms Agent     [4535b224cff7bed81beab6734d851cdb]  (shared memory)
        └── Sentinel Fallback Agent  [ee35f22c2fff325c0acb383fafa4e3c9]  (shared memory)
```

### Tools (7)
| Tool | sys_id |
|---|---|
| get_incident_details | `7045ba24cff7bed81beab6734d851c48` |
| search_knowledge_base | `3f45b264cff7bed81beab6734d851c4f` |
| find_similar_incidents | `b745f264cff7bed81beab6734d851c3a` |
| add_work_note | `ef55f6a82fff325c0acb383fafa4e3f2` |
| resolve_incident | `b355f264cff7bed81beab6734d851c45` |
| escalate_incident | `2a65fa64cff7bed81beab6734d851c60` |
| get_ci_details | `e265766c2fff325c0acb383fafa4e36d` |

### Use Case + Automation
| Component | sys_id | State |
|---|---|---|
| Agentic Workflow (Use Case) | `1e85362c2fff325c0acb383fafa4e303` | copilot mode |
| Business Rule (auto-trigger P1/P2) | `7095feac2fff325c0acb383fafa4e37a` | inactive |
| Sweep Job (15-min) | `4f95fe28cff7bed81beab6734d851c55` | inactive |
| VA Topic | `40a5f6ec2fff325c0acb383fafa4e337` | active |
| NAP setup job | `2905faaccf37bed81beab6734d851c84` | — |

### Scripts (~/Projects/kim/ and ~/Desktop/)
| File | Purpose |
|---|---|
| `fix_nap.js` | Run in sys.scripts.do — enables NAP via NowAssistConfig().enableNowAssistAndNAP() |
| `seed_l1_demo_data.js` | Creates 5 users, 20 incidents (12 open/2 hold/6 resolved), 6 KB articles. Idempotent. |
| `sentinel_demo_run.js` | Creates 3 vivid P1/P2 incidents, re-enables BR, fires Sentinel, re-disables BR. Idempotent. |

### Demo Data (seeded 2026-03-20)
**Users:** sarah.chen, james.okafor, priya.sharma, mike.torres, linda.kim (@alectri.com)
**Groups used:** IT Support Service Desk Level 1 (`912df9e3...`), Network Support (`0df0c400...`)
**KB:** 6 articles in KCS demo KB (`0aa3ffa7...`) — password, VPN/Zscaler, Teams, laptop perf, OneDrive, software access
**Incidents:** 20 total — mix P1/P2/P3, open/on-hold/resolved with real close_notes for RAG

### How Sentinel Learns
1. **RAG (active):** Research Agent searches KB + resolved incidents. More good close_notes = better answers.
2. **Predictive Intelligence (active):** Real ML models retrain on incident corpus automatically.
3. **LTM / Episodic Memory (enabled 2026-03-20):** Remembers context across sessions. Properties set:
   - `sn_aia.enable_ltm = true`
   - `sn_aia.enable_ltm_memory_service = true`
   - `sn_aia.enable_ltm_nlu_service = true`
   - `sn_aia.enable_episodic_memory` — queued via scheduled job (scope-protected, can't set via REST)

### NAP Approval Flow (when enabled)
1. Run `fix_nap.js` in sys.scripts.do — must show `NAP enabled: true`
2. Navigate to `/now/workspace`
3. Open an incident → Now Assist Panel slides in on right
4. Sentinel recommendation appears with Approve / Reject buttons

### Key Technical Discoveries (2026-03-20)
- **Correct tool-agent link table is `sn_aia_agent_tool_m2m`** (NOT `sn_aia_agent_tool` which 400s)
  - Required fields: `name`, `tool`, `agent`, `execution_mode`, `max_auto_executions`
- **AI Worker tables ARE on 127215:** `sn_aia_worker`, `sn_aia_worker_template`, `sn_aia_worker_user_m2m`, `sn_aia_agent_child` all return 200. `sn_aia_worker_blueprint` returns 400.
- **`sn_aia_agent` has no `active` field in Zurich** — agents are always "on"; activation is controlled at use case / business rule level
- **`sn_aia_execution` does not accept GlideRecord inserts** — trigger via business rule (insert fires action_insert BR) or FlowAPI
- **`sn_aia.enable_episodic_memory` is scope-protected** — REST PATCH returns 403. Must set server-side.
- **ZTSD use case is `supervised` not `autopilot`** — that's why ZTSD never worked autonomously. Fixed in Sentinel by setting `execution_mode=autopilot` (then set to copilot on user request).

### Why: Sentinel vs ZTSD
ZTSD problems found during validation:
- `auto_trigger = false` (worker never fired)
- Use case `execution_mode = supervised` (every step needed human approval)
- `lastProcessedCreatedOn = 2019` (would scan 7 years of incidents on first run)
- `u_agent_interaction_count = 0` on all execution records (ran but did nothing)
- NAP `nap_enabled` glide_var empty (approvals invisible even in supervised mode)

Sentinel fixes all of these in its design.

---

## Open Question (flagged, not resolved)

Per Theodore's note: **"Hero was the service portal-like experience next to Sentinel"** — built as part of ZeroForm. This is NOT reflected in the ZeroForm build log above (no Hero-named routes, components, or portal appear in the file list captured at time of memory-write). A separate, conflicting memory (`project_zeroform_architecture.md`) instead frames "Hero" as a positioning-strategy term ("AI veneer on top of existing SN") distinct from "Zeroform" (standalone competitor). That positioning memory may be stale or simply wrong — it was reconstructed after an accidental deletion on 2026-06-02 and could have drifted from the original meaning.

**If picking this back up:** check the actual `~/Projects/kim/` and `/Users/theodore.simmons/zeroform/` directories (if still present) for a Hero-named app/component before trusting either memory account.
