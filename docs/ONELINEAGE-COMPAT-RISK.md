# OneLineage Compatibility Risk Analysis: SM-S918U (Android 14)

**Status:** Static review only. No script has been executed on the device.
**Source pin:** `f5f5a7a0999f806dfd618d4dd2a80bfda50b258d`
**Date:** 2026-10-27

## 1. Shared-Storage Binding: Critical Risk

### What happens

`master_prepare.sh` (step 4) recursively bind-mounts the host's `/mnt` into the
container rootfs:

```sh
mount --rbind /mnt "$ROOTFS/mnt"
```

After `pivot_root` in `master_inner.sh`, the container's `/data/media` is the
host's real `/data/media`. The script then executes:

```sh
chown -R 1023:1023 /data/media
chmod -R 777 /data/media
```

### Impact on this device

- **All 98,859 shared files** (92 GB) would have their ownership changed to
  `media_rw:media_rw` and permissions set to `rwxrwxrwx`.
- Photos, documents, recordings, downloads, and app-specific media directories
  (`/Android/media/<package>`) are all affected.
- Any process running as any UID could read or modify every file.
- The change is **not reversible by the return script** (see §2).

### Mitigation required before any use

1. Snapshot ownership/permissions of `/data/media` before the takeover
   (e.g., `find /data/media -exec stat -c '%u %g %a %n' {} \; > /tmp/perms.bak`).
2. Restore from that snapshot after return, or accept permanent permission
   degradation.
3. Alternatively, patch `master_inner.sh` to skip the `chown`/`chmod` lines and
   rely on the existing permissive SELinux mode during the session.

## 2. State Restoration Gaps

The return script (`return_to_oneui.sh`) restores:

- SELinux enforcing mode (`setenforce 1`)
- Host service daemons (surfaceflinger, zygote, audioserver, cameraserver, media, wificond)
- Storage bind mounts (`/storage/emulated/0`, `/mnt/user/0/emulated`)
- One UI launcher database

It does **not** restore:

| Item | Set by | Consequence if un-restored |
|------|--------|----------------------------|
| `persist.sys.disable_rescue=true` | `switch_to_lineage.sh:155` | SystemUI rescue/panic handler stays disabled; user cannot trigger a soft recovery from the lock screen |
| `/data/media` ownership & permissions | `master_inner.sh` (chown/chmod) | All shared files remain 777 media_rw:media_rw permanently |
| Network routing rules (table 4242, rule priority 14999) | `net_fix.sh` created by `master_prepare.sh` | Stale ip-rule may interfere with future network configuration changes |
| Guest-written app data in bridged `/data/app`, `/data/user` trees | installd/artd during guest session | Orphaned files consume storage; host PMS does not know about them |
| `/data/misc/profiles` guest writes | ART profiling during guest session | Stale profile data may affect host JIT behaviour on next boot |

### `persist.sys.disable_rescue`

This property is persistent (survives reboot). The only recovery is:

```sh
setprop persist.sys.disable_rescue false
# or
adb shell settings put global disable_rescue 0
```

A patched return script should include this line.

## 3. Android 14 vs Android 16 Targeting

The upstream project targets Android 16 (One UI 7 / GSI). This phone runs
Android 14 (One UI 6.1). Specific concerns:

- **APEX layout:** Android 14 uses a different APEX set than 16. The script's
  hard-coded list (art, i18n, runtime, sdkext, etc.) may not match this build's
  `/system/apex` contents. Missing APEXes cause `PMS` abort at guest boot.
- **PermissionController RANGING patch:** The script patches Samsung's
  PermissionController for a missing `RANGING` permission. On Android 14 the
  permission set differs; the patched APK from an Android 16 build may be
  incompatible.
- **Vold / FBE:** Android 14 Vold has a different AIDL surface than 16. The
  guest's Vold binary (from the GSI) may not interoperate with the host's
  FBE-encrypted data partition.
- **SELinux policy:** The guest expects permissive mode (set by `setenforce 0`).
  If any host daemon enforces a label that the guest process cannot access even
  in permissive mode (e.g., audit denials that trigger a panic), behaviour is
  undefined.

## 4. KernelSU Dependency

The scripts assume a KernelSU-managed root environment:

- `busybox` at `/data/adb/ksu/bin/busybox`
- `su` binary from `/data/adb/ksud`
- Loop device node creation (`mknod /dev/loop*`)
- `pivot_root` (requires CAP_SYS_ADMIN, i.e., root)

This phone has **no root** (bootloader locked, verified boot green, no `su`).
The prerequisite root exploit (CVE-2026-43499 / `remove_waiter`) is identified
but **unverified**; the candidate profile has null `kernel_phys_offset` and
`cred.usage_offset`. Without a working root, none of these scripts can run.

## 5. Verdict

Running OneLineage on this device as-is would:

1. Permanently degrade shared-storage permissions (all files → 777).
2. Leave `persist.sys.disable_rescue=true` set indefinitely.
3. Potentially fail at guest boot due to APEX/permission mismatches (Android 14 vs 16).
4. Leave orphaned app data and stale network rules.

**Do not run.** The following must be resolved first. Status as of
2026-10-27 (this session):

- [x] Working root path with a matching kernel-module flavor:
      DirtyFrag v1.16 selected over the unverified futex profile and the
      per-firmware BOPE port; all offline gates closed, evidence in
      `work/device-evidence/dirtyfrag-gates.json`, on-device sequence in
      `docs/ROOT-RUNBOOK.md`.
- [x] Patched `master_inner.sh` that skips or scopes the `chown`/`chmod` on
      `/data/media`, superseded by an overlayfs isolation layer: the guest
      never gets a writable view of the host tree at all
      (`patches/onelineage/`, `CONFIG_OVERLAY_FS=y` verified in this
      firmware's kernel config).
- [x] Patched `return_to_oneui.sh` that restores `persist.sys.disable_rescue`,
      network rules, and file permissions, plus the four temporary audio
      properties, the dnsproxyd socket mode, and a permission snapshot/restore
      pair for the plain-bind fallback (`patches/onelineage/`).
- [x] APEX set verification against this specific firmware: the live
      `/system/apex` inventory (36 apexes, `com.google.android.*` names plus
      Samsung/lifeguard/shell/spqr/wifi) was captured this session. The
      guest mounts the GSI's own `com.android.*` apexes by name and binds
      the host's `/apex/*` mountpoints name-agnostically, so the upstream
      hard-coded list cannot desync from the host set; the remaining
      14-vs-16 apex-content caution is a staged-boot check, not a blocker.
- [x] PermissionController APK compatibility check for Android 14: the
      upstream failure mode (`android.permission.RANGING` undefined →
      PermissionController crash) is triggered by privapp whitelists the
      guest can see. This firmware's guest-visible manifest paths contain
      none: `/vendor/etc/permissions` (53 files, pulled this session) has no
      privapp whitelists and no RANGING; `/odm/etc/permissions` does not
      exist; the only RANGING reference is
      `/system/etc/permissions/privapp-permissions-com.samsung.android.dkey.xml`,
      a host-`/system` path the guest never scans. The patched
      PermissionController still binds as a safety net.

