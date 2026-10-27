#!/system/bin/sh
# Records the exact path/owner/group/mode of every file and directory under
# /data/media so the plain-bind fallback path can be undone byte-exactly by
# restore_media_perms.sh. switch_to_lineage.sh (patched) runs this
# automatically before the takeover when no snapshot exists. Harmless and
# cheap when the overlayfs path is used instead.
# Read-only over the shared tree: find + stat, no chmod/chown anywhere.

OUT=/data/local/tmp/media_perms_snapshot.tsv
TMP="$OUT.partial"

if ! : > "$TMP" 2>/dev/null; then
    echo "snapshot: cannot write $TMP (need root)"
    exit 1
fi

# toybox on the device provides find and stat; busybox is the fallback.
if [ -x /system/bin/find ] && /system/bin/stat -c '%n' /data/media >/dev/null 2>&1; then
    /system/bin/find /data/media -exec /system/bin/stat -c "%n\t%u\t%g\t%a" {} \; \
        > "$TMP" 2>/dev/null
else
    BB=$(which busybox 2>/dev/null || echo /data/adb/ksu/bin/busybox)
    [ -x "$BB" ] || BB=$(find /data/adb /system /data -name busybox 2>/dev/null | head -n 1)
    "$BB" find /data/media -exec "$BB" stat -c "%n\t%u\t%g\t%a" {} \; > "$TMP" 2>/dev/null
fi

n=$(wc -l < "$TMP")
if [ "$n" -lt 100 ]; then
    echo "snapshot: suspiciously few entries ($n); not replacing any existing snapshot"
    rm -f "$TMP"
    exit 1
fi

mv "$TMP" "$OUT"
echo "snapshot: $OUT written ($n entries)"
