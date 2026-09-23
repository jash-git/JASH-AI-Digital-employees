# Hermes Profile Backup & Restore Operations

## Trigger
Use when: backing up Hermes profile data (skills, memories, SOUL.md, config, cron), restoring profiles from backup, verifying backup integrity, troubleshooting backup conflicts or missing data.

## Backup Script
**Location**: `/home/vblinux/Hermes_BK/backup.sh`

Run with sudo (backup directories are root-owned):
```bash
sudo bash /home/vblinux/Hermes_BK/backup.sh
```

## Workflow

### 1. Backup (Full Clean Backup)
The script performs a **clean-slate backup** — always clears old data first:

1. **Clear all old backup directories**: `skills/`, `memories/`, `cron/`, `人格檔/`, `global_skills/`, `global_memories/`
2. **Clear all old config files**: `config_*.yaml`, `config.yaml`
3. **Recreate fresh directories** with `mkdir -p`
4. **Backup global skills** from `/home/vblinux/.hermes/skills/`
5. **Backup global memories** from `/home/vblinux/.hermes/memories/`
6. **For each profile** (auto-detected from `/home/vblinux/.hermes/profiles/`):
   - Skills → `skills/{profile}/`
   - Memories → `memories/{profile}/` (**isolated per profile**)
   - SOUL.md → `人格檔/{profile}_SOUL.md`
   - config.yaml → `config_{profile}.yaml`
   - Cron jobs → `cron/{profile}/`
7. **Backup global SOUL.md** and **global config.yaml**

### 2. Restore
To restore a profile from backup:
```bash
# Example: restore vpos_lead
sudo cp -r /home/vblinux/Hermes_BK/skills/vpos_lead/* /home/vblinux/.hermes/profiles/vpos_lead/skills/
sudo cp /home/vblinux/Hermes_BK/memories/vpos_lead/* /home/vblinux/.hermes/profiles/vpos_lead/memories/
sudo cp /home/vblinux/Hermes_BK/人格檔/vpos_lead_SOUL.md /home/vblinux/.hermes/profiles/vpos_lead/SOUL.md
sudo cp /home/vblinux/Hermes_BK/config_vpos_lead.yaml /home/vblinux/.hermes/profiles/vpos_lead/config.yaml
```

### 3. Verify Backup Integrity
After running backup, verify:
- `skills/` has one subdirectory per profile
- `memories/` has one subdirectory per profile (NOT flat files)
- `人格檔/` has `{profile}_SOUL.md` for each profile
- `config_{profile}.yaml` exists for each profile
- `cron/{profile}/` has cron data for each profile

See `references/backup-verification.md` for a verification checklist.

## Pitfalls

### ⚠️ Memories MUST be isolated per profile
**CRITICAL**: Each profile's `MEMORY.md` must be backed up to `memories/{profile}/` as a separate subdirectory. If all `MEMORY.md` files are copied to the same flat directory, later profiles will overwrite earlier ones, causing data loss.

**Wrong** (flat, causes overwrite):
```bash
cp "$PROF_DIR/memories/"* "$BACKUP_ROOT/memories/"  # BAD — overwrites!
```

**Correct** (isolated subdirectory):
```bash
mkdir -p "$BACKUP_ROOT/memories/$profile"
cp "$PROF_DIR/memories/"* "$BACKUP_ROOT/memories/$profile/"  # GOOD
```

### ⚠️ Always clear old data before backup
The script MUST clear ALL old backup data before creating fresh directories. If old directories already exist with stale data, `cp -r` will merge/overwrite unpredictably. Always start from a clean slate.

### ⚠️ Backup directories must be created with sudo
Backup directories are root-owned. The script auto-elevates via `exec sudo "$0" "$@"`, but manual operations also need `sudo`.

### ⚠️ Cron output directories may have permission issues
Some profile cron `output/` directories may be root-owned and inaccessible without `sudo`. Use `sudo` for any manual cron operations.

## Directory Structure

```
/home/vblinux/Hermes_BK/
├── skills/
│   ├── vpos_lead/          ← profile-specific skills
│   ├── vpos_ui/
│   ├── vpos_core/
│   ├── vpos_qa/
│   ├── jl_lead/
│   └── ...
├── memories/
│   ├── vpos_lead/          ← profile-specific memories (ISOLATED!)
│   ├── vpos_ui/
│   ├── vpos_core/
│   ├── vpos_qa/
│   ├── jl_lead/
│   ├── USER.md             ← global user profile
│   └── MEMORY.md           ← global memories
├── cron/
│   ├── vpos_lead/          ← profile-specific cron jobs
│   └── ...
├── 人格檔/
│   ├── vpos_lead_SOUL.md   ← profile personality
│   └── ...
├── global_skills/          ← shared skills (apple, devops, etc.)
├── global_memories/        ← global memories (USER.md)
├── config_{profile}.yaml   ← per-profile config
└── config.yaml             ← global config
```

## Auto-detection
The script auto-detects all profiles from `/home/vblinux/.hermes/profiles/`. New profiles are automatically included without script modification.

## Related
- See `references/backup-verification.md` for detailed verification steps
