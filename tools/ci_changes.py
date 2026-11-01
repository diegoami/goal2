"""[designed: owner, 2026-11-01, #493] Whether a PR push needs a workflow. --kind slow (the default): the
slow workflows (windows-slow.yml, linux-slow.yml) on the owner's machines, only when the push changes a file
the slow tests guard (check_premerge.py's SLOW_PATHS). --kind code: the hosted gates (ci.yml, windows.yml),
only when it changes a file outside docs/, measurements/ and Markdown.

    python3 tools/ci_changes.py [--kind slow|code] [--since SHA]

--since is the PR's previous head (the push's github.event.before): when it is an ancestor of HEAD, only
what changed since it counts, so a small follow-up commit does not start an hour of slow tests. Otherwise
(the PR's first push, its ready-for-review, a rewritten branch) everything the branch changes since its
merge base with origin/main counts. Prints the decision; with GITHUB_OUTPUT set, appends run=true|false.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_premerge import SLOW_PATHS  # noqa: E402

DOCS = re.compile(r"^(docs/|measurements/)|\.md$")
KINDS = {"slow": SLOW_PATHS.match, "code": lambda f: not DOCS.search(f)}
WHAT = {"slow": "the slow tests guard", "code": "the tests check (beyond docs, measurements, Markdown)"}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def decide(since: str | None = None, cwd: Path = ROOT, base: str = "origin/main", kind: str = "slow") -> tuple[bool, str]:
    """(run, why): run when a file of `kind` changed since `since`, or since the merge base with `base`
    when `since` is absent or not an ancestor of HEAD; run when git cannot tell."""
    if since and since.strip("0") and _git(cwd, "merge-base", "--is-ancestor", since, "HEAD").returncode == 0:
        diff, scope = _git(cwd, "diff", "--name-only", since, "HEAD"), f"since the previous push {since[:8]}"
    else:
        diff, scope = _git(cwd, "diff", "--name-only", f"{base}...HEAD"), f"since the merge base with {base}"
    if diff.returncode != 0:
        return True, f"git could not compare ({scope}): running to be safe"
    changed = [f for f in diff.stdout.split() if KINDS[kind](f)]
    if changed:
        return True, f"changed {scope}: {', '.join(changed[:5])}{' ...' if len(changed) > 5 else ''}"
    return False, f"nothing {WHAT[kind]} changed {scope}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", choices=sorted(KINDS), default="slow")
    parser.add_argument("--since", help="the PR's previous head (github.event.before)")
    args = parser.parse_args(argv)
    run, why = decide(args.since, kind=args.kind)
    print(f"{'RUN' if run else 'SKIP'} the {args.kind} workflows: {why}", flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"run={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
