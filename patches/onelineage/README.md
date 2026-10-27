# OneLineage data-isolation and state-restoration patch set

Patched versions of OneLineage's takeover scripts for a **personal, no-wipe**
device. Derived from the pinned upstream source at
`work/sources/OneLineage` (commit `f5f5a7a0999f806dfd618d4dd2a80bfda50b258d`).
**Nothing here has been executed on any device.** See
`docs/ONELINEAGE-COMPAT-RISK.md` for the risk analysis these patches close.

## What upstream does wrong on a personal phone

1. `master_prepare.sh` plain-binds the host's real `/data/media` into the
   guest rootfs, and `master_prepare.sh`'s `/mnt` rbind also exposes
   every host FUSE/vendor mount to the guest.
2. `master_inner.sh` then runs `chown -R 1023:1023 /data/media` and
   `chmod -R 777 /data/media` on the real shared-file tree (98,859 files on
   this phone), irreversibly.
3. `switch_to_lineage.sh` sets `persist.sys.disable_rescue=true` (persists
   across reboots), rewrites four audio properties, chmods `/dev/socket/dnsproxyd`
   to 666, and its generated `net_fix.sh` installs an `ip rule` at priority
   14999 plus routing table 4242 (and deletes the rule at 31999).
4. `return_to_oneui.sh` restores SELinux and services but none of the above.

## What the patch set changes

| File | Change |
|------|--------|
| `master_prepare.sh` | `/data/media` becomes a **read-only-over-host overlayfs** (`CONFIG_OVERLAY_FS=y` on this firmware): the guest reads host files, all writes and mode changes land in the private upper `media-overlay/upper`, host tree never modified. Falls back to the upstream plain bind (with the snapshot safety net) if the overlay mount fails. The `/mnt` rbind becomes a private tmpfs. |
| `master_inner.sh` | The `chown -R 1023:1023` / `chmod -R 777` of `/data/media` are **removed**. Under the overlay they would only touch the private upper; `ensure_app_storage.sh` already creates per-app and skeleton dirs with sane ownership. |
| `switch_to_lineage.sh` | Takes `/data/local/tmp/media_perms_snapshot.tsv` (path, uid, gid, mode of every file under `/data/media`) before anything runs. |
| `return_to_oneui.sh` | New step 4b: detaches the overlay, deletes `persist.sys.disable_rescue`, deletes the four temporary audio props, restores `/dev/socket/dnsproxyd` to `root:inet 660`, removes the 14999 rule and flushes table 4242, restarts `netd` so One UI's routing rules and BPF configuration map rebuild, restores the permission snapshot if present, and optionally exports guest-session files from the upper when `$STAGE/export_upper.flag` exists. |

New helper scripts:

- `snapshot_media_perms.sh` records path/uid/gid/mode of the whole
  `/data/media` tree. Read-only (`find` + `stat`).
- `restore_media_perms.sh` replays that snapshot. Never creates or deletes
  files; reports any entries that could not be restored.

## Trade-offs you are accepting

- Guest-session files (screenshots, downloads, edits) live in the overlay
  upper at rest, which is not per-user FBE-encrypted the way `/data/media`
  normally is, until exported or deleted. Export copies them into
  `/data/media` without touching existing files' ownership.
- The `ip rule del priority 31999` done by upstream's `net_fix.sh` cannot be
  undone exactly (the original rule is unknown); the `netd` restart lets the
  host rebuild its ruleset, which is what One UI would do on the next network
  change anyway.
- The overlay makes the guest's shared storage read-mostly-host + private
  writes; apps that expect to modify existing host files see their changes
  disappear on return unless exported.

## Applying

Copy the four `.sh` files plus the two helpers into the OneLineage app stage
(`/data/local/tmp/lineage_stage/`) or re-pack them into the app assets, in
place of the upstream scripts of the same names. Order at runtime is
unchanged: `switch_to_lineage.sh` → `master_prepare.sh` → `master_inner.sh`,
return via `return_to_oneui.sh`.

The full diff against the pinned upstream is `onelineage-isolation.patch`.

## Remaining gates before any install on this phone

See `docs/ONELINEAGE-COMPAT-RISK.md`; the checklist there tracks what is
resolved (storage isolation, state restoration) and what still needs a staged
test (GSI framework vs host apex contents, first-guest-boot log review).
