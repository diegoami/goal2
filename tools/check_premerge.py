"""[designed: owner, #127] Offline checks of the exact reviewed, clean commit.

Task-specific tests and independent review remain separate merge requirements.
This command preserves every check previously run by the hosted CI workflow.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys


class ValidationError(ValueError):
    """A mandatory validation failed."""


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout


def check_checkout(root: Path, expected_head: str) -> None:
    # [designed: #127] A prefix is insufficient to identify the reviewed commit.
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValidationError("expected HEAD must be a full lowercase 40-character commit SHA")
    actual = git(root, "rev-parse", "HEAD").strip()
    if actual != expected_head:
        raise ValidationError(f"HEAD mismatch: expected {expected_head}, got {actual}")
    if git(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValidationError("tracked checkout is dirty; commit changes before validating")


def check_lock(root: Path) -> None:
    count = 0
    for line in (root / "harness.lock").read_text().splitlines():
        if not line or line.startswith(("#", "source ", "copied ", "adapt ", "local ")):
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValidationError(f"malformed harness.lock entry: {line}")
        digest, name = match.groups()
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValidationError(f"invalid locked path: {name}")
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValidationError(f"harness.lock hash mismatch: {name}")
        count += 1
    if not count:
        raise ValidationError("harness.lock has no SHA256 entries")
    print(f"PASS harness.lock: {count} hashes", flush=True)


def check_originals(root: Path) -> None:
    # [designed: #127; rule19] Include rebuild session files as well as DOS assets.
    forbidden = {".exe", ".dat", ".hlp", ".hil", ".pif", ".bat", ".sav", ".gl", ".g2save"}
    files = git(root, "ls-files", "-z").split("\0")
    bad = [name for name in files if Path(name).suffix.lower() in forbidden]
    if bad:
        raise ValidationError("tracked original/session assets: " + ", ".join(bad))
    print("PASS original-asset exclusion", flush=True)


def validate(root: Path, expected_head: str) -> None:
    check_checkout(root, expected_head)
    check_lock(root)
    check_originals(root)
    commands = (
        (sys.executable, "tools/check_links.py"),
        ("node", "tools/harness/review.mjs", "--self-test"),
        ("node", "--test", "tests/harness_clients.test.mjs"),
        ("node", "--test", "tests/opencode_protocol.test.mjs"),
        (sys.executable, "-m", "unittest", "tests.test_agent_permissions",
         "tests.test_merge_workflow", "tests.test_local_validation", "-v"),
    )
    for command in commands:
        print("RUN " + " ".join(command), flush=True)
        subprocess.run(command, cwd=root, check=True)
    # [designed: #127] A check that changes tracked inputs cannot certify this SHA.
    check_checkout(root, expected_head)
    check_lock(root)
    check_originals(root)
    print(f"PASS local pre-merge validation at {expected_head}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True,
                        help="full reviewed commit SHA (not a branch or abbreviated SHA)")
    args = parser.parse_args(argv)
    try:
        validate(Path(__file__).resolve().parents[1], args.expected_head)
    except (ValidationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL local pre-merge validation: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
