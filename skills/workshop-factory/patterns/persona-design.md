# Pattern: Persona Design for Independently-Exploring Students

Source: `ztsd-lab-guide-repo` memory (buildtheo/ztsd, the ZTSD/LAB8114-K26 lab guide, 2026-07-13/14 fixes).

## Why

A workshop demo has one narrator walking a script. A workshop has N students clicking around independently on their own provisioned instance, each hitting whatever the persona's actual permissions allow — not what the guide assumes they allow. Two real bugs from the ZTSD lab guide came directly from skipping this check: a persona was written to author a KB article as an admin-equivalent role when the live persona (Ravi Kapoor) actually has `knowledge`, not `knowledge_admin` — the guide had to be fixed to either stay in-role or explicitly fall back to admin. And a caller-lookup script's first-choice branch (matching "Fred Luddy" by name) *never* fires on this instance type — every run falls through to a named-persona fallback list — which meant the guide, if left unfixed, would describe a UI moment that would never actually happen for any student.

## The rules

1. **Verify the persona's actual role on the live instance before writing exercise steps around it** — don't assume a persona has the permission the exercise needs. Check the real role (`sys_user_has_role` or equivalent), not the persona's title/flavor text.
2. **When a script's lookup has a fallback chain, identify which branch actually fires in practice** — trace it live, don't leave a guide describing a first-choice branch that structurally can never win. If a "primary" path never fires, document the fallback as the real path, not an edge case.
3. **Assume every incident/record number varies per student** — CloudLabs provisions a fresh instance per student, so a fixed record number (`INC0010314`) baked into a guide either drifts (if seed scripts create records dynamically) or is simply wrong on someone else's instance. Reference records by short description or by a dynamically-looked-up value, and add an explicit "your instance may vary" note wherever a guide shows a screenshot with a specific number in it.
4. **Design personas for independent exploration, not a single guided walkthrough** — a workshop persona needs to survive a student who clicks the wrong thing first, not just follow the happy path the guide describes.
