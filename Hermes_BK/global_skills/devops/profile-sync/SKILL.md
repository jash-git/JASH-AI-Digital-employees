---
name: profile-sync
description: Sync generic Hermes skills across all 8 profiles on add.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [profiles, skills, sync, cross-profile, hub]
    category: devops
---

## When to Use
Every time you install/create a skill in the default hub (`/home/vblinux/.hermes/skills/`) OR discover a reusable skill living only inside one profile, classify it as generic (sync outward) or family-specific (keep put). The user switches profiles often; a missing generic skill on the other side wastes time re-adding/re-fetching.

## The 8 profiles
default hub = `/home/vblinux/.hermes` (source of truth for generic skills).
Sub-profiles under `/home/vblinux/.hermes/profiles/`: jl_lead, jl_php, jl_qa, jl_ui (PHP/Layui family); vpos_core, vpos_lead, vpos_qa, vpos_ui (Avalonia family).

## Classification rule
- GENERIC / system-level → sync to ALL 8 sub-profiles. Generic examples (top-level categories or nested like devops/): creative, data-science, github, research, mlops, productivity, web, taiwan-stock-query, finance (+ its daytrade-next-day-open-scanner & market-data-apis), and the ops tools hermes-tool-lifecycle / terminal-long-download / web-tools-keyless-setup (all now live under devops/). Nested under category dirs (media/): view-comfyui-glb, 3d-print-mesh-repair, comfyui-image-to-3d — the user's fully-delegated 3D/comfyui workflow.
- FAMILY-SPECIFIC → stay in their family only, never cross:
  - jl-delegation-workflow → jl_* only
  - vpos-delegation-workflow → vpos_* only
  - project skills: layui-development, cdp-web-test, content-alignment, original-site-content-alignment, site-link-audit, deployment-iron-rules, month-select-regression-guard, project-finalization (jl_); concurrency-audit, hermes-backup, kanban, refactoring-qa-review, sqlite-connection-string-audit, subagent-delegation (vpos_).

## Tool — `profile-sync` (installed at /home/vblinux/.hermes/bin/profile-sync, on PATH)
Run this instead of hand-writing cp loops. It classifies, copies to the right profiles, auto-backs up first, then verifies:
- `profile-sync report` — audit which generic skills each profile is missing (read-only). Run FIRST to find gaps.
- `profile-sync sync SKILL... | all` — copy skill(s) or every generic hub skill; auto-backs up unless --no-backup.
- `profile-sync backup [--tag NAME]` — snapshot all profiles' skills/ -> timestamped tarball in ~/.hermes/backups/profile-sync/; keeps newest 5 (prunes older).
- `profile-sync restore ARCHIVE` — restore a previous backup over the profiles.
- Global flags: `--no-backup`, `--all-families` (override family isolation; use sparingly).
The tool mirrors hub generic skills into every profile and skips cross-family delegation workflows automatically. Verified 2026-10-22 (report/sync-single/sync-multi/sync-all/backup/prune/restore all pass).

## Steps (manual fallback only if the tool is unavailable)
1. Enumerate ALL skill dirs recursively under the hub, including category subdirs (media/, mlops/, ...): `find /home/vblinux/.hermes/skills -name SKILL.md` (skip .archive/). Do NOT rely on a top-level listing only (use search_files target='files') — nested skills get missed.
2. Classify each as generic vs family-specific per rules above.
3. For generic: `cp -r <hub>/skills/<relpath> /home/vblinux/.hermes/profiles/<p>/skills/<relpath>` (preserve category relpath; mkdir -p parent dir) for each of the 8 profiles (skip if already present).
4. If a reusable skill exists only in sub-profiles and is byte-identical across them, promote it into the hub first so future syncs cover it.
5. Verify for a given skill relpath: `for p in /home/vblinux/.hermes/profiles/*/; do [ -d "$p/skills/<relpath>" ] || echo "MISSING $(basename $p): <relpath>"; done` — should print nothing.

## Gotchas
- canvas-game is an EMPTY skeleton (references/ only, no SKILL.md, 0 files) — do NOT propagate it; ask the user to fill or delete it.
- Before promoting a cross-family skill, confirm copies are identical (md5sum each profile's SKILL.md); only then copy into hub.
- Do not edit another profile's memories/skills unless the user directs it. Backup after bulk changes: `sudo /home/vblinux/Hermes_BK/backup.sh`.
- Skills can live under category subdirs (media/, mlops/...). Always recurse (`find ... -name SKILL.md`, or search_files target='files'), never only a top-level listing — that is exactly how view-comfyui-glb / 3d-print-mesh-repair / comfyui-image-to-3d were missed.
- image-to-3d shows in the available-skills list but has NO files under .hermes (stub/plugin-provided) — nothing to sync.
- ONE canonical copy per skill. Hermes resolves skills by NAME, so two same-named skills (e.g. a top-level + a devops/ copy) mean only ONE loads and the other is shadowed — you can't "use both". As of 2026-10-22 we consolidated hermes-tool-lifecycle / terminal-long-download / web-tools-keyless-setup to single copies under devops/. If a duplicate ever reappears: keep the COMPLETE/better version, archive or delete the other (never leave two same-named skills). hermes-tool-lifecycle's complete version kept its devops/ copy because it held the state.db backup warning the top-level one lacked.