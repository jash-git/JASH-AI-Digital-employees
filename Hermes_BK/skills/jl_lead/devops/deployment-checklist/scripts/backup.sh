#!/bin/bash
# Hermes_BK - Backup Script
# Backs up all Hermes profile data to /home/vblinux/Hermes_BK/
# Usage: bash /home/vblinux/Hermes_BK/backup.sh
#
# Prerequisites (run once with sudo):
#   sudo mkdir -p /home/vblinux/Hermes_BK/{skills/{jl_lead,jl_php,jl_qa,jl_ui},memories,global_skills,global_memories,人格檔}
#   sudo chown vblinux:vblinux /home/vblinux/Hermes_BK/skills/{jl_lead,jl_php,jl_qa,jl_ui}

set -euo pipefail

BACKUP_ROOT="/home/vblinux/Hermes_BK"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROFILES_DIR="/home/vblinux/.hermes/profiles"
GLOBAL_SKILLS="/home/vblinux/.hermes/skills"
GLOBAL_MEMORIES="/home/vblinux/.hermes/memories"
PERSONALITY_DIR="/home/vblinux/.hermes"

ALL_PROFILES="jl_lead jl_php jl_qa jl_ui"

echo "=== Hermes Backup ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup root: $BACKUP_ROOT"

# Verify directories exist (must be created with sudo first)
[ -d "$BACKUP_ROOT/skills" ] || { echo "ERROR: $BACKUP_ROOT/skills not found"; exit 1; }
[ -d "$BACKUP_ROOT/memories" ] || { echo "ERROR: $BACKUP_ROOT/memories not found"; exit 1; }
[ -d "$BACKUP_ROOT/global_skills" ] || { echo "ERROR: $BACKUP_ROOT/global_skills not found"; exit 1; }
[ -d "$BACKUP_ROOT/global_memories" ] || { echo "ERROR: $BACKUP_ROOT/global_memories not found"; exit 1; }
[ -d "$BACKUP_ROOT/人格檔" ] || { echo "ERROR: $BACKUP_ROOT/人格檔 not found"; exit 1; }

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

    echo "[skills] Backing up $profile skills..."
    if [ -d "$PROF_DIR/skills" ]; then
        mkdir -p "$BACKUP_ROOT/skills/$profile"
        cp -r "$PROF_DIR/skills/"* "$BACKUP_ROOT/skills/$profile/" 2>/dev/null || true
        echo "  ✓ $profile skills backed up"
    else
        echo "  ⚠ No $profile skills found"
    fi

    echo "[memories] Backing up $profile memories..."
    if [ -d "$PROF_DIR/memories" ]; then
        cp "$PROF_DIR/memories/"* "$BACKUP_ROOT/memories/" 2>/dev/null || true
        echo "  ✓ $profile memories backed up"
    else
        echo "  ⚠ No $profile memories found"
    fi

    echo "[soul] Backing up $profile SOUL.md..."
    if [ -f "$PROF_DIR/SOUL.md" ]; then
        cp "$PROF_DIR/SOUL.md" "$BACKUP_ROOT/人格檔/${profile}_SOUL.md"
        echo "  ✓ $profile SOUL.md backed up"
    else
        echo "  ⚠ No $profile SOUL.md found"
    fi

    echo "[config] Backing up $profile config.yaml..."
    if [ -f "$PROF_DIR/config.yaml" ]; then
        cp "$PROF_DIR/config.yaml" "$BACKUP_ROOT/config_${profile}.yaml"
        echo "  ✓ $profile config.yaml backed up"
    else
        echo "  ⚠ No $profile config.yaml found"
    fi
done

# Backup global personality SOUL.md
echo ""
echo "[soul] Backing up global SOUL.md..."
if [ -f "$PERSONALITY_DIR/SOUL.md" ]; then
    cp "$PERSONALITY_DIR/SOUL.md" "$BACKUP_ROOT/人格檔/global_SOUL.md"
    echo "  ✓ Global SOUL.md backed up"
fi

# Backup global config.yaml
echo "[config] Backing up global config.yaml..."
if [ -f "$PERSONALITY_DIR/config.yaml" ]; then
    cp "$PERSONALITY_DIR/config.yaml" "$BACKUP_ROOT/config.yaml"
    echo "  ✓ Global config.yaml backed up"
fi

echo ""
echo "=== Backup Complete ==="
echo "Files saved to: $BACKUP_ROOT/"
ls -la "$BACKUP_ROOT/"
echo ""
echo "Backup sizes:"
du -sh "$BACKUP_ROOT"/* 2>/dev/null || true

exit 0
