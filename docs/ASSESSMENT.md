# SM-S918U / S918USQS2CXCN

## Owner's constraints

Preserve the personal phone and its existing data. The owner reported no
backup when this assessment opened; since then a complete, verified copy of
the ADB-accessible shared files exists (see "Backup boundary" below). Private
app data remains unprotected, which keeps the no-wipe constraint in force.
Work is restricted to offline analysis and read-only handset access.
Do not execute a root payload or a OneLineage takeover on the strength of this
assessment. Do not flash, unlock, repartition or factory-reset the phone.

## Live baseline

Verified over authorized USB ADB on 2026-10-26:

- Model: `SM-S918U`, device `dm3q`, product `dm3qsqw`.
- Android 14 / One UI 6.1, April 2024 security patch.
- Display: `UP1A.231005.007.S918USQS2CXCN`.
- Kernel: `5.15.123-android13-8-28577312-abS918USQS2CXCN`.
- Kernel build: `#1 SMP PREEMPT Wed Apr 3 07:38:39 UTC 2024`.
- CSC software: `S918UOYN2CXCN`; current sales code `DSG`; original carrier `VZW`.
- Bootloader locked, verified boot green, warranty bit 0.
- ADB runs as UID 2000 in the shell SELinux domain; no `su` found.
- About 23 GiB free on the data volume at inspection.

Raw baseline and copied kernel configuration: `work/device-evidence/`.
Reading `/sys/kernel/btf/vmlinux` and `/proc/kallsyms` is denied. No attempt was
made to bypass those restrictions during collection.

## Root investigation

The [upstream CVE record](https://kernel.googlesource.com/pub/scm/linux/security/vulns/+/56b9526616e328caac4d560e2700b4d8771517c6/cve/published/2026/CVE-2026-43499.mbox)
dates CVE-2026-43499 to Linux 2.6.39 and identifies 5.15.212 as the upstream
5.15-series fixed release. The running configuration enables `CONFIG_FUTEX_PI`.
This supported investigating the older kernel. The subsequent offline image
inspection below confirmed the unpatched primitive in this exact firmware;
a reliable root exploit remains unverified.

The [validated SM-S918U community root port](https://github.com/soumarcelino/Root-My-Galaxy-SM-S918B/releases/tag/S918USQS8FZF5)
targets Android 16 firmware `S918USQS8FZF5`, kernel 5.15.189, and an exact
fingerprint/kernel identity. Its offsets and KernelSU module cannot be treated
as compatible with the phone's current 5.15.123 firmware.

[GhostLock's extractor](https://github.com/YuKongA/ghostlock-app) can inspect an
offline boot image and generate a candidate profile. A generated profile is
explicitly not evidence of successful device support. Source pinned locally to
commit `413c86acbf0993703acf18ada53da84a1dbd572b`.

An exact current-firmware download was accepted by Samsung FUS:

```text
model: SM-S918U
region: VZW
version: S918USQS2CXCN/S918UOYN2CXCN/S918USQS2CXCN/S918USQS2CXCN
server file: SM-S918U_2_20240404070311_2jp07zxa9u_fac.zip.enc4
bytes: 10667060992
local output: downloads/SM-S918U-VZW-S918USQS2CXCN.zip
```

The PC-side download and image extraction completed. No image was flashed.
Extracted `boot.img` is 100663296 bytes, SHA-256
`128fcf1710d520c356ac0e4a7ef0efdafcdc72e9118cec97bb0a531dbc53256d`.
Its embedded kernel release matches the live handset exactly.

The source-built extractor recovered 119502 symbols and identifies
`remove_waiter@0x15c6944` as unpatched: it still uses `current`. The final analysis
uses the handset's explicit iomem dump and this firmware's bootloader images,
not the workstation's `/proc/iomem`. The UEFI map supplies a candidate kernel
physical load of `0xa8000000`. This is static evidence, not a runtime exploit.

The pselect stack derivation is ambiguous on this build. The tool suggests
the multicast route with medium confidence and emits an explicitly unverified
candidate profile containing unresolved fields. Do not deploy it or fill missing
offsets with guesses. The extractor's two `remove_waiter` regression checks pass.
Logs, provenance and candidate output are in `work/device-evidence/`.

### Selected root path: DirtyFrag (CVE-2026-43284)

After this assessment was written, the root path was re-planned around
**DirtyFrag v1.16**, which exploits the ESP page-cache write primitive
(disclosed May 2026, so this 2024-04 firmware cannot contain the fix), loads a
kernel module without unlocking the bootloader, and is **fully ephemeral**:
exactly the no-wipe recovery model this phone requires. Its bundled
`dfroot-android13-5.15.ko` matches this firmware's KMI, all patch targets are
present and world-readable on the handset, and Samsung DEFEX/RKP/KDP are
handled by the engine. The GhostLock futex profile above is demoted to a
documented fallback; the BOPE/Root-My-Galaxy port has no target for this
firmware. Gate-by-gate evidence: `work/device-evidence/dirtyfrag-gates.json`.
The on-device sequence and its abort points: `docs/ROOT-RUNBOOK.md`. Nothing
has been executed on the phone yet.

## OneLineage data handling

Source pinned locally to `f5f5a7a0999f806dfd618d4dd2a80bfda50b258d`.
The upstream demo is aimed at Android 16; Android 14 operation is unverified.

Observed in the supplied scripts:

- `master_prepare.sh` bind-mounts host `/data/media` into the guest and
  recursively binds host `/mnt` into the rootfs.
- `master_inner.sh` recursively changes ownership and permissions of
  `/data/media`, which therefore reaches the real shared-file tree.
- Preparation overlays host app-data trees so host services work against guest
  directories. That is a running-system change, not a fully isolated VM.
- The takeover sets `persist.sys.disable_rescue=true`; the return script does
  not restore that property.
- The return script restores host services and mounts, but static inspection
  cannot establish that recovery succeeds on this Android 14 phone.

An installation on this personal phone needs storage isolation and complete
state restoration to be reviewed and verified first. No modified scripts have
been run. Upstream also has an [open shared-storage report](https://github.com/WeWaffles/OneLineage/issues/9);
that report alone does not establish its cause or applicability to this model.

## Backup boundary

The accessible shared-file copy is complete and PC-side verified: 98,859
files, 97.6 GB under
`/home/arm/Backups/galaxy/2026-10-26-shared-files/`, with per-directory
counts and nine restore samples in `work/device-evidence/backup-verification.json`.
It is not an atomic snapshot and does not cover private app data, accounts
or device settings.

## Where the work stands

- **Root achieved (2026-10-27 15:05):** DirtyFrag run with a locally rebuilt
  APK. `adb shell su -c id` returns uid 0 in the `u:r:ksu:s0` domain,
  SELinux left Enforcing, write access verified. Ephemeral by design: a
  reboot clears everything. See `docs/ROOT-RUNBOOK.md` and
  `patches/dirtyfrag/` (the Samsung SEPF fix: allow_shell + staged-ksud
  label patch + permissive-ksu policy step).
- Data-isolation and state-restoration patches for OneLineage are written and
  reviewed but never executed: `patches/onelineage/` (overlayfs storage
  isolation, perms snapshot/restore, full return-path restoration).
- The risk checklist in `docs/ONELINEAGE-COMPAT-RISK.md` is fully closed
  against this firmware with captured evidence.
- Next step, on the owner's go-ahead: OneLineage staging under the fresh
  root: GSI image fetch, the OneLineage app, then the patched takeover
  scripts, with the first guest boot watched.
