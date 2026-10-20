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

# Options: whether to back up each profile's state.db (SQLite memory store).
# Default = NO (skip). state.db is large (~590MB across all profiles) and every
# profile calls this script, so backing it up by default wastes space/time.
# Pass --state to opt in; --no-state or the default skips the DB backups.
STATE_DB=0
for arg in "$@"; do
    case "$arg" in
        --no-state) STATE_DB=0 ;;
        --state)    STATE_DB=1 ;;
        -h|--help)  echo "Usage: backup.sh [--no-state] [--state]"; exit 0 ;;
    esac
done
STATE_DB="${BACKUP_STATE_DB:-$STATE_DB}"

BACKUP_ROOT="/home/vblinux/Hermes_BK"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROFILES_DIR="/home/vblinux/.hermes/profiles"
GLOBAL_SKILLS="/home/vblinux/.hermes/skills"
GLOBAL_MEMORIES="/home/vblinux/.hermes/memories"
PERSONALITY_DIR="/home/vblinux/.hermes"

# Auto-detect all profiles (supports new profiles without script modification).
# Only directories count as profiles; a stray config.yaml file in this dir must be ignored.
ALL_PROFILES=""
if [ -d "$PROFILES_DIR" ]; then
    for d in "$PROFILES_DIR"/*/; do
        [ -d "$d" ] || continue
        ALL_PROFILES="$ALL_PROFILES$(basename "$d") "
    done
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
rm -rf "$BACKUP_ROOT/skills" "$BACKUP_ROOT/memories" "$BACKUP_ROOT/cron" "$BACKUP_ROOT/state" "$BACKUP_ROOT/人格檔" "$BACKUP_ROOT/global_skills" "$BACKUP_ROOT/global_memories"
rm -f "$BACKUP_ROOT/config_*.yaml" "$BACKUP_ROOT/config.yaml"
mkdir -p "$BACKUP_ROOT/skills" "$BACKUP_ROOT/memories" "$BACKUP_ROOT/cron" "$BACKUP_ROOT/人格檔" "$BACKUP_ROOT/global_skills" "$BACKUP_ROOT/global_memories"
[ "$STATE_DB" = "1" ] && mkdir -p "$BACKUP_ROOT/state" || true
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

# Backup daytrade_scanner project (day-trade scanner tool)
echo "[project] Backing up /home/vblinux/daytrade_scanner..."
if [ -d "/home/vblinux/daytrade_scanner" ]; then
    rm -rf "$BACKUP_ROOT/Code/daytrade_scanner"
    mkdir -p "$BACKUP_ROOT/Code"
    cp -r "/home/vblinux/daytrade_scanner" "$BACKUP_ROOT/Code/daytrade_scanner"
    echo "  ✓ daytrade_scanner backed up to $BACKUP_ROOT/Code/"
else
    echo "  ⚠ No /home/vblinux/daytrade_scanner found"
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

    # Backup profile SQLite state.db (live persistent memory store) + WAL sidecars.
    # NOTE: state.db is NOT covered by memories/ (.md files); it holds the live DB.
    # Copy db + -shm + -wal together for a consistent hot snapshot of the WAL database.
    if [ "$STATE_DB" = "1" ]; then
        echo "[state] Backing up $profile state.db..."
        mkdir -p "$BACKUP_ROOT/state/$profile"
        cp -p "$PROF_DIR/state.db"      "$BACKUP_ROOT/state/$profile/state.db"      2>/dev/null || true
        cp -p "$PROF_DIR/state.db-shm"  "$BACKUP_ROOT/state/$profile/state.db-shm"  2>/dev/null || true
        cp -p "$PROF_DIR/state.db-wal"  "$BACKUP_ROOT/state/$profile/state.db-wal"  2>/dev/null || true
        if [ -f "$PROF_DIR/state.db" ]; then
            sz=$(stat -c%s "$PROF_DIR/state.db" 2>/dev/null || echo 0)
            echo "  ✓ $profile state.db backed up ($((sz/1024/1024)) MB)"
        else
            echo "  ⚠ No $profile state.db found"
        fi
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
