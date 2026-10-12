#!/usr/bin/env bash
# What an OpenCode run is doing now: its latest steps, read-only from the harness's data directory.
#
#   tools/harness/peek.sh ses_XXXX [-n 20]
#   tools/harness/peek.sh <run log> [-n 20]     (the log's "session ses_… started" line names it)
#
# Prints the newest N steps: each tool call with its status (running, completed, error) and the
# start of its input, and the start of each message the model wrote. It reads the session through
# `opencode export` with the harness's XDG directories (review.mjs runs there),
# never auth.json. Works while the run is going and after it ends.
set -eu
target=${1:?usage: peek.sh ses_XXXX|<run log> [-n N]}; shift
n=20
[ "${1:-}" = -n ] && n=$2
sid=$target
if [ -f "$target" ]; then
  sid=$(grep -o 'session ses_[A-Za-z0-9]* started' "$target" | tail -1 | cut -d' ' -f2)
  [ -n "$sid" ] || sid=$(grep -o '"sessionID":"ses_[A-Za-z0-9]*"' "$target" | head -1 | cut -d'"' -f4)
  [ -n "$sid" ] || { echo "peek.sh: no session id in $target yet" >&2; exit 1; }
fi
case "$sid" in ses_*) ;; *) echo "peek.sh: not a session id or a run log: $target" >&2; exit 2 ;; esac
H=${HARNESS_OPENCODE_HOME:-$HOME/.local/share/harness-opencode}
# The harness's own binary (review.mjs logs it), never whichever `opencode` comes
# first on PATH: in a WSL shell that can be the Windows install (/mnt/c/…/npm/opencode), which
# cannot read this database and answers "Session not found".
oc=${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}
[ -x "$oc" ] || { echo "peek.sh: no OpenCode binary at $oc (set OPENCODE_BIN)" >&2; exit 1; }
out=$(mktemp) err=$(mktemp)
trap 'rm -f -- "$out" "$err"' EXIT
# To a file: a large session read through a pipe came back cut short. Retried: while the run
# writes, a read can meet "database is locked" (OpenCode's SQLite), and the next one succeeds.
ok=0
for try in 1 2 3 4 5; do
  if (cd /tmp && XDG_DATA_HOME=$H/data XDG_CACHE_HOME=$H/cache XDG_STATE_HOME=$H/state \
      "$oc" export "$sid" > "$out" 2> "$err") && jq -e .info.id "$out" > /dev/null 2>&1; then
    ok=1; break
  fi
  sleep 2
done
if [ $ok = 0 ]; then
  echo "peek.sh: opencode export $sid failed 5 times; its last error:" >&2
  grep -v '^Exporting session' "$err" | tail -5 >&2
  exit 1
fi
jq -r --argjson n "$n" '
  "\(.info.title) · \(.info.model.providerID)/\(.info.model.id) · \(.info.directory)",
  ([.messages[].parts[]
    | if .type == "tool" then "  tool \(.tool) [\(.state.status)]: \(.state.input | tostring | gsub("\n"; " ") | .[0:140])"
      elif .type == "text" and (.text | length) > 0 then "  says: \(.text | gsub("\n"; " ") | .[0:200])"
      else empty end] | .[-$n:][])
' "$out"
