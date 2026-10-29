# Working in a cloud session

[designed: owner, 2026-10-20] goal2 runs from any fresh checkout, a Claude Code on the web
session included.

## Secrets of the cloud environment

- `GH_TOKEN`: a fine-grained GitHub token for `diegoami/goal2` with read and write access to
  contents, issues and pull requests. Without it `gh` cannot read labels or open and merge PRs,
  and autonomous work stops at the first PR.
- `GOAL2_RCLONE_TOKEN`: the `token = {...}` value of the `goal2drive` remote in a configured
  machine's `~/.config/rclone/rclone.conf` (the original-game files, [artifacts.md](artifacts.md)).
  With the owner's own Google OAuth client (rclone's shared one is being retired during 2026), also
  `RCLONE_DRIVE_CLIENT_ID` and `RCLONE_DRIVE_CLIENT_SECRET`.
- No keys are needed for reviews: no session starts one; the owner runs each review from the prompt
  the main session gives (CLAUDE.md rule 4).

## What happens at session start

The session-start hook (`.claude/hooks/session-start.sh`, cloud sessions only) runs
`tools/cloud_setup.sh`: offscreen Qt libraries, a virtualenv in `.cache/venv` with
`goal2[desktop,watched,match-view]`, rclone and `gh` if missing, the Drive remote, the original-game
files pulled into `.cache/` and `GOAL.DAT` verified, and a full clone of the public
goal2-archaeology in `.cache/goal2-archaeology` (its run records feed the fidelity tests;
`GOAL2_ARCHAEOLOGY` points the tests and `tools/check_provenance.py` at it). It puts `.cache/cloud.env` (the venv on PATH,
`QT_QPA_PLATFORM=offscreen`, SDL's dummy drivers) into the session's environment and reports the
branch, gh's login and the Drive remote. Its log is `.cache/cloud-setup.log`. Elsewhere, run
`tools/cloud_setup.sh` and `source .cache/cloud.env` by hand.

## GitHub from a cloud session

[designed: owner, 2026-10-21, after the first goal2-archaeology cloud run] The session's proxy lets
only GitHub's REST API through: `gh`'s GraphQL commands (`gh pr create`, `gh pr merge`, `gh pr view`,
`gh issue list`, `gh release download`, `gh auth status`) fail with 403. Use the session's built-in
GitHub tools, or `gh api` (REST), for example:

- merge with the merge commit process.md §3 asks for, pinned to the checked head:
  `gh api -X PUT repos/diegoami/goal2/pulls/<n>/merge -f merge_method=merge -f sha=<head sha>`
  (goal2 squashes only locally; a cloud session always merges like this);
- open a PR: `gh api repos/diegoami/goal2/pulls -f title=... -f head=<branch> -f base=main -F draft=true -f body=@<file>`;
- the login check: `gh api user --jq .login`.

Release assets come over plain HTTPS from the public release (the setup falls back to it); their
downloads redirect to `release-assets.githubusercontent.com`, which the network settings must allow.

## Branches

The session starts on its own `claude/…` branch, the work branch for every task of the session;
PRs merge with a merge commit, never squash (process.md §3).

## Limits

Qt runs offscreen and SDL with dummy drivers: screenshots work, nothing is shown. Native Windows
is covered by the Windows workflow on every PR (#278; `docs/process.md` §3): the game tests, the
`spawn` worker, saves, and the Qt/SDL scenarios with the real Windows platforms. What stays with the
owner, at milestones: true 2× scaling, accessibility gates and the playtest. A clone made by hand can
be shallow (`git clone --depth 1`, about 20 MB instead of the 157 MiB history).
