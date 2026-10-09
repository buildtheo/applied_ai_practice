# Leave-Behind Asks — JARVIS & Forge

Context for whoever reads this cold: `workshop-factory` converts SC demos into CloudLabs workshops. The recurring cost is reverse-engineering what an AI build tool actually did to an instance (the Myriad Genetics OMS lab burned multiple days on this). The ask: have the build tools leave behind an artifact of what they actually changed, so workshop-factory never has to reconstruct it from scratch. Verified directly against both codebases before sending — this is not a cold ask.

---

## To JARVIS (Zach Zoretich & Chris Conte)

### Firm asks

1. **Publish an explicit, versioned JSON schema for `what_was_built` items.** Today no item schema exists anywhere in the orchestrator — the only shape is unstructured prose in the mandatory end-of-turn output block (`- [item 1 with table and sys_id where available]`). Extending a field onto an undefined schema isn't possible; the schema has to be defined first.
2. **Persist `SESSION_LOG_ENTRY` fields to disk incrementally, not only in working memory.** The richer structured shape already exists (`timestamp, phase, action_type, description, table, sys_id, key_fields, agent_used, ...` — includes `record_deleted`) but per the Session Capture Protocol, it's explicitly allowed to stay in memory and only optionally flush to `session-log.md` (markdown, not JSON) at finalization. This contradicts the stated reason `session-state.json` exists at all ("LLM session memory dies when the Claude Code window closes") — the same fix was never applied to the fine-grained log.
3. **Extend build-manifest coverage to Fluent-track and hybrid builds.** Today `what_was_built` and the session log are scoped to MCP-track tool calls only. On the Fluent track, `now-sdk build`/`install` writes real structure to the instance and none of it generates a log entry — only `fluent_app_path` (a source directory pointer) gets recorded. A hybrid build's custom-app half is currently invisible to this mechanism entirely.
4. **Add a `schema_version` field to `session-state.json`, with a compatibility commitment.** Neither file has one today. Tooling built against either format needs to know when it's safe to assume the shape hasn't changed underneath it.

### Open questions (answer before we build against this, don't assume)

- Is session-log capture backed by a deterministic hook (like `scan-builds.sh`'s UserPromptSubmit hook), or purely LLM instruction-following ("log every action")? If the latter — what's the known miss rate? JARVIS already hit this exact failure class once (Design Decision 4: moved in-progress-build detection to a shell hook specifically because instruction-following was unreliable for silent multi-step operations) — has the same fix been considered for the build log itself?
- Does the schema model deletes end-to-end (confirmed present in the in-memory design, `action_type: record_deleted`) all the way through to whatever gets persisted, or only in the working-memory representation?
- Does any finalization step sweep **every** `sys_update_set` named "Default" (`state=in progress`) created during the build's time window and reconcile against the intended update set? This is the direct fix for the actual Myriad failure mode — a 17-record Workspace and a full GenAI config chain were stranded in Default despite the single-update-set discipline being followed, because certain record types (Workspace/UI Builder, GenAI config, ACLs) route to Default regardless of which set is current. See `~/.claude/skills/workshop-factory/patterns/preflight-hardening.md`'s "known-affected-table sweep" for the specific tables and the recovery technique already proven to work. **This reconciliation step is worth more than everything else in this ask combined** — a manifest without it will be confidently wrong about exactly the record types that already cost multiple days once.

---

## To the public `servicenow-mcp` maintainers (github.com/ServiceNow/servicenow-mcp — "ServiceNow Forge")

Check current maintainers/CODEOWNERS before addressing by name — this is an open-source repo, file as a GitHub issue, not an internal message.

### Firm ask

Add a **post-call** audit emission alongside the existing pre-call one. Today (`src/guardrails.ts`, called from `src/index.ts`) the always-on audit log (`snow-mcp-audit-<instance-slug>.jsonl`, already redacted via `sanitizeArgsForLog`) fires once, at the pre-call guardrail check — it logs intent (tool + args), never outcome. Ask: emit a second record after a successful write, reusing the same JSONL file and redaction logic:
```json
{"table": "...", "sysId": "...", "updateSetId": "<queried live at write time, not assumed from session state>", "scopeId": "...", "action": "created|updated|deleted", "correlationId": "..."}
```
This is a small, concrete lift — the audit infrastructure, redaction, and `snow_manage_update_set` groundwork already exist.

---

## To whoever owns `dev/forge` / Foundry (internal GHE) — HOLD until field usage is confirmed

Do not send firm asks yet — it's unconfirmed whether SCs building demos actually route through this system (ServiceNow Studio's browser chat panel) versus the public `servicenow-mcp` package above. Get that confirmed first (ask a handful of SCs directly which one they actually use — answers so far have been "not sure / depends on the SC"). Once confirmed, these are the open questions to lead with, not firm asks — Forge's write-tracking capability here is genuinely unknown, not just undocumented:

- Does the Build Agent Runner's write path track or associate with update sets at all today? The documented "Working Set" feature (`INTEGRATION.md`) only tracks reads/edits pulled into the virtual filesystem — nothing in it describes tracking writes back to the instance or which update set absorbed them. "Add `updateSetId`" may be asking for a capability that has to be built from scratch, not a field addition.
- Is there a documented conversation/session-end event beyond the per-turn `turn_end`? A leave-behind needs something to hook at completion, not just per-turn.
- Is `conversation_id` persistence across a client restart a server-side capability, or — per current docs — entirely optional client-side storage ("client may persist across sessions in local storage/DB (optional, not automatic)")? This doesn't match JARVIS's file-based resumability story; parity is a bigger ask than it sounds.
- What redaction, if any, applies to data pulled into the Working Set's virtual filesystem? Any write-tracking event added on top of this needs a firm redaction requirement (table + sysId + scope only, no field values) stated explicitly — this would be drawing from live customer/demo data.

---

## The one thing that matters regardless of which team answers

A leave-behind, from either tool, is a hint that shortens the pre-flight instance sweep. It is never a replacement for running that sweep. This is now hard-coded into `workshop-factory/patterns/preflight-hardening.md` — if either team ships something and it starts getting trusted as authoritative, that's the exact moment the actual safety net (querying the live instance for stray Default update sets) stops happening, which is what caused the original multi-day cost in the first place.
