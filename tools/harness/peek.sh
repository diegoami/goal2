#!/usr/bin/env bash
# [designed: T72] Same current binary/major-aware owned receipt reader as the review harness.
set -eu
exec node "$(dirname "$0")/peek.mjs" "$@"
