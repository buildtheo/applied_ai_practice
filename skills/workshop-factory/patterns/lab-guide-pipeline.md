# Pattern: Lab Guide → GitBook Pipeline

Sources: `~/.claude/skills/ice-package/SKILL.md`'s `lab-guide` subcommand (the mechanized PDF→markdown→screenshot→validation tool — v2.0.0) plus the `lab-guides-workflow` and `ztsd-lab-guide-repo` memories (the actual GitBook-published repos and their hard-won gotchas).

**Use `/ice-package lab-guide` for the conversion/capture/validation work — don't hand-roll a PDF-to-markdown pass.** This file is what to know on top of that tool: the two-repo handoff it doesn't itself manage, and the GitBook-specific gotchas that live one step downstream of it.

## The two-repo reality — don't conflate them

- **`/ice-package lab-guide` writes into `sn-dt-corp/redteam-zeroform`** (`lab-guides/<lab_id>.md`, images at `lab-guides/assets/<lab_id>/`). This repo is the **source/version-history backup** — per its own SKILL.md, GitBook Git Sync is not configured on it directly.
- **The actual published GitBook site is synced from a different repo** — `buildtheo/lab-guide` (LAB8114-K26 lineage) or `buildtheo/ztsd` (successor), each requiring **`SUMMARY.md` at the repo root + one `.md` per page** and images at **`.gitbook/assets/{LAB-CODE}/`** — a different path convention than `redteam-zeroform`'s `lab-guides/assets/`.
- **Porting content from the source repo to the published repo is a real reformatting step**, not a copy: restructure into `SUMMARY.md`-referenced pages, and move/re-reference every image from `lab-guides/assets/<lab_id>/` to `.gitbook/assets/<lab_id>/`. Don't assume the ice-package tool's output is publish-ready as-is.

## `/ice-package lab-guide` — what it actually does

- **Phase 1 (PDF conversion, always runs for new guides)**: PDF → markdown with a fixed convention — `**bold**` for UI element names (buttons, fields, tabs), `` `inline code` `` for field values/record numbers/sys_ids/paths, fenced blocks for scripts, tables for personas/agendas/state mappings, `>` blockquotes for callouts, numbered lists for sequential steps. Page numbers and running headers are omitted on conversion, not left in for later cleanup.
- **Phase 2 (screenshot capture, needs `--instance`)**: via `/browse`, one screenshot per key moment (starting state, first nav step of each exercise, config panels, checkpoints, final state), named `<exercise>-<step>-<short-description>.png`.
- **Phase 3 (step validation, needs `--instance`)**: compares markdown steps against the live instance — nav paths, field/button/tab labels, default values, step count — and **annotates every corrected step** with `> **Updated {YYYY-MM-DD}:** {what changed and why}` so a future maintainer can see what drifted and when. This annotation convention is worth carrying into the published GitBook repo too, not just the source repo.
- **Phase 4 (`--add-section`)**: append a new exercise/module to an existing guide without needing a new source PDF — draft with the user, validate live if an instance is available, insert at the right position.

## GitBook-specific gotchas (apply once content reaches the published repo)

- **`SUMMARY.md` is load-bearing** — without it at the repo root, Git Sync treats the whole repo as a single page.
- **Images MUST resolve under `.gitbook/assets/`** in the published repo — any other path renders "Could not load image" even though the file exists.
- **Case-insensitive macOS filesystem collision**: `README.md`/`readme.md` can be two distinct, intentional GitBook pages that collide to one inode on a macOS checkout — only one's content is ever actually on disk. **Never `git add -A` / `git add .`** in a local clone of a repo with this pattern; stage by explicit path.
- **A GitHub PAT scoped to an org does not imply access to a personal-account repo**, even with matching permissions — an org-SSO token can resolve to a different identity and 403 on a personal repo. If push fails despite a seemingly-correct token, check which identity it actually resolves to before regenerating.
- **Real screenshot-capture blockers exist, not just effort**: shadow-DOM modals with no direct URL, popups that open in a genuinely new browser window (unreachable by headless `/browse` without an explicit `handoff`), and release-gated UI sections visible on one release but not another.
- **Multiple independent review/tester-feedback rounds catch different bugs.** The ZTSD guide needed a terminology pass, a full structural rewrite matching a changed live UI, a numbering-cascade fix (renumbering one heading requires checking every subsequent heading in the file, not just the immediate collision), and a cross-check against a second tester's independent notes — each round found something the previous one missed. Budget for more than one pass.
