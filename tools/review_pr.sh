#!/usr/bin/env bash
# [designed: owner, 2026-10-20] An optional review of one PR by a reviewer CLI, called directly
# (CLAUDE.md rule 4). Any model may review. Usage:
#   tools/review_pr.sh <pr> <opencode|claude|codex> <model> [--print]
# Checks the PR out (refuses with uncommitted tracked changes) and runs the CLI with
# .opencode/agents/reviewer.md's instructions from origin/main; the reviewer posts its own review as
# one PR comment (2026-10-22: the old harness posted for it, which blocked reviewers run by hand).
# The output is kept under .cache/reviews/. --print shows the command instead of running it.
set -euo pipefail
pr=${1:?usage: tools/review_pr.sh <pr> <opencode|claude|codex> <model> [--print]}
cli=${2:?give the CLI: opencode, claude or codex}
model=${3:?give the model, e.g. openai/gpt-5.6-luna#high, opus or gpt-6.1-sol}
print=${4:-}
cd "$(git rev-parse --show-toplevel)"

git fetch -q origin main
agent=$(git show origin/main:.opencode/agents/reviewer.md)
instructions=${agent#---*---}
head=$(gh pr view "$pr" --json headRefOid -q .headRefOid)
issue=$(gh pr view "$pr" --json body -q .body | grep -oiE '(closes|fixes) #[0-9]+' | head -1 | grep -oE '[0-9]+' || true)
prompt="Review pull request #$pr at $head${issue:+ (it closes issue #$issue: read it with gh issue view $issue)}.
Your instructions follow (from .opencode/agents/reviewer.md on origin/main).
${instructions}"

case "$cli" in
  opencode) cmd=(opencode run --agent reviewer -m "$model" --title "review-pr$pr" "$prompt") ;;
  claude)   cmd=(claude -p --model "$model" --allowedTools Bash Read Grep Glob --disallowedTools Edit Write NotebookEdit -- "$prompt") ;;
  codex)    cmd=(codex exec -m "$model" -s workspace-write -c sandbox_workspace_write.network_access=true "$prompt") ;;
  *) echo "Unknown CLI $cli: use opencode, claude or codex." >&2; exit 2 ;;
esac
if [ "$print" = "--print" ]; then printf '%q ' "${cmd[@]}"; echo; exit 0; fi

if [ "$(git rev-parse HEAD)" != "$head" ]; then
  [ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "Uncommitted tracked changes; commit them first." >&2; exit 2; }
  git fetch -q origin "pull/$pr/head" && git checkout -q --detach "$head"
fi
mkdir -p .cache/reviews
out=".cache/reviews/pr$pr-$(date -u +%Y%m%dT%H%M%SZ).md"
echo "reviewing PR #$pr at $head with $cli ($model); output in $out"
"${cmd[@]}" </dev/null | tee "$out"
[ -s "$out" ] || { echo "No review came back." >&2; exit 3; }
echo "The reviewer posts its review on PR #$pr itself; its output is in $out."
