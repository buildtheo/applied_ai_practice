# Workshop Factory

Stage 2/3 of the workshop-factory pipeline: turning an SC art-of-the-possible demo that has already passed the Stage 1 go/no-go checkpoint into a CloudLabs-launchable, multi-student hands-on workshop. Sibling to `sc-demo` (Stage 0 — builds the golden-instance demo) and `ice-package` (mechanical ICE operations). This skill does not build demos and does not reimplement ICE mechanics — it owns the workflow in between: persona conversion, lab guide authoring, idempotent seeding, packaging orchestration, and a mandatory hardening gate.

Motivated by a real, expensive case study: the Myriad Genetics OMS lab (`~/Desktop/myriad-lab/`), where workshop-specific problems — the same bug hiding in 3 separate business rules, screenshots that drifted from a UI that changed underneath the guide, record references that broke because CloudLabs provisions a fresh instance every time — were each found the hard way, in separate ad-hoc review rounds, because no shared process caught them earlier. This skill exists so the next workshop starts with that discipline built in instead of re-deriving it.

## Preconditions

Do not start here. Confirm first:
1. **Stage 0 is done** — a golden-instance demo exists, built through a tracked update-set-lifecycle session (see `sc-demo/patterns/update-set-lifecycle.md`), not scattered raw MCP calls.
2. **Stage 1 go/no-go passed** — this demo genuinely needs a teaching narrative (exercises, checkpoints, personas), not just an impressive click-through. Most demos should stay demos.

## The workflow

1. **Persona design** (`patterns/persona-design.md`) — decide who the students are and what each one can actually do on a live instance, before writing a word of the guide.
2. **Lab guide authoring** (`patterns/lab-guide-pipeline.md`) — call `/ice-package lab-guide` for the actual PDF→markdown→screenshot→validation work; this pattern file covers the two-repo handoff (source repo → GitBook-published repo) and GitBook-specific gotchas that tool doesn't itself manage.
3. **Idempotent seeding** (`patterns/idempotent-seeding.md`) — write the build/seed scripts so a fresh CloudLabs provision reproduces the exact same teachable state every single time, not just the one time you tested it.
4. **ICE packaging** (`patterns/ice-packaging-gotchas.md`) — call `/ice-package update`/`create`/`analyze` for the mechanical work. **Read `~/.claude/skills/ice-package/SKILL.md` directly before packaging any workshop** — its version-selection gotchas (silent downgrades, renamed-app duplicate records, persistent scraper bugs) carry the highest blast radius of anything in this pipeline, since a bad package reaches every student instance, not just one.
5. **Pre-flight hardening** (`patterns/preflight-hardening.md`) — mandatory gate before trusting any fresh CloudLabs provision. Not optional, regardless of how confident the build feels.
6. **Guide-drift audit** (`patterns/guide-drift-audit.md`) — for an *already-published* guide that's drifted from a live instance's UI (as opposed to step 2's new-guide authoring). Starts from a scoped findings doc, re-verifies nav *and mechanism* claims live before rewriting, and recaptures screenshots in the same pass.

## What this does NOT do

- Does not design the demo narrative itself — that's `sc-demo`.
- Does not reimplement ICE extraction/creation/comparison — that's `ice-package`.
- Does not replace the standing global rules (update-set discipline, "don't break unless certain," verify-before-claiming-done) — it applies them at the workshop-packaging layer, cross-referencing rather than restating them.
