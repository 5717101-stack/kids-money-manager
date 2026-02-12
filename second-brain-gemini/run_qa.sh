#!/bin/bash
# ============================================================================
# Second Brain QA Runner
# ============================================================================
# Usage:
#   ./run_qa.sh              — Run all non-live tests
#   ./run_qa.sh unit         — Run unit tests only
#   ./run_qa.sh integration  — Run integration tests only
#   ./run_qa.sh e2e          — Run E2E tests only
#   ./run_qa.sh live         — Run live tests (real APIs, use with caution)
#   ./run_qa.sh coverage     — Run with coverage report
#   ./run_qa.sh fixtures     — Generate test audio fixtures
# ============================================================================

set -e

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Second Brain QA Suite v1.0               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"

# Check if dev dependencies are installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements-dev.txt
fi

MODE="${1:-all}"

case "$MODE" in
    unit)
        echo -e "\n${GREEN}Running UNIT tests...${NC}\n"
        python -m pytest tests/unit -v --tb=short
        ;;
    integration)
        echo -e "\n${GREEN}Running INTEGRATION tests...${NC}\n"
        python -m pytest tests/integration -v --tb=short
        ;;
    e2e)
        echo -e "\n${GREEN}Running E2E tests...${NC}\n"
        python -m pytest tests/e2e -v --tb=short -m "not live"
        ;;
    live)
        echo -e "\n${YELLOW}Running LIVE tests (real APIs)...${NC}\n"
        python -m pytest tests/ -v --tb=short -m "live"
        ;;
    coverage)
        echo -e "\n${GREEN}Running ALL tests with COVERAGE...${NC}\n"
        python -m pytest tests/ -v --tb=short -m "not live" \
            --cov=app --cov-report=term-missing --cov-report=html
        echo -e "\n${GREEN}Coverage report: htmlcov/index.html${NC}"
        ;;
    fixtures)
        echo -e "\n${GREEN}Generating test audio fixtures...${NC}\n"
        python -m tests.fixtures.generate_test_audio
        ;;
    all)
        echo -e "\n${GREEN}Running ALL tests (unit + integration + e2e)...${NC}\n"
        python -m pytest tests/ -v --tb=short -m "not live"
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: ./run_qa.sh [unit|integration|e2e|live|coverage|fixtures|all]"
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some tests failed (exit code: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
