#!/usr/bin/env bash
# ============================================================================
# NZT-backend: start all services (core + monitoring) in development mode.
#
# Uses a single docker-compose.yml with profiles so `--wait` works correctly
# across all service dependencies.
#
# Usage:
#   ./scripts/start-with-monitoring.sh
#   Ctrl+C to stop all services gracefully.
# ============================================================================

# Safety check — this is a bash script, not Python
if [ -z "${BASH_VERSION:-}" ]; then
    echo "ERROR: This script must be run with bash, not sh or python" >&2
    echo "Usage: bash scripts/start-with-monitoring.sh" >&2
    exit 1
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"
    docker compose \
        -f "$COMPOSE_FILE" \
        --profile core --profile monitoring \
        down -v 2>/dev/null || true
    echo -e "${GREEN}✅ All services stopped.${NC}"
}
# Only trigger on Ctrl+C (SIGINT / SIGTERM), not on normal exit
trap cleanup INT TERM

echo -e "${CYAN}🚀 Starting monitoring stack (Loki, Grafana, Alloy)...${NC}"
docker compose \
    -f "$COMPOSE_FILE" \
    --profile monitoring \
    up -d --wait 2>&1 || {
    echo -e "${RED}❌ Failed to start monitoring services${NC}"
    exit 1
}

echo -e "${CYAN}🚀 Starting core stack (PostgreSQL, Redis, App)...${NC}"
docker compose \
    -f "$COMPOSE_FILE" \
    --profile core \
    up -d --wait 2>&1 || {
    echo -e "${RED}❌ Failed to start core services${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✅ All services started successfully${NC}"
echo ""
echo -e "📊 ${CYAN}Grafana:${NC}     http://localhost:3000 (admin/admin)"
echo -e "🔍 ${CYAN}Loki:${NC}        http://localhost:3100"
echo -e "🌐 ${CYAN}Backend:${NC}     http://localhost:8000"
echo -e "📝 ${CYAN}App logs:${NC}    ./logs/"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services gracefully.${NC}"

# Keep the script alive so Ctrl+C triggers the trap
wait