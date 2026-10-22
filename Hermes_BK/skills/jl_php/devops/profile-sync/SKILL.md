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
- GENERIC / system-level → sync to ALL 8 sub-profiles. Top-level examples: creative, data-science, devops, github, research, mlops, productivity, web, taiwan-stock-query, finance (+ its daytrade-next-day-open-scanner & market-data-apis), hermes-tool-lifecycle, terminal-long-download, web-tools-keyless-setup. Nested under category dirs (media/): view-comfyui-glb, 3d-print-mesh-repair, comfyui-image-to-3d — the user's fully-delegated 3D/comfyui workflow.
- FAMILY-SPECIFIC → stay in their family only, never cross:
  - jl-delegation-workflow → jl_* only
  - vpos-delegation-workflow → vpos_* only
  - project skills: layui-development, cdp-web-test, content-alignment, original-site-content-alignment, site-link-audit, deployment-iron-rules, month-select-regression-guard, project-finalization (jl_); concurrency-audit, hermes-backup, kanban, refactoring-qa-review, sqlite-connection-string-audit, subagent-delegation (vpos_).

## Steps
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
- A skill may exist at BOTH top-level and a category subdir (e.g. hermes-tool-lifecycle, terminal-long-download, web-tools-keyless-setup). Sync every level so profiles mirror the hub. NOTE: as of 2026-10-22 hermes-tool-lifecycle has DIVERGENT content between its top-level copy and devops/ nested copy in the hub — flag to user before consolidating; do not silently pick one.