#!/usr/bin/env python3
"""Copy accessible shared files; this is not an Android app-data backup."""

import argparse
from datetime import datetime, timezone
import json
import fcntl
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    adb = ["adb", "-s", args.serial]
    model = subprocess.check_output(
        adb + ["shell", "getprop", "ro.product.model"], text=True
    ).strip()
    if model != "SM-S918U":
        raise SystemExit(f"Unexpected phone model: {model!r}")
    dest = args.destination.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest.chmod(0o700)
    lock = (dest / ".backup.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("A backup is already running for this destination.")
    report_path = dest / "backup-report.json"
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "firmware": subprocess.check_output(
            adb + ["shell", "getprop", "ro.build.display.id"], text=True
        ).strip(),
        "limitations": [
            "Shared files only; excludes private app data, accounts and device settings.",
            "Live copy, not an atomic snapshot; open files may change during copying.",
            "Exit status reports transfer completion, not a tested phone restore.",
        ],
        "directories": {},
    }
    if args.resume and report_path.exists():
        previous = json.loads(report_path.read_text())
        if any(previous.get(key) != report[key] for key in ("model", "firmware")):
            raise SystemExit("Existing backup belongs to a different model or firmware.")
        report = previous
        report.pop("finished_at", None)
        report.setdefault("resumed_at", []).append(datetime.now(timezone.utc).isoformat())
    directories = [
        "Documents", "Pictures", "Recordings", "Download", "DCIM",
        "Android/media", "Movies", "Music", "Audiobooks", "Podcasts",
        "Alarms", "Notifications", "Ringtones", "LOCALSEND",
    ]
    def save():
        tmp = report_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(report, indent=2) + "\n")
        tmp.replace(report_path)
    save()
    for name in directories:
        remote = "/sdcard/" + name
        target = dest / "shared-files" / name
        previous = report["directories"].get(name, {})
        if args.resume and previous.get("status") == "copied" and target.is_dir():
            files = [p for p in target.rglob("*") if p.is_file()]
            if (len(files) == previous.get("local_file_count") and
                    sum(p.stat().st_size for p in files) == previous.get("local_bytes")):
                print(f"{name}: retaining completed copy", flush=True)
                continue
        exists = subprocess.run(
            adb + ["shell", f"test -d '{remote}'"], capture_output=True
        ).returncode == 0
        if not exists:
            report["directories"][name] = {"status": "absent-or-inaccessible"}
            save()
            continue
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        log = dest / ("transfer-" + name.replace("/", "-") + ".log")
        print(f"Copying {name}...", flush=True)
        report["directories"][name] = {"status": "copying", "log": log.name}
        save()
        with log.open("ab") as output:
            result = subprocess.run(
                adb + ["pull", "-a", remote + "/.", str(target)],
                stdout=output, stderr=subprocess.STDOUT,
            )
        files = [p for p in target.rglob("*") if p.is_file()]
        report["directories"][name] = {
            "status": "copied" if result.returncode == 0 else "incomplete",
            "exit_code": result.returncode,
            "local_file_count": len(files),
            "local_bytes": sum(p.stat().st_size for p in files),
            "log": log.name,
        }
        save()
        print(f"{name}: {report['directories'][name]['status']}", flush=True)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    failed = any(x["status"] == "incomplete" for x in report["directories"].values())
    print(f"Shared-file copy finished. Report: {report_path}", flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
