# Pattern: ICE Packaging Gotchas for Workshop Content

Source: `~/.claude/skills/ice-package/SKILL.md` itself (the mechanized skill's own gotcha list — v2.0.0) plus the `reference_ice_extraction_patterns` memory. This file does not replace `/ice-package` — call it for the actual analyze/update/compare/create/lab-guide operations. This is the checklist of what can silently go wrong while doing that, specifically as it bears on workshop content, where a bad package or a stale guide reaches every student, not just one demo.

**Read the full `~/.claude/skills/ice-package/SKILL.md` before packaging any workshop** — it is versioned and actively maintained; treat this file as "what to double-check for a workshop specifically," not a substitute for the source.

## Version-selection gotchas (the ones with the highest blast radius)

- **Never run with the default `--platform "Australia"`.** It reads Australia GA versions — lower than any patch — and `update_ice_package.py` will **actively downgrade** apps already at patch-level versions. Confirmed: 5+ apps downgraded in one run (Now Assist in AI Search 16.0.4→15.3.0, Generative AI Controller 12.1.2→12.0.17) when the platform flag was omitted. **Always confirm the target platform with the user before every run** — the release cadence advances (P2→P3→Zurich GA) and yesterday's right answer may be wrong today.
- **Use the highest version that does not exceed the target**, never one from a higher patch. Fallback chain for a P2 target: P2 → P1 → GA. Don't accept `analyze` output blindly — if it reports a version from a higher patch than the target, the scraper fell through to the wrong selection.
- **The update script does not guard against downgrades — this is a known bug, not expected behavior.** After every run, scan `old_ver → new_ver` output for any line where the new version is semantically lower than the old one, and treat that as a bug to manually correct, not an accepted result.
- **Renamed apps can have duplicate `x_sncclab_ice_store_application` records** — a REST query against the old (pre-rename) record only returns pre-rename versions; newer versions live under a new record sharing the same `source_app_id`. Detection: a REST query returns fewer versions than the ICE machine UI shows for that app. Fix requires patching the m2m record with both the new `store_application` and `version` sys_ids — see the manual REST patch pattern in the source SKILL.md.
- **Known persistent scraper bug**: "Now Assist for Order Management" consistently scrapes to 1.0.1 (GA) regardless of platform flag; the correct P2 version is 2.1.0. Verify this app manually after every P2-targeted run — don't trust the automated result for it specifically.
- **Platform plugins (`com.glide.*`, `com.snc.*`) never have patch families — this is correct, not a gap.** They'll show "No '<platform>' family found" and get skipped for any patch target; don't try to force them onto a patch family.
- **ICE catalog gaps are time-specific, not necessarily bugs** — an app can skip because its version records haven't been published to the ICE machine catalog yet. Check the live UI before concluding an app is broken; it may resolve on a later run with zero action needed.

## Structural/extraction gotchas

- **M2M tables are the real install/visibility mechanism, not the cosmetic field.** Setting `ice_package` directly on a content record (e.g. `x_sncclab_ice_script`) makes it queryable via the REST API but **invisible in the ICE UI**. The UI reads the M2M linkage table (`x_sncclab_ice_m2m_scripts_ice_ice_packages`, `x_sncclab_ice_m2m_xml_unloads_ice_packages`, etc.). Always create both the base record and its M2M entry.
- **Content is stored as an attachment, not a field.** Both XML unload content and update set XML live as file attachments on their respective records — fetched via the attachment API, not read from a table field.
- **sys_id extraction from reference fields requires regex, not a `value` key.** These responses return `{"display_value": ..., "link": ".../table/{table}/{sys_id}"}` with no `value` key.
- **Order fields contain commas** (`"1,010"`) — strip before parsing as an integer.
- **Cross-scope content needs one committed update set per scope.**
- **Nested CDATA breaks naive XML assembly** if hand-processing update-set XML rather than letting the platform export it.
- **Runtime GlideRecord patches against privileged tables (`sys_script_include`, `sys_script`) silently no-op under ICE's automated execution.** Bake the fix into the source and re-export the update set instead.

## The workshop-packaging workflow (per the source SKILL.md's own recommended sequence)

1. `/ice-package update <sys_id> --apply --platform "Australia Patch 2"` (or whatever platform was confirmed with the user).
2. Scan output for downgrades (new < old).
3. Check any "version not found" skip for a renamed-app duplicate-record situation.
4. Manually verify Now Assist for Order Management is at the correct patch version.
5. `/ice-package analyze <sys_id> --platform "..."` to confirm final state.
6. Confirm every workshop fixup script (see `idempotent-seeding.md`) is reachable via its M2M entry, not just present in the base table — re-run analyze after any late-stage fixup.
7. Confirm the package's update sets match the per-scope boundaries of everything the workshop touches.
