#!/usr/bin/env python3
"""Create and verify write-once experiment receipts. Standard library only.

Usage:
  make_receipt.py create --experiment-id ID --command "python run.py ..." --out receipts/ID.json \
      [--status COMPLETED|PARTIAL|FAILED|PENDING_RUN] [--metrics metrics.json] \
      [--config cfg.yaml ...] [--data data.csv ...] [--seed 0 --seed 1 ...] \
      [--plan plan.md] [--packages numpy,torch] [--failure-reason "OOM at step 300"] [--notes "..."]
  make_receipt.py verify receipts/ID.json

Design notes
- Metrics are never typed by hand: they are read from a JSON file the experiment itself wrote.
- The receipt is written with exclusive-create mode, so an existing receipt is never overwritten.
- receipt_sha256 covers the whole receipt; `verify` detects edits and changed input files.
  This is tamper-evident, not tamper-proof: keep receipts in version control too.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib import metadata as md

SCHEMA_VERSION = "1.0"
STATUSES = ["PENDING_RUN", "COMPLETED", "PARTIAL", "FAILED"]
DEFAULT_PACKAGES = ["numpy", "scipy", "pandas", "torch", "transformers", "jax", "scikit-learn"]


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        # Rationale: File may be unreadable, non-existent, or locked; return None hash.
        return None
    return h.hexdigest()


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        # Rationale: Command may not exist on system (e.g. nvidia-smi or git); return None output.
        return None


def git_info():
    commit = run(["git", "rev-parse", "HEAD"])
    if commit is None:
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(run(["git", "status", "--porcelain"]))}


def gpu_info():
    out = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
               "--format=csv,noheader,nounits"])
    gpus = []
    for line in (out or "").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3:
            try:
                mem = float(parts[1])
            except ValueError:
                # Rationale: GPU memory string may not be a valid float; record None.
                mem = None
            gpus.append({"name": parts[0], "memory_total_mib": mem, "driver_version": parts[2]})
    return gpus


def package_versions(names):
    versions = {}
    for name in names:
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            # Rationale: Optional package may not be installed in the current environment.
            versions[name] = None
    return versions


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def receipt_hash(receipt):
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


def cmd_create(args):
    if args.status in ("FAILED", "PARTIAL") and not args.failure_reason:
        sys.exit("error: --failure-reason is required when status is FAILED or PARTIAL")
    if args.status in ("COMPLETED", "PARTIAL") and not args.metrics:
        sys.exit("error: --metrics FILE is required for COMPLETED/PARTIAL runs "
                 "(metrics must come from a file the experiment wrote, not typed by hand)")

    metrics, metrics_hash = None, None
    if args.metrics:
        try:
            with open(args.metrics, encoding="utf-8") as f:
                metrics = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            sys.exit(f"error: cannot read metrics file: {e}")
        metrics_hash = sha256_file(args.metrics)
        if not isinstance(metrics, dict):
            sys.exit("error: metrics file must contain a JSON object of metric_name -> details")
        for name, m in metrics.items():
            if not isinstance(m, dict) or "n" not in m:
                warn(f"metric '{name}' has no sample size 'n'; report n (examples) and/or n_seeds")
            elif "std" not in m and "ci95" not in m and m.get("n", 0) > 1 and "n_seeds" not in m:
                warn(f"metric '{name}' has no spread (std or ci95); a point estimate alone is weak evidence")
    if not args.seed:
        warn("no --seed given; record seeds, or state in --notes that the run has no randomness")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": args.experiment_id,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": args.status,
        "failure_reason": args.failure_reason,
        "plan_ref": args.plan,
        "command": args.command,
        "notes": args.notes,
        "git": git_info(),
        "seeds": args.seed or [],
        "inputs": {
            "configs": {p: sha256_file(p) for p in args.config or []},
            "data": {p: sha256_file(p) for p in args.data or []},
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": package_versions(
                [p.strip() for p in args.packages.split(",")] if args.packages else DEFAULT_PACKAGES),
            "gpus": gpu_info(),
        },
        "results": {
            "metrics_file": args.metrics,
            "metrics_file_sha256": metrics_hash,
            "metrics": metrics,
        },
    }
    for group in ("configs", "data"):
        for path, digest in receipt["inputs"][group].items():
            if digest is None:
                warn(f"input file not readable, hash recorded as null: {path}")
    if receipt["git"]["dirty"]:
        warn("git working tree has uncommitted changes; the commit hash does not fully identify the code")
    receipt["receipt_sha256"] = receipt_hash(receipt)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    try:
        with open(args.out, "x", encoding="utf-8") as f:  # 'x': never overwrite
            json.dump(receipt, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    except FileExistsError:
        sys.exit(f"error: {args.out} already exists; receipts are write-once. Use a new filename for a rerun.")
    print(f"wrote {args.out}  (receipt_sha256={receipt['receipt_sha256'][:16]}...)")


def cmd_verify(args):
    try:
        with open(args.receipt, encoding="utf-8") as f:
            receipt = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"error: cannot read receipt: {e}")

    problems = []
    if receipt.get("receipt_sha256") != receipt_hash(receipt):
        problems.append("receipt_sha256 mismatch: the receipt was modified after creation")

    for group in ("configs", "data"):
        for path, expected in receipt.get("inputs", {}).get(group, {}).items():
            actual = sha256_file(path)
            if actual is None:
                problems.append(f"{group} file not found (cannot check): {path}")
            elif expected is None:
                problems.append(f"{group} file had no recorded hash: {path}")
            elif actual != expected:
                problems.append(f"{group} file changed since the run: {path}")

    res = receipt.get("results", {})
    mf = res.get("metrics_file")
    if mf and res.get("metrics_file_sha256"):
        actual = sha256_file(mf)
        if actual is None:
            problems.append(f"metrics file not found (cannot check): {mf}")
        elif actual != res["metrics_file_sha256"]:
            problems.append(f"metrics file changed since the run: {mf}")

    if receipt.get("status") == "COMPLETED" and not res.get("metrics"):
        problems.append("status is COMPLETED but no metrics are recorded")
    if receipt.get("git", {}).get("dirty"):
        problems.append("note: run was made with uncommitted code changes")

    if problems:
        print("VERIFY: issues found")
        for p in problems:
            print(f"  - {p}")
        hard = [p for p in problems if not p.startswith("note:")]
        sys.exit(1 if hard else 0)
    print("VERIFY: OK (self-hash and input hashes match)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="write a new receipt")
    c.add_argument("--experiment-id", required=True)
    c.add_argument("--command", required=True, help="exact command that produced the run")
    c.add_argument("--out", required=True)
    c.add_argument("--status", choices=STATUSES, default="COMPLETED")
    c.add_argument("--metrics", help="JSON file written by the experiment: {name: {value, n, std|ci95, ...}}")
    c.add_argument("--config", action="append", help="config file to hash (repeatable)")
    c.add_argument("--data", action="append", help="data/checkpoint file to hash (repeatable)")
    c.add_argument("--seed", action="append", type=int, help="RNG seed used (repeatable)")
    c.add_argument("--plan", help="path/id of the pre-registration")
    c.add_argument("--packages", help="comma-separated package names to record (default: common scientific/ML set)")
    c.add_argument("--failure-reason")
    c.add_argument("--notes")
    c.set_defaults(func=cmd_create)

    v = sub.add_parser("verify", help="check a receipt's self-hash and input hashes")
    v.add_argument("receipt")
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
