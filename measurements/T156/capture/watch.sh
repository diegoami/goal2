#!/bin/bash
# [designed: T156] Follow a watched match with timed waits, one logged step each:
#   RUN=/tmp/goal2-t156-run1 watch.sh SECS MAXSTEPS LABEL
# It stops at the first screen that leaves the plain pitch legend (no "R-result" on the bottom line)
# or shows a prompt, notice or board, so the next action is chosen by hand. Each wait is one step of
# server.py's log; the script never sends a key.
here=$(dirname "$0")
secs=$1; max=$2; label=$3
for i in $(seq 1 "$max"); do
  out=$(python3 "$here/client.py" "$RUN" wait "$secs" "$label")
  head -1 <<<"$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['step'], d['text_digest'], d['bottom'][:80])"
  txt=$(tail -n +2 <<<"$out")
  bottom=$(head -1 <<<"$out" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['bottom'])")
  if ! grep -q "R-result" <<<"$bottom" || grep -qiE "\(Y/N\)|taker|any key|SUBSTITUTION|INJURED|BOOKED|SENT OFF|half time|full time" <<<"$txt"; then
    echo "$txt"; exit 0
  fi
done
echo "$txt"
