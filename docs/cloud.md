# Working in a cloud session

[designed: owner, 2026-10-20] goal2 runs from any fresh checkout. In a cloud session:

1. Secrets the session needs:
   - `GOAL2_RCLONE_TOKEN`: the `token = {...}` value of the `goal2drive` remote in a configured
     machine's `~/.config/rclone/rclone.conf` (the original-game files, [artifacts.md](artifacts.md)).
   - `GH_TOKEN`: a GitHub token with push and merge rights on `diegoami/goal2`.
   - Optional, for reviews by other model families from the cloud: the API keys of the CLI that
     `tools/review_pr.sh` or `tools/milestone_review.sh` calls. Without them, the owner runs
     those reviews locally.
2. `tools/cloud_setup.sh`, then `source .cache/cloud.env`. It installs the system libraries for
   offscreen Qt (as root), a virtualenv in `.cache/venv` with `goal2[desktop,watched,match-view]`,
   rclone (pinned, checksum verified), the Drive remote, and pulls the original-game files into
   `.cache/`.
3. Work as `CLAUDE.md` and [process.md](process.md) say. Qt runs offscreen and SDL with the dummy
   driver, so screenshots work but nothing is shown; the owner's playtest and Windows-native
   checks stay local.

What the cloud cannot do: native Windows, 2× scaling or accessibility gates; the owner's playtest.
