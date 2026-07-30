#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

status=0

echo "========== forbidden archive/runtime files =========="
found=$(find . \
  -path './.git' -prune -o \
  -path './.venv' -prune -o \
  -path './site' -prune -o \
  \( -name '*.tar.gz' -o -name '*.bag' -o -name '*.db3' -o -name '*.pid' -o -name '*.log' \) \
  -type f -print)
if [ -n "$found" ]; then
  printf '%s\n' "$found"
  status=1
else
  echo "None found."
fi

echo
echo "========== possible secrets/private paths =========="
if grep -RInE \
  'BEGIN .*PRIVATE KEY|password[[:space:]]*[:=]|passwd[[:space:]]*[:=]|api[_-]?key[[:space:]]*[:=]|/home/darhan|darhan@' \
  . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=site --exclude='check_public_tree.sh'; then
  status=1
else
  echo "No obvious matches."
fi

exit "$status"
