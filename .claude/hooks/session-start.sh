#!/bin/bash
# [designed: owner, 2026-10-20] SessionStart, Claude Code on the web only: run tools/cloud_setup.sh
# and report the branch and gh's login (docs/cloud.md). It never fails the session.
set -uo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
log=.cache/cloud-setup.log
mkdir -p .cache
if tools/cloud_setup.sh >"$log" 2>&1; then echo "Setup: done."; else echo "Setup: failed; see $log."; fi
# Every later Bash call of the session gets the venv, offscreen Qt and dummy SDL.
[ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f .cache/cloud.env ] && grep '^export' .cache/cloud.env >>"$CLAUDE_ENV_FILE"
if gh api user --jq .login >/dev/null 2>&1; then gh_login="logged in"; else gh_login="NOT logged in: add a GH_TOKEN secret (docs/cloud.md)"; fi
echo "Branch: $(git branch --show-current 2>/dev/null): the work branch for every task of this session; PRs merge with --merge (docs/process.md §3). gh: $gh_login."
echo "Drive remote: $(rclone listremotes 2>/dev/null | grep -qx goal2drive: && echo configured || echo 'missing (GOAL2_RCLONE_TOKEN)'). Reviews are optional; milestones get one (CLAUDE.md rule 4)."
exit 0
