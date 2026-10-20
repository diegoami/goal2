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
if ! rclone listremotes 2>/dev/null | grep -qx 'goal2drive:'; then
  if [ -n "${GOAL2_RCLONE_TOKEN:-}" ]; then
    rclone config create goal2drive drive scope=drive root_folder_id="$folder" token="$GOAL2_RCLONE_TOKEN" --non-interactive >/dev/null
  else
    echo "GOAL2_RCLONE_TOKEN is not set: no remote, no original-game files (docs/artifacts.md)"
  fi
fi
if rclone listremotes 2>/dev/null | grep -qx 'goal2drive:'; then
  python3 tools/artifacts.py pull
  python3 tools/check_goaldat.py .cache/GOAL.DAT && echo "GOAL.DAT verified"
fi

say "GitHub"
gh auth status >/dev/null 2>&1 && echo "gh is logged in" || echo "gh is not logged in: set GH_TOKEN with push and merge rights"

cat > .cache/cloud.env <<EOF
# written by tools/cloud_setup.sh
export PATH="$PWD/.cache/venv/bin:\$HOME/.local/bin:\$PATH"
export QT_QPA_PLATFORM=offscreen
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
EOF
say "done: source .cache/cloud.env, then python3 tools/check_premerge.py --expected-head \$(git rev-parse HEAD) --tests"
