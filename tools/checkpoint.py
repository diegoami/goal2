"""[designed: owner, 2026-10-29, T149] A live snapshot of the work, to stop and resume from.

    python3 tools/checkpoint.py [--checkout DIR ...]
    python3 tools/checkpoint.py --post "<next action>" [--notes FILE] [--checkout DIR ...]

The snapshot lists each checkout (this one, every `--checkout`, and the directories in
`GOAL2_CHECKOUTS`, separated by the path separator): its repository, branch, head and how many
tracked files are changed or files untracked (names are not read). Then each repository's open
PRs with head, draft state, labels and checks, and the jobs registered with tools/jobs.py in
each checkout. A GitHub call that fails is reported as failed, never left out.

`--post` adds the next action (and the notes file, if any) and posts the whole as a comment on
the open issue labelled `checkpoint` in this checkout's repository; it refuses when there is not
exactly one. Resuming starts from that issue's latest comment and a fresh snapshot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import jobs as job_registry  # noqa: E402

LABEL = "checkpoint"


class CheckpointError(ValueError):
    """The snapshot cannot be posted."""


def sh(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def repository(url: str) -> str | None:
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url.strip())
    return m.group(1) if m else None


def checkout(path: Path, run=sh) -> dict:
    code, top, err = run(["git", "rev-parse", "--show-toplevel"], path)
    if code:
        return dict(path=str(path), error=(err.strip().splitlines() or ["not a git checkout"])[0])
    path = Path(top.strip())
    found = dict(path=str(path))
    _, url, _ = run(["git", "remote", "get-url", "origin"], path)
    found["repo"] = repository(url)
    _, branch, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)
    _, sha, _ = run(["git", "rev-parse", "HEAD"], path)
    _, status, _ = run(["git", "status", "--porcelain"], path)
    lines = status.splitlines()
    found.update(branch=branch.strip(), head=sha.strip(),
                 changed=sum(1 for l in lines if not l.startswith("??")),
                 untracked=sum(1 for l in lines if l.startswith("??")))
    _, ahead, _ = run(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"], path)
    if re.fullmatch(r"\d+\s+\d+", ahead.strip()):
        behind, ahead_n = ahead.split();found.update(behind=int(behind), ahead=int(ahead_n))
    found["jobs"] = job_registry.jobs(path)
    return found


def checks(rollup: list[dict]) -> str:
    if not rollup:
        return "no checks"
    states = {}
    for c in rollup:
        state = (c.get("conclusion") or c.get("status") or c.get("state") or "?").lower()
        states.setdefault(state, []).append(c.get("name") or c.get("context") or "?")
    order = sorted(states, key=lambda s: (s != "failure", s))
    return "; ".join(f"{s} {len(states[s])}" + (f" ({', '.join(states[s])})" if s not in ("success", "skipped") else "")
                     for s in order)


def pulls(repo: str, run=sh) -> dict:
    code, out, err = run(["gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "50", "--json",
                          "number,title,headRefName,headRefOid,isDraft,labels,statusCheckRollup"])
    if code:
        return dict(repo=repo, error=(err.strip().splitlines() or [f"gh exit {code}"])[0])
    return dict(repo=repo, prs=json.loads(out or "[]"))


def snapshot(paths: list[Path], run=sh) -> str:
    lines = [f"Snapshot {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "", "Checkouts:"]
    found = [checkout(p, run) for p in paths]
    repos = []
    for c in found:
        if "error" in c:
            lines.append(f"- {c['path']}: FAILED ({c['error']})");continue
        drift = f", {c['ahead']} ahead/{c['behind']} behind upstream" if "ahead" in c else ""
        lines.append(f"- {c['path']} ({c['repo']}): {c['branch']} at {c['head'][:12]}, "
                     f"{c['changed']} changed, {c['untracked']} untracked{drift}")
        for j in c["jobs"]:
            lines.append(f"  - job {job_registry.describe(j)}")
        if c["repo"] and c["repo"] not in repos:
            repos.append(c["repo"])
    for repo in repos:
        lines += ["", f"Open PRs in {repo}:"]
        result = pulls(repo, run)
        if "error" in result:
            lines.append(f"- FAILED to read PRs ({result['error']})");continue
        if not result["prs"]:
            lines.append("- none")
        for pr in sorted(result["prs"], key=lambda p: p["number"]):
            labels = ", ".join(l["name"] for l in pr.get("labels", [])) or "no labels"
            lines.append(f"- #{pr['number']} {pr['title']} ({pr['headRefName']} at {pr['headRefOid'][:12]}"
                         f"{', draft' if pr.get('isDraft') else ''}; {labels}): {checks(pr.get('statusCheckRollup') or [])}")
    return "\n".join(lines)


def post(repo: str, body: str, run=sh) -> str:
    code, out, err = run(["gh", "issue", "list", "--repo", repo, "--label", LABEL, "--state", "open",
                          "--json", "number"])
    if code:
        raise CheckpointError(f"could not list {LABEL} issues: {(err.strip().splitlines() or [''])[0]}")
    issues = json.loads(out or "[]")
    if len(issues) != 1:
        raise CheckpointError(f"{len(issues)} open issues labelled {LABEL} in {repo}; need exactly one")
    number = issues[0]["number"]
    code, out, err = run(["gh", "issue", "comment", str(number), "--repo", repo, "--body", body])
    if code:
        raise CheckpointError(f"could not comment on #{number}: {(err.strip().splitlines() or [''])[0]}")
    return out.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkout", type=Path, action="append", default=[])
    parser.add_argument("--post", metavar="NEXT", help="post the snapshot with this next action")
    parser.add_argument("--notes", type=Path, help="a Markdown file posted with the snapshot")
    args = parser.parse_args(argv)
    paths = [ROOT] + [Path(p) for p in os.environ.get("GOAL2_CHECKOUTS", "").split(os.pathsep) if p] + args.checkout
    unique = []
    for p in paths:
        if p.resolve() not in unique:
            unique.append(p.resolve())
    text = snapshot(unique)
    if args.post is None:
        print(text);return 0
    notes = args.notes.read_text().strip() + "\n\n" if args.notes else ""
    body = f"## Checkpoint\n\n**Next:** {args.post}\n\n{notes}```text\n{text}\n```\n"
    repo = checkout(ROOT).get("repo")
    try:
        if not repo:
            raise CheckpointError("this checkout has no GitHub origin")
        print(post(repo, body))
    except CheckpointError as error:
        print(text);print(f"checkpoint.py: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
