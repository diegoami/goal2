#!/usr/bin/env bash
# [designed: owner, 2026-11-01, #493] Make this Linux machine (WSL included) a goal2 slow-test runner:
# GitHub's runner, checksum-verified, registered for diegoami/goal2 with the label goal2-slow-linux only,
# kept running by a systemd user service. The owner runs it on each of their own machines; every run
# pulls the original-game files from the owner's Drive, so never on a computer someone else uses.
#
#   bash tools/runner/setup-linux.sh            # registration token from `gh` (logged in as the owner)
#   GOAL2_RUNNER_TOKEN=<token> bash tools/runner/setup-linux.sh   # or a token from Settings > Actions > Runners
#
# GOAL2_RUNNER_DIR (default ~/actions-runner/goal2) and GOAL2_RUNNER_NAME (default goal2-<host>-linux)
# override the folder and the name. Run again to repair the service; an existing registration is kept.
set -euo pipefail
REPO=diegoami/goal2
LABEL=goal2-slow-linux
DIR=${GOAL2_RUNNER_DIR:-$HOME/actions-runner/goal2}
NAME=${GOAL2_RUNNER_NAME:-goal2-$(hostname -s)-linux}
UNIT=goal2-runner.service
export PATH="$HOME/.local/bin:$PATH"

missing=()
need() { command -v "$1" > /dev/null || missing+=("$1 ($2)"); }
need git "apt install git"
need curl "apt install curl"
need unzip "apt install unzip"
need sha256sum "coreutils"
need tar "apt install tar"
need uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
need systemctl "a systemd user session (WSL: systemd=true in /etc/wsl.conf)"
# offscreen Qt and SDL (the xcb ones ci.yml installs are for Qt's X11 windows, which the runs never open)
for lib in libEGL.so.1 libGL.so.1 libxkbcommon.so.0 libfontconfig.so.1 libdbus-1.so.3; do
    ldconfig -p 2> /dev/null | grep -q "$lib" || missing+=("$lib (apt install libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3)")
done
if [ ${#missing[@]} -gt 0 ]; then
    printf 'missing: %s\n' "${missing[@]}" >&2
    exit 1
fi
uv python find 3.12 > /dev/null 2>&1 || uv python install 3.12

mkdir -p "$DIR"
cd "$DIR"
if [ ! -f .runner ]; then
    token=${GOAL2_RUNNER_TOKEN:-}
    if [ -z "$token" ]; then
        command -v gh > /dev/null || { echo "no gh: set GOAL2_RUNNER_TOKEN (Settings > Actions > Runners > New)" >&2; exit 1; }
        token=$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token)
    fi
    release=$(curl -sSfL https://api.github.com/repos/actions/runner/releases/latest)
    tag=$(printf '%s' "$release" | grep -o '"tag_name": *"v[^"]*"' | grep -o 'v[0-9.]*')
    sum=$(printf '%s' "$release" | grep -o 'BEGIN SHA linux-x64 -->[0-9a-f]\{64\}' | grep -o '[0-9a-f]\{64\}')
    tgz=actions-runner-linux-x64-${tag#v}.tar.gz
    curl -sSfL "https://github.com/actions/runner/releases/download/$tag/$tgz" -o "$tgz"
    echo "$sum  $tgz" | sha256sum -c -
    tar xzf "$tgz" && rm "$tgz"
    ./config.sh --unattended --url "https://github.com/$REPO" --token "$token" --name "$NAME" \
        --labels "$LABEL" --no-default-labels --work w --replace
fi

mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/$UNIT" << EOF
[Unit]
Description=goal2 GitHub Actions runner ($NAME, label $LABEL; goal2#493)
After=network-online.target

[Service]
WorkingDirectory=$DIR
ExecStart=$DIR/run.sh
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now "$UNIT"
systemctl --user --no-pager status "$UNIT" | head -3

if [ "$(loginctl show-user "$USER" -p Linger --value 2> /dev/null)" != yes ]; then
    echo "to run without a login session: sudo loginctl enable-linger $USER"
fi
if grep -qi microsoft /proc/version; then
    echo "WSL: the runner runs while WSL does; Windows stops WSL some time after its last terminal closes."
fi
echo "runner $NAME (label $LABEL) installed in $DIR"
