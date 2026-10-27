<img src="assets/icon.svg" width="64" height="64" alt="">

# Galaxy: OneLineage assessment

Running [OneLineage](https://github.com/WeWaffles/OneLineage) (a LineageOS
guest on the stock Samsung kernel) on a personal Galaxy S23 Ultra
(`SM-S918U`, One UI 6.1, kernel `5.15.123-android13-8`) without wiping it,
unlocking the bootloader, or flashing anything.

## What we achieved

- **Root, no-wipe, reversible.** `adb shell su` returns uid 0 in the `ksu`
  SELinux domain with the policy still Enforcing. Root comes from a locally
  rebuilt [DirtyFrag](https://github.com/mitschud/DirtyFrag) that fixes the
  Samsung-specific installer failure (SEPF has no `ksu_file` type): an
  `allow_shell` module flag, a same-length SELinux label substitution in the
  staged `ksud`, and a three-step daemon start. The exploit only writes page
  caches, so a reboot clears every trace. See
  [patches/dirtyfrag](patches/dirtyfrag/README.md) and
  [docs/ROOT-RUNBOOK.md](docs/ROOT-RUNBOOK.md).
- **The OneLineage compatibility checklist is closed** against this exact
  firmware with captured evidence: shared-storage/data-isolation risk,
  state-restoration gaps, APEX set, and the PermissionController concern are
  each resolved or measured. See
  [docs/ONELINEAGE-COMPAT-RISK.md](docs/ONELINEAGE-COMPAT-RISK.md).
- **A safe storage-isolation patch set for OneLineage.** The upstream
  takeover scripts `chown -R` and `chmod 777` the real shared-storage tree;
  our patched scripts mount it read-only-over-host via overlayfs
  (`CONFIG_OVERLAY_FS=y` verified), drop the host `/mnt` recursive bind, and
  restore rescue-party, audio properties, socket modes, network rules and
  file permissions on return. Written and reviewed, never executed:
  [patches/onelineage](patches/onelineage/README.md).
- **A verified, restorable backup of all 98,859 shared files (97.6 GB)**,
  taken before any of this, via ADB only (private app data excluded).

## What this lays the ground for

With root available on demand (and gone on reboot) and the isolation patches
ready, the next stage is the OneLineage takeover as a staged, watched test:
fetch the LineageOS GSI image, install the OneLineage app, stage the patched
scripts, boot the guest once under supervision, and verify that the return
path restores One UI and that the host's `/data/media` was never writable by
the guest. The runbook order and abort points are in the docs.

## Repository layout

- [docs/ASSESSMENT.md](docs/ASSESSMENT.md): device baseline, firmware
  analysis, root-path decision.
- [docs/ONELINEAGE-COMPAT-RISK.md](docs/ONELINEAGE-COMPAT-RISK.md): risk
  analysis with the closed checklist.
- [docs/ROOT-RUNBOOK.md](docs/ROOT-RUNBOOK.md): the working root sequence.
- [patches/onelineage/](patches/onelineage/): patched takeover scripts and
  a unified diff vs the pinned upstream source.
- [patches/dirtyfrag/](patches/dirtyfrag/): the Samsung root fix for
  DirtyFrag, with diff, build recipe and run evidence.
- `scripts/backup_shared_files.py`: the ADB shared-file backup script.

`work/` and `downloads/` (gitignored) hold the reproducible analysis inputs,
cloned upstream sources, the exact firmware image and the built APK. Nothing
private, no device identifiers and no credentials are part of this
repository.

## Credits

This builds on the work of these projects. All assessment, patches and
changes here are ours; upstream licenses apply to their code:

| Project | Used for |
|---|---|
| [WeWaffles/OneLineage](https://github.com/WeWaffles/OneLineage) | the LineageOS-takeover project being assessed (pinned `f5f5a7a`) |
| [mitschud/DirtyFrag](https://github.com/mitschud/DirtyFrag) | the hardened exploit engine we rebuilt for Samsung (v1.16, CVE-2026-43284) |
| [diabl0w/DFRoot](https://github.com/diabl0w/DFRoot) | upstream of DirtyFrag |
| [V4bel/dirtyfrag](https://github.com/V4bel/dirtyfrag) | original Dirty Frag research |
| [diabl0w/KernelSU](https://github.com/diabl0w/KernelSU) | Samsung KernelSU manager (`samsung-v2.2`, ships `libksud.so`) |
| [KernelSU-Next/KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) | alternative manager evaluated (module conflict on this kernel, do not use here) |
| [soumarcelino/Root-My-Galaxy-SM-S918B](https://github.com/soumarcelino/Root-My-Galaxy-SM-S918B) | community S23 Ultra root port; per-firmware payload reference |
| [BuSung-dev/Root-My-Galaxy-Payloads](https://github.com/BuSung-dev/Root-My-Galaxy-Payloads) | per-firmware payload target catalog |
| [YuKongA/ghostlock-app](https://github.com/YuKongA/ghostlock-app) | kernel-profile extractor used for the offline kernel analysis (pinned `413c86a`) |
| [samloader/samloader](https://github.com/samloader/samloader) | exact-firmware download from Samsung FUS |
| [topjohnwu/samloader-rs](https://github.com/topjohnwu/samloader-rs) | Rust samloader variant used for image extraction |
