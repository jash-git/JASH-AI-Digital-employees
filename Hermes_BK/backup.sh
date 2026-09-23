#!/bin/bash
# Hermes_BK - Backup Script
# Backs up all Hermes profile data to /home/vblinux/Hermes_BK/
# NOTE: Must be run with sudo (backup directories are root-owned)

set -euo pipefail

# Auto-elevate to root if needed (backup dirs are root-owned)
if [ "$(id -u)" -ne 0 ]; then
    echo "⚠ Backup directories are root-owned. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

BACKUP_ROOT="/home/vblinux/Hermes_BK"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROFILES_DIR="/home/vblinux/.hermes/profiles"
GLOBAL_SKILLS="/home/vblinux/.hermes/skills"
GLOBAL_MEMORIES="/home/vblinux/.hermes/memories"
PERSONALITY_DIR="/home/vblinux/.hermes"

# Auto-detect all profiles (supports new profiles without script modification)
ALL_PROFILES=""
if [ -d "$PROFILES_DIR" ]; then
    ALL_PROFILES=$(ls -1 "$PROFILES_DIR" | tr '\n' ' ')
fi
if [ -z "$ALL_PROFILES" ]; then
    echo "WARNING: No profiles found in $PROFILES_DIR"
    ALL_PROFILES="jl_lead"  # fallback
fi

echo "=== Hermes Backup ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup root: $BACKUP_ROOT"

# Create backup directories (must be created manually with sudo first)
# mkdir -p $BACKUP_ROOT/skills/{jl_lead,jl_php,jl_qa,jl_ui}
# mkdir -p $BACKUP_ROOT/memories
# mkdir -p $BACKUP_ROOT/global_skills
# mkdir -p $BACKUP_ROOT/global_memories
# mkdir -p $BACKUP_ROOT/人格檔
# 🧹 CLEAN OLD BACKUP DATA TO AVOID RESIDUE
# CRITICAL: Must clear ALL old backup data BEFORE creating fresh directories.
# Pitfall: If directories already exist with stale data, cp -r will merge/overwrite
# unpredictably. Always start from a clean slate.
echo "🧹 Clearing old backup data and recreating directories..."
rm -rf "$BACKUP_ROOT/skills" "$BACKUP_ROOT/memories" "$BACKUP_ROOT/cron" "$BACKUP_ROOT/人格檔" "$BACKUP_ROOT/global_skills" "$BACKUP_ROOT/global_memories"
rm -f "$BACKUP_ROOT/config_*.yaml" "$BACKUP_ROOT/config.yaml"
mkdir -p "$BACKUP_ROOT/skills" "$BACKUP_ROOT/memories" "$BACKUP_ROOT/cron" "$BACKUP_ROOT/人格檔" "$BACKUP_ROOT/global_skills" "$BACKUP_ROOT/global_memories"
echo "✓ Old data cleared. Fresh directories created."
echo ""

# Backup global skills
echo "[1] Backing up global skills..."
if [ -d "$GLOBAL_SKILLS" ]; then
    cp -r "$GLOBAL_SKILLS/"* "$BACKUP_ROOT/global_skills/" 2>/dev/null || true
    echo "  ✓ Global skills backed up"
else
    echo "  ⚠ No global skills found"
fi

# Backup global memories
echo "[2] Backing up global memories..."
if [ -d "$GLOBAL_MEMORIES" ]; then
    cp "$GLOBAL_MEMORIES/"* "$BACKUP_ROOT/global_memories/" 2>/dev/null || true
    echo "  ✓ Global memories backed up"
else
    echo "  ⚠ No global memories found"
fi

# Backup each profile
for profile in $ALL_PROFILES; do
    PROF_DIR="$PROFILES_DIR/$profile"
    echo ""
    echo "--- Profile: $profile ---"

    # Backup profile skills
    echo "[skills] Backing up $profile skills..."
    if [ -d "$PROF_DIR/skills" ]; then
        mkdir -p "$BACKUP_ROOT/skills/$profile"
        cp -r "$PROF_DIR/skills/"* "$BACKUP_ROOT/skills/$profile/" 2>/dev/null || true
        echo "  ✓ $profile skills backed up"
    else
        echo "  ⚠ No $profile skills found"
    fi

    # Backup profile memories (isolated per profile)
    echo "[memories] Backing up $profile memories..."
    if [ -d "$PROF_DIR/memories" ]; then
        mkdir -p "$BACKUP_ROOT/memories/$profile"
        cp "$PROF_DIR/memories/"* "$BACKUP_ROOT/memories/$profile/" 2>/dev/null || true
        echo "  ✓ $profile memories backed up"
    else
        echo "  ⚠ No $profile memories found"
    fi

    # Backup SOUL.md
    echo "[soul] Backing up $profile SOUL.md..."
    if [ -f "$PROF_DIR/SOUL.md" ]; then
        cp "$PROF_DIR/SOUL.md" "$BACKUP_ROOT/人格檔/${profile}_SOUL.md"
        echo "  ✓ $profile SOUL.md backed up"
    else
        echo "  ⚠ No $profile SOUL.md found"
    fi

    # Backup profile config.yaml
    echo "[config] Backing up $profile config.yaml..."
    if [ -f "$PROF_DIR/config.yaml" ]; then
        cp "$PROF_DIR/config.yaml" "$BACKUP_ROOT/config_${profile}.yaml"
        echo "  ✓ $profile config.yaml backed up"
    else
        echo "  ⚠ No $profile config.yaml found"
    fi

    # Backup profile cron jobs
    echo "[cron] Backing up $profile cron jobs..."
    if [ -d "$PROF_DIR/cron" ]; then
        mkdir -p "$BACKUP_ROOT/cron/$profile"
        cp -r "$PROF_DIR/cron/"* "$BACKUP_ROOT/cron/$profile/" 2>/dev/null || true
        echo "  ✓ $profile cron jobs backed up"
    else
        echo "  ⚠ No $profile cron jobs found"
    fi
done

# Backup global personality SOUL.md (root level)
echo ""
echo "[soul] Backing up global SOUL.md..."
if [ -f "$PERSONALITY_DIR/SOUL.md" ]; then
    cp "$PERSONALITY_DIR/SOUL.md" "$BACKUP_ROOT/人格檔/global_SOUL.md"
    echo "  ✓ Global SOUL.md backed up"
else
    echo "  ⚠ No global SOUL.md found"
fi

# Backup global config.yaml (root level)
echo "[config] Backing up global config.yaml..."
if [ -f "$PERSONALITY_DIR/config.yaml" ]; then
    cp "$PERSONALITY_DIR/config.yaml" "$BACKUP_ROOT/config.yaml"
    echo "  ✓ Global config.yaml backed up"
else
    echo "  ⚠ No global config.yaml found"
fi

echo ""
echo "=== Backup Complete ==="
echo "Files saved to: $BACKUP_ROOT/"
ls -la "$BACKUP_ROOT/"
echo ""
echo "Backup sizes:"
du -sh "$BACKUP_ROOT"/* 2>/dev/null || true

exit 0
