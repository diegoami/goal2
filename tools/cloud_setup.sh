#!/usr/bin/env bash
# [designed: owner, 2026-10-20] Prepare a fresh checkout, a cloud session included, to work on
# goal2 (docs/cloud.md). Safe to run again; each step skips what is already in place.
#
#   GOAL2_RCLONE_TOKEN='{"access_token":...}' tools/cloud_setup.sh
#
# GOAL2_RCLONE_TOKEN is the `token = {...}` value of the goal2drive remote in a configured
# machine's ~/.config/rclone/rclone.conf, kept as a secret, never committed. Without it the
# original-game files are not pulled and the steps that need them are skipped.
# Afterwards: source .cache/cloud.env
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
say() { printf '== %s\n' "$*"; }
RCLONE_VERSION=v1.75.2
mkdir -p .cache "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

say "system libraries for offscreen Qt and SDL"
if command -v apt-get >/dev/null && [ "$(id -u)" = 0 ]; then
  apt-get update -qq && apt-get install -y -qq libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 >/dev/null \
    || echo "apt-get failed; Qt tests may not start"
else
  echo "skipped (not root or no apt-get); install libegl1 libgl1 libxkbcommon0 if Qt fails to load"
fi

say "Python environment in .cache/venv with goal2[desktop,watched,match-view]"
[ -x .cache/venv/bin/python ] || python3 -m venv .cache/venv
.cache/venv/bin/python -m pip install -q --upgrade pip
.cache/venv/bin/python -m pip install -q -e '.[desktop,watched,match-view]'

say "rclone"
if ! command -v rclone >/dev/null && command -v apt-get >/dev/null && [ "$(id -u)" = 0 ]; then
  apt-get install -y -qq rclone >/dev/null 2>&1 || true
fi
if ! command -v rclone >/dev/null; then
  tmp=$(mktemp -d)
  zip="rclone-$RCLONE_VERSION-linux-amd64.zip"
  curl -sSfL "https://downloads.rclone.org/$RCLONE_VERSION/$zip" -o "$tmp/$zip"
  curl -sSfL "https://downloads.rclone.org/$RCLONE_VERSION/SHA256SUMS" -o "$tmp/SHA256SUMS"
  (cd "$tmp" && grep " $zip\$" SHA256SUMS | sha256sum -c --quiet -)
  unzip -q "$tmp/$zip" -d "$tmp"
  cp "$tmp/rclone-$RCLONE_VERSION-linux-amd64/rclone" "$HOME/.local/bin/"
  rm -rf "$tmp"
fi
rclone version | head -1

say "Drive remote goal2drive and the original-game files"
folder=$(python3 -c "import json,re;print(re.search(r'folders/([\w-]+)',json.load(open('artifacts.json'))['drive']['folderUrl']).group(1))")
token_ok() {  # the whole JSON value of rclone.conf's `token = {...}`, refresh_token included
  printf '%s' "$1" | python3 -c "import json,sys; t=json.load(sys.stdin); sys.exit(0 if t.get('refresh_token') else 1)" 2>/dev/null
}
# With the secret set, the remote is (re)created every time, so a corrected secret replaces a bad one.
if [ -z "${GOAL2_RCLONE_TOKEN:-}" ]; then
  rclone listremotes 2>/dev/null | grep -qx 'goal2drive:' \
    || echo "GOAL2_RCLONE_TOKEN is not set: no remote, no original-game files (docs/cloud.md)"
elif ! token_ok "$GOAL2_RCLONE_TOKEN"; then
  echo "GOAL2_RCLONE_TOKEN is not the whole token: set it to the JSON after 'token = ' in rclone.conf,"
  echo "from { to }, with refresh_token in it (it starts with {\"access_token\":...). No remote created."
  rclone config delete goal2drive >/dev/null 2>&1 || true
else
  # RCLONE_DRIVE_CLIENT_ID/SECRET: the owner's own OAuth client, when the token was made with it
  rclone config create goal2drive drive scope=drive root_folder_id="$folder" token="$GOAL2_RCLONE_TOKEN" \
    ${RCLONE_DRIVE_CLIENT_ID:+client_id="$RCLONE_DRIVE_CLIENT_ID"} \
    ${RCLONE_DRIVE_CLIENT_SECRET:+client_secret="$RCLONE_DRIVE_CLIENT_SECRET"} --non-interactive >/dev/null \
    || echo "could not create the goal2drive remote"
fi
# A Drive failure never stops the setup: the rest (gh, cloud.env) still runs.
if rclone listremotes 2>/dev/null | grep -qx 'goal2drive:'; then
  if python3 tools/artifacts.py pull; then
    python3 tools/check_goaldat.py .cache/GOAL.DAT >/dev/null && echo "GOAL.DAT verified" || echo "GOAL.DAT missing or wrong"
  else
    echo "pulling the original-game files failed; check the token and the network (docs/cloud.md)"
  fi
fi

say "GitHub"
if ! command -v gh >/dev/null && command -v apt-get >/dev/null && [ "$(id -u)" = 0 ]; then
  { apt-get install -y -qq gh || { apt-get update -qq && apt-get install -y -qq gh; }; } >/dev/null 2>&1 || echo "could not install gh"
fi
gh auth status >/dev/null 2>&1 && echo "gh is logged in" || echo "gh is not logged in: set GH_TOKEN (docs/cloud.md)"

cat > .cache/cloud.env <<EOF
# written by tools/cloud_setup.sh
export PATH="$PWD/.cache/venv/bin:\$HOME/.local/bin:\$PATH"
export QT_QPA_PLATFORM=offscreen
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
EOF
say "done: source .cache/cloud.env, then python3 tools/check_premerge.py --expected-head \$(git rev-parse HEAD) --tests"
