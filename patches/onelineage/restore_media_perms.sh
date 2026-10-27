#!/system/bin/sh
# Restores the ownership and modes recorded by snapshot_media_perms.sh.
# return_to_oneui.sh (patched) runs it automatically when a snapshot exists.
# Only needed on the plain-bind fallback path, or after any other code
# rewrote /data/media ownership. Never creates or deletes files.
#
# Files the guest created during the session are not in the snapshot; they
# keep whatever ownership the guest used. Re-run the snapshot afterwards if
# you want a fresh baseline.

SNAP="${1:-/data/local/tmp/media_perms_snapshot.tsv}"
[ -f "$SNAP" ] || { echo "restore: no snapshot at $SNAP"; exit 1; }

restored=0
failed=0
TAB="	"
while IFS="$TAB" read -r path uid gid mode; do
    [ -n "$path" ] || continue
    if [ -e "$path" ]; then
        if chown "$uid:$gid" "$path" 2>/dev/null && chmod "$mode" "$path" 2>/dev/null; then
            restored=$((restored + 1))
        else
            failed=$((failed + 1))
        fi
    fi
done < "$SNAP"

echo "restore: $restored entries restored from $SNAP"
[ "$failed" -eq 0 ] || echo "restore: $failed entries FAILED (inspect manually)"
