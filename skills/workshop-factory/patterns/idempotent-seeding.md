# Pattern: Idempotent, Numbered Seed Scripts

Source: `~/Desktop/myriad-lab/scripts/` and `00_README.md` (Myriad Genetics OMS lab build).

## Why

A demo instance is built once and lives indefinitely. A CloudLabs workshop instance is provisioned fresh **per student, every single time**. A seed script that "worked" once — because it happened to run against an instance already in some particular state — is not proven; it's untested against the only condition that actually matters: a truly blank fresh provision. Idempotency is the whole game here, not a nice-to-have.

## The conventions

**Numbered build order.** Base build scripts are numbered in strict run order (`01_users_personas.js`, `02_hcls_organizations.js`, ... `17_hcls_field_scope_fix.js` in the Myriad build) so dependency order is legible from the filename alone — no separate run-order doc to keep in sync.

**Four-digit fixup scripts for post-hoc fixes.** When adversarial review finds a bug in an already-numbered script, don't edit history in place — add a new script in the `1700+` range (`1700_fixup1.js`, `1701_gold_doc_gaps_fix.js`, `1703_fulfillment_br_consumer_fix.js`, etc.) that layers the fix on top. This preserves a clear provenance trail: what was in the original build vs. what got patched in after review, and in what order the patches were applied.

**Separate ranges for seed-data batches.** `1800+`/`1900+` for bulk data-seeding batches (`1800_seed_cases.js`, `1900_seed_data2.js`) — distinct from both the base build and the fixups, since these can be re-run independently to top up data volume without re-running structural fixes.

**One XML export per named fix in `update_sets/`**, not one giant bundle. When a config-layer bug is fixed (business rule, ACL, field scope), export it as its own named XML (`Myriad_ORM_Order_Consumer_Fields.xml`, `Myriad_HCLS_Field_Scope_Fix.xml`) so a bad fix can be isolated, re-pulled, or re-applied independently of everything else that shipped alongside it.

## The actual idempotency bar

Before trusting a seed script for a fresh-provision workshop:
- Does it use `find-or-create` logic, or does it assume the record doesn't exist yet and will duplicate on a second run?
- Does anything it creates get referenced later by a fixed sys_id or number that only existed because of a *previous* run's side effects?
- Has it actually been run against a genuinely fresh provision — not just re-run against the same dev instance it was written on? (The Myriad build's Section 4 pre-flight checklist exists specifically because "worked in dev" and "works on fresh provision" turned out to be different claims more than once.)
