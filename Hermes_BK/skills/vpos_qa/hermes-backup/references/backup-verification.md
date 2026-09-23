# Backup Verification Checklist

## Quick Verification (after running backup.sh)

Run this to verify all profiles are backed up correctly:

```bash
echo "=== Skills ===" && ls /home/vblinux/Hermes_BK/skills/
echo "=== Memories ===" && ls /home/vblinux/Hermes_BK/memories/
echo "=== SOUL.md ===" && ls /home/vblinux/Hermes_BK/人格檔/
echo "=== Config ===" && ls /home/vblinux/Hermes_BK/config*.yaml
echo "=== Cron ===" && ls /home/vblinux/Hermes_BK/cron/
```

## Expected Output (for 8 profiles)

### skills/
Should contain 8 directories (one per profile):
```
jl_lead  jl_php  jl_qa  jl_ui  vpos_core  vpos_lead  vpos_qa  vpos_ui
```

### memories/
Should contain 8 directories (one per profile) + global files:
```
jl_lead/  jl_php/  jl_qa/  jl_ui/  vpos_core/  vpos_lead/  vpos_qa/  vpos_ui/
USER.md  MEMORY.md  (global files)
```

**CRITICAL**: memories must be per-profile subdirectories, NOT flat MEMORY.md files.

### 人格檔/
Should contain 9 files (8 profiles + 1 global):
```
global_SOUL.md  jl_lead_SOUL.md  jl_php_SOUL.md  jl_qa_SOUL.md  jl_ui_SOUL.md
vpos_core_SOUL.md  vpos_lead_SOUL.md  vpos_qa_SOUL.md  vpos_ui_SOUL.md
```

### config*.yaml
Should contain 9 files (8 profiles + 1 global):
```
config.yaml  config_jl_lead.yaml  config_jl_php.yaml  config_jl_qa.yaml  config_jl_ui.yaml
config_vpos_core.yaml  config_vpos_lead.yaml  config_vpos_qa.yaml  config_vpos_ui.yaml
```

### cron/
Should contain 8 directories (one per profile):
```
jl_lead/  jl_php/  jl_qa/  jl_ui/  vpos_core/  vpos_lead/  vpos_qa/  vpos_ui/
```

## Spot Check Memory Content

Verify each profile's MEMORY.md has unique content (not overwritten):

```bash
for p in vpos_lead vpos_ui vpos_core vpos_qa jl_lead; do
  echo "--- $p ---"
  sudo head -1 /home/vblinux/Hermes_BK/memories/$p/MEMORY.md
done
```

Each should show different content. If two profiles show the same content, the backup failed to isolate memories.

## Common Failure Modes

1. **Flat memories/** — If `memories/MEMORY.md` exists at root level instead of `memories/{profile}/MEMORY.md`, the backup script has a bug (old version).
2. **Missing profiles** — If a profile appears in `profiles/` but not in backup, check if its `memories/` or `skills/` directory exists.
3. **Permission errors** — Some cron `output/` directories may be root-owned and inaccessible without `sudo`.
