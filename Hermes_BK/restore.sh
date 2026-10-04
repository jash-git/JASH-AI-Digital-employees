#!/bin/bash
# Hermes_BK - Restore Script
# Restores all Hermes profile data from /home/vblinux/Hermes_BK/ back into ~/.hermes/
# Mirrors backup.sh in reverse (see backup_docs.md for the mapping).
#
# WHY sudo is needed here (and NOT forbidden):
#   The backup files are mode 600, owned by root. The normal user CANNOT read them.
#   So reading requires `sudo cat`, but we must write the destination as vblinux so
#   ~/.hermes stays user-owned and Hermes' permissions aren't broken. We never let
#   sudo write into ~/.hermes directly (that would make files root-owned).
#
# SAFETY: This OVERWRITES live ~/.hermes data. The script stops the Hermes gateway
# (user systemd service) before restoring and restarts it afterwards, so we don't
# clobber in-progress work or hit locked files. Use --no-gateway to skip all gateway ops.

set -euo pipefail

GATEWAY_SERVICE="hermes-gateway.service"
SKIP_GATEWAY=0

# Optional flag: --no-gateway (or SKIP_GATEWAY=1) to leave the gateway running.
for arg in "$@"; do
    case "$arg" in
        --no-gateway) SKIP_GATEWAY=1 ;;
    esac
done

# --- Gateway helpers ---------------------------------------------------------
gateway_stop() {
    echo "⏹ Stopping $GATEWAY_SERVICE..."
    if systemctl --user stop "$GATEWAY_SERVICE" 2>/dev/null; then
        echo "  ✓ Gateway stopped"
    else
        echo "  ⚠ Could not stop gateway (is it running / systemd user available?)" >&2
    fi
}

gateway_start() {
    echo "▶ Starting $GATEWAY_SERVICE..."
    if systemctl --user start "$GATEWAY_SERVICE" 2>/dev/null; then
        echo "  ✓ Gateway started"
    else
        echo "  ⚠ Could not start gateway automatically. Start it manually:" >&2
        echo "     systemctl --user start $GATEWAY_SERVICE" >&2
    fi
}

# --- Backup read helper ------------------------------------------------------
# Reads a backup file/dir as root (files are 600 root) into a temp file/dir that is
# owned by the current user, then returns its path. This keeps destination writes
# user-owned while still being able to read root-only backups.
read_backup() {
    # $1 = source path in backup; prints absolute path of a user-readable copy on stdout.
    local src="$1" tmp out
    if [ ! -e "$src" ]; then
        return 1
    fi
    tmp="$(mktemp -d /tmp/hermes_restore.XXXXXX)"
    chmod u+rwx "$tmp"
    if [ -d "$src" ]; then
        # Copy as root, then chown to current user so we can read it.
        sudo cp -a "$src" "$tmp/data" 2>/dev/null || { rm -rf "$tmp"; return 1; }
        sudo chown -R "$(id -u):$(id -g)" "$tmp/data"
        out="$tmp/data"
    else
        # cat via sudo -> user-owned temp file (ownership follows the writer).
        out="$tmp/file"
        sudo cat "$src" > "$out" 2>/dev/null || { rm -rf "$tmp"; return 1; }
        chmod u+r "$out"
    fi
    echo "$out"
}

# --- Config ------------------------------------------------------------------
BACKUP_ROOT="/home/vblinux/Hermes_BK"
HOME_DIR="$HOME"                       # ~/.hermes parent
HERMES_DIR="$HOME_DIR/.hermes"
PROFILES_DIR="$HERMES_DIR/profiles"
GLOBAL_SKILLS="$HERMES_DIR/skills"
GLOBAL_MEMORIES="$HERMES_DIR/memories"

# --- Pre-flight checks -------------------------------------------------------
if [ ! -d "$BACKUP_ROOT" ]; then
    echo "❌ Backup root not found: $BACKUP_ROOT" >&2
    exit 1
fi

echo "=== Hermes Restore ==="
echo "Backup source: $BACKUP_ROOT"
echo "Restore target: $HERMES_DIR"
echo ""

# Stop the gateway so we don't clobber in-progress work or hit locked files.
if [ "$SKIP_GATEWAY" -eq 0 ]; then
    gateway_stop
else
    echo "ℹ --no-gateway: leaving gateway running."
fi
echo ""

# Ask which profile to restore (or all). Default = all.
read -r -p "Restore [a]ll profiles, or a single [p]rofile name? (default=all): " CHOICE
CHOICE="${CHOICE:-all}"

if [ "$CHOICE" != "all" ]; then
    ALL_PROFILES="$CHOICE"
else
    # Auto-detect all profiles present in the backup's skills/ or memories/ dirs.
    ALL_PROFILES=""
    if [ -d "$BACKUP_ROOT/skills" ]; then
        ALL_PROFILES=$(ls -1 "$BACKUP_ROOT/skills" | tr '\n' ' ')
    fi
    if [ -z "$ALL_PROFILES" ] && [ -d "$BACKUP_ROOT/memories" ]; then
        ALL_PROFILES=$(ls -1 "$BACKUP_ROOT/memories" | tr '\n' ' ')
    fi
    if [ -z "$ALL_PROFILES" ]; then
        echo "⚠ No profiles found in backup. Will restore only global data."
    fi
fi

echo ""
echo "Profiles to restore: ${ALL_PROFILES:-<none>}"
echo ""

# --- Restore a single file ---------------------------------------------------
restore_file() {
    # $1 = source path (in backup), $2 = destination path
    local src="$1" dst="$2" copy rc=0
    if [ ! -e "$src" ]; then
        echo "  ⚠ Missing in backup: $src"
        return 1
    fi
    mkdir -p "$(dirname "$dst")"
    copy="$(read_backup "$src")" || { echo "  ❌ Failed to read: $src"; return 1; }
    if cp -a "$copy" "$dst"; then
        echo "  ✓ $(basename "$src") -> $dst"
    else
        echo "  ❌ Failed to write: $dst"
        rc=1
    fi
    rm -rf "$(dirname "$copy")"
    return $rc
}

# --- Restore a directory tree ------------------------------------------------
restore_dir() {
    # $1 = source dir (in backup), $2 = destination dir
    local src="$1" dst="$2" copy rc=0
    if [ ! -d "$src" ]; then
        echo "  ⚠ Missing in backup: $src"
        return 1
    fi
    mkdir -p "$dst"
    copy="$(read_backup "$src")" || { echo "  ❌ Failed to read: $src"; return 1; }
    if cp -a "$copy/." "$dst/" 2>/dev/null; then
        echo "  ✓ $(basename "$src"/) -> $dst/"
    else
        echo "  ❌ Failed to write: $dst"
        rc=1
    fi
    rm -rf "$(dirname "$copy")"
    return $rc
}

# --- Global data -------------------------------------------------------------
echo "[G] Restoring global skills..."
restore_dir "$BACKUP_ROOT/global_skills" "$GLOBAL_SKILLS" || true

echo "[G] Restoring global memories..."
restore_dir "$BACKUP_ROOT/global_memories" "$GLOBAL_MEMORIES" || true

echo "[G] Restoring global SOUL.md..."
restore_file "$BACKUP_ROOT/人格檔/global_SOUL.md" "$HERMES_DIR/SOUL.md" || true

echo "[G] Restoring global config.yaml..."
restore_file "$BACKUP_ROOT/config.yaml" "$HERMES_DIR/config.yaml" || true

# --- Per-profile data --------------------------------------------------------
for profile in $ALL_PROFILES; do
    PROF_SRC="$PROFILES_DIR/$profile"
    echo ""
    echo "--- Profile: $profile ---"

    restore_dir "$BACKUP_ROOT/skills/$profile" "$PROF_SRC/skills" || true
    restore_dir "$BACKUP_ROOT/memories/$profile" "$PROF_SRC/memories" || true
    restore_file "$BACKUP_ROOT/人格檔/${profile}_SOUL.md" "$PROF_SRC/SOUL.md" || true
    restore_file "$BACKUP_ROOT/config_${profile}.yaml" "$PROF_SRC/config.yaml" || true
    restore_dir "$BACKUP_ROOT/cron/$profile" "$PROF_SRC/cron" || true
done

# --- daytrade_scanner project + tool symlink ---------------------------------
# backup.sh copies the live project to Hermes_BK/Code/daytrade_scanner (root-owned,
# since backup runs with sudo) and does NOT back up the tools/ symlink. Restore both:
echo ""
echo "[project] Restoring /home/vblinux/daytrade_scanner..."
PROJ_DST="/home/vblinux/daytrade_scanner"
if [ -d "$BACKUP_ROOT/Code/daytrade_scanner" ]; then
    copy="$(read_backup "$BACKUP_ROOT/Code/daytrade_scanner")" || { echo "  ❌ Failed to read project backup"; }
    if [ -n "${copy:-}" ] && cp -a "$copy/." "$PROJ_DST/" 2>/dev/null; then
        # Backup copies are root-owned via sudo → chown back to current user.
        chown -R "$(id -u):$(id -g)" "$PROJ_DST" 2>/dev/null || true
        echo "  ✓ daytrade_scanner restored -> $PROJ_DST"
    else
        echo "  ❌ Failed to write project restore: $PROJ_DST"
    fi
    [ -n "${copy:-}" ] && rm -rf "$(dirname "$copy")" 2>/dev/null || true
else
    echo "  ⚠ No daytrade_scanner in backup (Hermes_BK/Code/daytrade_scanner)"
fi

echo ""
echo "[tool] Rebuilding ~/.hermes/tools/daytrade_scanner symlink..."
TOOL_LINK="$HERMES_DIR/tools/daytrade_scanner"
if [ -e "$PROJ_DST" ]; then
    ln -sfn "$PROJ_DST" "$TOOL_LINK" && echo "  ✓ symlink -> $TOOL_LINK" || echo "  ⚠ Could not create symlink"
else
    echo "  ⚠ Skipping symlink (project not restored)"
fi

# --- Done --------------------------------------------------------------------
echo ""

# Restart the gateway so it picks up the restored data (unless skipped).
if [ "$SKIP_GATEWAY" -eq 0 ]; then
    echo "⏸ Pausing before restart to let you review restored files..."
    read -r -p "Press Enter after reviewing, or type 'skip' to leave the gateway stopped: " REVIEW
    if ! echo "$REVIEW" | grep -qi '^skip'; then
        gateway_start
    else
        echo "ℹ Gateway left stopped. Start it with: systemctl --user start $GATEWAY_SERVICE"
    fi
else
    echo "ℹ --no-gateway: restart the gateway manually when ready."
fi

echo ""
echo "=== Restore Complete ==="
echo "Restored into: $HERMES_DIR/"
echo ""

exit 0
