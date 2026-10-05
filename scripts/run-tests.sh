#!/usr/bin/env bash
# Run each service's tests in its own pytest process: api, bot and listener
# all ship a top-level `app` package, so they cannot share one interpreter.
#
# Usage:
#   ./scripts/run-tests.sh
#   ./scripts/run-tests.sh -k tag

set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

for suite in core api bot listener; do
    echo "== $suite"
    uv run --all-packages --with pytest --with httpx --with fakeredis \
        pytest "$suite/tests" -q -p no:cacheprovider "$@"
done
