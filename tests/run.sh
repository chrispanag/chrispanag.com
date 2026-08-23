#!/usr/bin/env bash
#
# Build the site the way production does and assert on the result.
#
#   ./tests/run.sh
#
# Requires Hugo extended (>= 0.162) and python3. The build goes to a temporary
# directory, so ./public is left alone.

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f themes/PaperMod/layouts/baseof.html ]; then
  echo "themes/PaperMod is empty. Run: git submodule update --init --recursive" >&2
  exit 2
fi

out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT

# No -D: production excludes drafts (buildDrafts: false), and that is what the
# assertions describe. --minify matches the minify.minifyOutput setting production
# builds with, so the checks run against the same bytes the CDN serves.
echo "building into $out"
hugo --quiet --minify --destination "$out"

python3 tests/check_build.py "$out"
