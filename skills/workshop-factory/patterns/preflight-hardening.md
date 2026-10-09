# Pattern: Mandatory Pre-Flight Hardening Gate

Source: `~/Desktop/myriad-lab/PREFLIGHT_2026-07-15.md` and `REVIEW_2026-07-14.md` / `REVIEW_2026-07-15.md` / `REVIEW_2026-07-15_followup.md` (Myriad Genetics OMS lab).

## Why this is a required gate, not an optional nice-to-have

Every round in the Myriad build that skipped an independent review shipped a bug the next round caught. Concretely: a consumer-lookup bug existed in 3 separate business rules across earlier build rounds before one independent review round found all 3 — and a 4th round found a 4th instance that *that* review still missed. A "workspace access fixed" claim from one round turned out, on the next round's re-verification, to have only fixed the shell entry point, not the actual ACL gap blocking the exercise. None of these were exotic failures — they were the ordinary cost of trusting a single pass. Treat adversarial review as required infrastructure for shipping a workshop, the same way a test suite is required infrastructure for shipping code.

## The pre-flight document shape

Adopt this structure verbatim (it's what actually worked, not a theoretical template):

1. **Compiled checklist** — every "not yet confirmed by fresh provision" item pulled from build notes and prior review docs, in one place. Don't let these live scattered across changelog entries.
2. **Status table** — resolve every numbered item from (1): fixed-and-verified, fixed-but-unverified, investigated-not-a-bug, or deferred-out-of-scope. No item left ambiguous.
3. **Explicit GO/NO-GO call** — a direct recommendation, not a summary. If NO-GO, say exactly what blocks it.
4. **Exact post-provision validation checklist** — the precise steps to run the moment a genuinely fresh instance comes online, so the first real signal after provisioning is a checklist result, not a student hitting a broken exercise live.

## The discipline underneath the document

- **Don't break unless certain** (standing global rule, applies directly here): before editing anything off a findings list, classify each item as verified-live vs. merely-inferred. Only touch the verified ones without doing a fresh recheck first.
- **Multiple independent rounds, not one long round.** A single reviewer re-reading their own work misses what they missed the first time, structurally. Route review through an independent pass (a different session, a different angle, a genuinely adversarial "try to break this" framing) — see `evaluator` agent for a subagent that already does this.
- **A "resolved" claim needs re-verification, not trust.** The workspace-access example above is the concrete case: the claim was directionally right and still incomplete. Re-check the actual symptom, not just whether the described fix was applied.
- **Run the full checklist on every fresh provision**, not just the first one — CloudLabs providing a working instance once does not mean the seed scripts are idempotent (see `idempotent-seeding.md`) or that the fix set is complete.

## The known-affected-table sweep — mandatory, not optional (2026-07-16 correction)

**Holding one update set open the entire build does NOT prevent stray content from landing in Default.** This was assumed to be a solved problem (see `sc-demo/patterns/update-set-lifecycle.md`) until an adversarial review of the Myriad case study directly disproved it: certain record types route to an auto-created **Default** update set regardless of which set is current at write time — this is ServiceNow platform routing behavior, not a session-discipline failure, and no amount of "hold the update set open" fixes it. Confirmed from `~/Desktop/myriad-lab/00_README.md`: a 17-record custom Workspace, a full GenAI prompt-config chain, and 6 other real working items were all found stranded in Default, split across **12 separate auto-created "Default" sets** on the same instance from different days — discovered only by manually querying `sys_update_xml`, well after the fact.

**Confirmed-affected table families** — always re-check these specifically, regardless of how careful the build session was:
- Workspace / UI Builder: `sys_ux_app_config`, `sys_ux_screen`, `sys_ux_macroponent`, `sys_ux_page_registry`, `sys_ux_client_script`, `sys_ux_page_property`
- GenAI configuration: `sys_generative_ai_config`, `sys_gen_ai_skill`, `sys_generative_ai_prompt_config`
- Access control: `sys_security_acl`
- UI configuration content that doesn't reliably survive update-set export at all (ship these as idempotent scripts instead — see `idempotent-seeding.md` — not as update-set content): `sys_ui_element`, `sys_ux_form_action`, `sys_ui_related_list`

**The mandatory sweep, as part of every pre-flight pass:**
1. Query `sys_update_set` for every record with `name LIKE 'Default'` and `state=in progress` — list **all** of them, not just the first one found.
2. Cross-reference `sys_update_xml` for the confirmed-affected tables above, scoped to the build's time window, against what the intended/named update set actually captured. Anything present in Default but absent from the named set is a blocking finding, not an FYI.
3. **Recovery technique (proven 3× on Myriad, reuse it, don't reinvent it):** reassign the stray records' `update_set` field to a newly created, clearly-named update set. If the standard `UpdateSetExport` script include doesn't produce a downloadable attachment (it didn't, on Myriad), assemble the XML directly from each record's `payload` field. Run the real Preview action (confirm 0 collisions) → Commit.

**A leave-behind/manifest from a build tool (JARVIS, Forge, or anything else) is a hint that shortens this sweep — never a replacement for running it.** If a tool's self-reported "what I built" list is trusted as authoritative, this is the exact failure mode that recurs: the tool's manifest will be confidently correct about the update set it explicitly managed, and silently wrong about everything that routed to Default underneath it. Run the sweep every time, regardless of how complete any tool's own accounting claims to be.
