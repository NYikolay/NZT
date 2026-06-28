#!/usr/bin/env bash
set -euo pipefail

# Run pytest inside the Docker app container.
# If called from pre-commit (during git push), containers are torn down
# after tests complete to avoid leaving them running.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

# Detect if we're running from pre-commit (git push)
if [ -n "${PRE_COMMIT:-}" ] || [ -n "${PRE_COMMIT_HOOK:-}" ]; then
    TEARDOWN=true
else
    TEARDOWN=false
fi

echo "⏳ Ensuring core services are up..."
docker compose \
    -f "$COMPOSE_FILE" \
    --profile core \
    up -d --wait 2>&1

echo "⏳ Running tests..."
docker compose \
    -f "$COMPOSE_FILE" \
    --profile core \
    run --rm app \
    python3 -m pytest --tb=short tests/ -q "$@"

# Store exit code
EXIT_CODE=$?

if [ "$TEARDOWN" = true ]; then
    echo "⏳ Tearing down containers..."
    docker compose \
        -f "$COMPOSE_FILE" \
        --profile core \
        down 2>&1
    echo "✅ Containers stopped."
fi

exit $EXIT_CODE