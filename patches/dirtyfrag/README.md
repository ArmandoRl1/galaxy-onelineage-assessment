# DirtyFrag Samsung root fix

Local rebuild of DirtyFrag v1.16 for the SM-S918U (`S918USQS2CXCN`, One UI
6.1, kernel `5.15.123-android13-8`) that makes the KernelSU userspace install
survive Samsung's SEPF policy and opens root to the ADB shell.

**Result on this phone (2026-10-27):** `adb shell su -c id` returns
`uid=0(root) ... context=u:r:ksu:s0` with SELinux still **Enforcing**. Root is
ephemeral; a reboot clears the module and everything returns to stock.

## Why upstream fails on this firmware

Upstream DirtyFrag's chain reaches `ksud late-load` as root, but the installer
aborts at:

```
Failed to change SELinux context for /data/adb/ksud
  1: Invalid argument
```

`restorecon.rs` labels the daemon `u:object_r:ksu_file:s0`, and Samsung's SEPF
policy **does not define the `ksu_file` type**, so the kernel rejects the label
(EINVAL). With the type substituted for a valid one the failure becomes
EACCES instead: the enforcing policy has no relabel rules for the `ksu`
domain either. The daemon therefore never starts and root never reaches the
shell.

## The fix (three changes)

1. **`ExploitRunner.stageBin` (Java).** After staging the manager's
   `libksud.so` as `ksud`, replace the 22-byte string
   `u:object_r:ksu_file:s0` with `u:object_r:installd:s0` (a type that exists
   in this policy, same length) in the staged copy. The manager APK itself is
   untouched, so its signature stays valid.
2. **`bootstrap.c` (native).** Invoke `ksud late-load` with `--allow-shell`
   so `kernelsu.ko` loads with `allow_shell=1`; the kernel then treats ADB
   shell (uid 2000) as an allowed su caller.
3. **`bootstrap.c` (native).** Three-step daemon start:
   first late-load (brings the driver up), then
   `ksud sepolicy patch "permissive ksu"` (makes the ksu domain permissive so
   the relabel cannot be blocked), then a second late-load (the ko is already
   present, so this pass completes the install and starts the daemon).

Note: the userspace daemon install still does not fully complete on this
policy (the relabel of `/data/adb/ksud` remains EACCES), but it does not need
to. Root is provided **in-kernel** via the sucompat hook and `allow_shell`,
and `adb shell su -c <cmd>` works with full write access
(`/data/adb` write verified).

## Build

Requires JDK 21, Android SDK (platforms;android-36, build-tools;37.0.0,
ndk;29.0.14206865, cmake), `local.properties` with `sdk.dir`. The repo's
`app/keystore.jks` is not published; generate a local one:

```sh
keytool -genkeypair -keystore app/keystore.jks -alias dirtyfrag \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass dirtyfrag -keypass dirtyfrag -dname "CN=DirtyFrag Local"
./gradlew assembleRelease
```

Built artifact: `downloads/DirtyFrag-v1.16-samsung-fixed.apk`
(sha256 `9e55d4a814310cb880dc641da0f94e00aed1e68c1286ee211f9593db4606505e`).

Full diff against upstream v1.16: `samsung-root-fix.patch`.

## Runbook (with the fixed APK installed)

1. Open DirtyFrag, SU Manager = KernelSU (diabl0w, `me.weishu.kernelsu`).
2. Run exploit → confirm ("Are you sure").
3. Verify: `adb shell su -c id` → `uid=0(root) ... context=u:r:ksu:s0`.
4. Panic button at any point: reboot, and module, patches and root are gone.

Run evidence: `work/device-evidence/dirtyfrag-run5-applog.txt` (app-side log),
`work/device-evidence/dirtyfrag-run4-logcat.txt` (late-load internals of the
run that isolated the SEPF behavior).
