#!/usr/bin/env bash
# [designed: owner, 2026-10-20] Start a milestone review with a reviewer CLI directly, outside the
# harness (docs/milestone-review.md). Usage:
#   tools/milestone_review.sh <issue> <opencode|claude|codex> <model> [--print]
# --print shows the command instead of running it.
set -euo pipefail
issue=${1:?usage: tools/milestone_review.sh <issue> <opencode|claude|codex> <model> [--print]}
cli=${2:?give the CLI: opencode, claude or codex}
model=${3:?give the model, e.g. openai/gpt-6.1-sol#low, opus or gpt-6.1-sol}
print=${4:-}
top=$(git rev-parse --show-toplevel)
cd "$top"

body=$(gh issue view "$issue" --json body -q .body)
candidate=$(grep -oE '\*\*Candidate\*\*: *`[0-9a-f]{40}`' <<<"$body" | grep -oE '[0-9a-f]{40}' || true)
[ -n "$candidate" ] || { echo "Issue #$issue has no '**Candidate**: \`<full sha>\`' line." >&2; exit 2; }

git fetch -q origin main --tags
git cat-file -e "$candidate^{commit}" || { echo "Candidate $candidate is not on origin." >&2; exit 2; }
# The reviewer's instructions come from origin/main, never from a branch under review.
agent=$(git show origin/main:.opencode/agents/milestone-reviewer.md)
if [ "$(git rev-parse HEAD)" != "$candidate" ]; then
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "This checkout has uncommitted tracked changes; commit them first." >&2; exit 2
  fi
  git checkout -q --detach "$candidate"
fi
echo "reviewing milestone issue #$issue at $candidate with $cli ($model)"

instructions=${agent#---*---}
prompt="Review the goal2 milestone on issue #$issue. Start with: gh issue view $issue.
Your instructions follow (from .opencode/agents/milestone-reviewer.md on origin/main).
${instructions}"

case "$cli" in
  opencode) cmd=(opencode run --agent milestone-reviewer -m "$model" --title "milestone-$issue" "Review the goal2 milestone on issue #$issue, as your instructions say. Start with: gh issue view $issue.") ;;
  claude)   cmd=(claude -p --model "$model" --allowedTools Bash Read Grep Glob --disallowedTools Edit Write NotebookEdit -- "$prompt") ;;
  codex)    cmd=(codex exec -m "$model" -s workspace-write -c sandbox_workspace_write.network_access=true "$prompt") ;;
  *) echo "Unknown CLI $cli: use opencode, claude or codex." >&2; exit 2 ;;
esac
if [ "$print" = "--print" ]; then printf '%q ' "${cmd[@]}"; echo; exit 0; fi
"${cmd[@]}" </dev/null
