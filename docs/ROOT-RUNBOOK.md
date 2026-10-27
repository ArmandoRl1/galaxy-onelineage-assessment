# Root runbook: DirtyFrag on SM-S918U (S918USQS2CXCN)

Status as of 2026-10-27 15:05: **root achieved and verified.**
`adb shell su -c id` returns `uid=0(root) gid=0(root) context=u:r:ksu:s0`
with SELinux still Enforcing and full write access (`/data/adb` verified).
Root is **ephemeral**: it lives only in the loaded kernel module and clears
on reboot. No bootloader unlock, no flash, no wipe. The no-wipe constraint
held throughout. The shared-file backup is complete and verified
(`work/device-evidence/backup-verification.json`); private app data is NOT
covered by it.

Achieving this required a local DirtyFrag rebuild, because upstream aborts on this
firmware because Samsung's SEPF policy lacks the `ksu_file` SELinux type
(`ksud` installer dies at `lsetfilecon`). The fix, the build recipe and the
run evidence live in `patches/dirtyfrag/`. The fixed APK is
`downloads/DirtyFrag-v1.16-samsung-fixed.apk`; the installed manager is the
**original** diabl0w KernelSU (`me.weishu.kernelsu`, untouched signature).

Do NOT select KernelSU-Next as the SU manager on this phone: its kernelsu.ko
conflicts with the loaded dfroot.ko and kernel-panics (observed once;
rebooted clean).

## Verified path (reproducible after any reboot)

1. Open DirtyFrag → SU Manager = KernelSU (`me.weishu.kernelsu`).
2. Run exploit → confirm ("Are you sure").
3. `adb shell su -c id` → uid 0. The in-kernel sucompat + `allow_shell=1`
   module param grant shell directly; the ksud userspace daemon is not
   required (its installer is still policy-limited; see
   `patches/dirtyfrag/README.md`).
4. Wireless debugging works identically: pair once (Settings → Developer
   options → Wireless debugging → pairing code), then `adb pair ip:port
   <code>` and `adb connect`. `su` over the TLS transport returns the same
   uid 0, including write access. Security note: any paired adb client gets
   root over the network until the phone reboots (the listener, the pairing
   grant and the root module all clear together).
5. Panic button at any point: reboot returns the phone to clean stock One UI.

## Why this path

Three candidate root paths were assessed:

1. **DirtyFrag v1.16** (CVE-2026-43284, ESP page-cache write). Chosen.
   Generic engine, self-testing, ephemeral, and its module matrix contains an
   exact `android13-5.15` KMI flavor matching this firmware.
2. Root-My-Galaxy / BOPE (pipe-physrw + tty UMH) requires a hand-tuned
   payload per exact firmware; no `CXCN` target exists. Not viable without a
   full port.
3. GhostLock futex profile (CVE-2026-43499, `remove_waiter`). The primitive
   confirmed unpatched in this kernel, but the candidate profile has null
   `kernel_phys_offset` and `cred.usage_offset` and the pselect route is
   ambiguous. Kept as a documented fallback only. Do not guess the missing
   offsets.

DirtyFrag's recovery model is what a no-wipe personal phone needs: the
page-cache patches are memory-only and restored by the app's cleanup, and
`dfroot.ko`/`su`/all module state vanish on reboot. No persistent artifact is
written to any partition.

## Gates verified (evidence in `work/device-evidence/dirtyfrag-gates.json`)

- Kernel predates the May 2026 fix (built 2024-04-03), statically expected
  vulnerable; the app's own self-test is the decisive gate.
- `CONFIG_INET_ESP`/`CBC`/`AES` + `CONFIG_XFRM_USER` all `=y`; SA privilege
  model works without `CONFIG_USER_NS` (Android IpSecManager API).
- KMI `android13-5.15` module flavor is bundled in the APK.
- All patch targets exist and are world-readable: `crash_dump64`,
  `/system/lib64/libc++.so` (hook symbol exported at `0x68cac`),
  `/vendor/lib64/libbinderdebug.so` (first ko-target candidate).
- Samsung DEFEX present in kallsyms; DirtyFrag 1.16 neutralises
  `task_defex_enforce`/`task_defex_user_exec` in RAM.
- RKP/KDP present; the fork targets Samsung hardening (its release notes and
  issue tracker are the reference if a run fails at module load).
- `CONFIG_MODULE_SIG=y` without `SIG_FORCE`; vendor `SIG_PROTECT` is a noted
  risk the run verdict resolves.

## Files staged

`downloads/` (gitignored):

- `DirtyFrag-v1.16.apk`, sha256 `fb0f8e25…de445d3`
- `KernelSU_samsung-v2.2_32687-release.apk`, sha256 `761dffad…290a69`
  (the Samsung-required manager that ships `libksud.so`)

## On-device sequence (each step reversible; stop on any failure)

1. **adb install** both APKs. If Samsung blocks USB install, enable
   "Install via USB" in Developer options on the phone (user action).
2. Open **KernelSU** (manager) once so it registers its `libksud.so`.
3. Open **DirtyFrag**, select the KernelSU manager in the SU Manager card.
4. **Run exploit.** The engine first patches the `crash_dump64` page cache and
   verifies it. That check prints `DEVICE NOT VULNERABLE` and aborts
   cleanly if the kernel is not exploitable. Nothing survives a reboot at
   any point.
5. On success, grant root to a shell and immediately verify state:
   `su -c id`, `getenforce`, `mount | grep -E "media|overlay"`.
6. **Reboot is the panic button at every step.** It returns the phone to a
   clean, unrooted One UI. Root is needed only for the OneLineage staging
   session and does not persist.

## After root: OneLineage staging

Use the patched scripts in `patches/onelineage/` (see that README). The
isolation overlay keeps the host `/data/media` untouched; the return script
restores rescue-party, audio props, socket modes, network rules, and (on the
fallback path) file permissions.

First guest boot is a staged test: watch `logcat` for PMS/PermissionController
crashes before granting anything, and do not run the takeover until the
guest's system_server reaches boot-completed without framework aborts.
