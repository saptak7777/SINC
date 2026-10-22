#!/usr/bin/env bash
# =============================================================================
# tests/integration/test_slim.sh
# S.L.I.M. Master Integration Test Suite (All Phases)
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

echo "========================================================================="
echo " STARTING FULL S.L.I.M. LINTER TEST SUITE"
echo "========================================================================="

bash "$ROOT_DIR/tests/integration/test_slim_phase1.sh"
echo ""
bash "$ROOT_DIR/tests/integration/test_slim_phase2.sh"
echo ""
bash "$ROOT_DIR/tests/integration/test_slim_phase3.sh"

echo ""
echo "========================================================================="
echo " SUCCESS: ALL S.L.I.M. TEST SUITES PASSED (PHASES 1, 2, 3)"
echo " Core compiler speed, runtime, and zero-overhead semantics 100% preserved."
echo "========================================================================="
