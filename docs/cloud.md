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
- Optional, for reviews by other model families from the cloud: the API keys of the CLI that
  `tools/review_pr.sh` or `tools/milestone_review.sh` calls. Without them, the owner runs those
  reviews locally.

## What happens at session start

The session-start hook (`.claude/hooks/session-start.sh`, cloud sessions only) runs
`tools/cloud_setup.sh`: offscreen Qt libraries, a virtualenv in `.cache/venv` with
`goal2[desktop,watched,match-view]`, rclone and `gh` if missing, the Drive remote, the original-game
files pulled into `.cache/` and `GOAL.DAT` verified. It puts `.cache/cloud.env` (the venv on PATH,
`QT_QPA_PLATFORM=offscreen`, SDL's dummy drivers) into the session's environment and reports the
branch, gh's login and the Drive remote. Its log is `.cache/cloud-setup.log`. Elsewhere, run
`tools/cloud_setup.sh` and `source .cache/cloud.env` by hand.

## Branches

The session starts on its own `claude/…` branch, the work branch for every task of the session;
PRs merge with a merge commit, never squash (process.md §3).

## Limits

Qt runs offscreen and SDL with dummy drivers: screenshots work, nothing is shown. Native Windows,
2× scaling and accessibility gates, and the owner's playtest, stay local. A clone made by hand can
be shallow (`git clone --depth 1`, about 20 MB instead of the 157 MiB history).
