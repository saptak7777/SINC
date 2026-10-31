#!/usr/bin/env bash
# tests/slim_v3/test_slim_v3.sh
# S.L.I.M. v3 Integration Tests — 9-Tag Architectural Linter
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SLIM="${SLIM:-"$ROOT_DIR/bin/slim.elf"}"
FIXTURES="${ROOT_DIR}/tests/slim_v3/fixtures"

PASS=0
FAIL=0

run_test() {
    local name="$1"
    local fixture="$2"
    local expect_exit="$3"
    local expect_tag="$4"

    actual_out=$("${SLIM}" check "${FIXTURES}/${fixture}" 2>&1 || true)
    actual_exit=$("${SLIM}" check "${FIXTURES}/${fixture}" > /dev/null 2>&1; echo $?) || actual_exit=$?

    # Re-run to capture exit code properly
    set +e
    "${SLIM}" check "${FIXTURES}/${fixture}" > /tmp/sv3_out.txt 2>&1
    actual_exit=$?
    set -e
    actual_out=$(cat /tmp/sv3_out.txt)

    if [ "${actual_exit}" -eq "${expect_exit}" ]; then
        if [ -n "${expect_tag}" ]; then
            if echo "${actual_out}" | grep -q "${expect_tag}"; then
                echo "[Test] ${name}... PASS (Exit ${actual_exit}, ${expect_tag} detected)"
                PASS=$((PASS + 1))
            else
                echo "[Test] ${name}... FAIL (Exit ${actual_exit} OK but tag '${expect_tag}' not in output)"
                echo "       Output: ${actual_out}"
                FAIL=$((FAIL + 1))
            fi
        else
            echo "[Test] ${name}... PASS (Exit ${actual_exit})"
            PASS=$((PASS + 1))
        fi
    else
        echo "[Test] ${name}... FAIL (Expected exit ${expect_exit}, got ${actual_exit})"
        echo "       Output: ${actual_out}"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================================================="
echo " RUNNING SINC S.L.I.M. V3 TESTS (9-Tag Architectural Linter)"
echo "========================================================================="

run_test "[FOSSIL] self-assignment x=x detected"     "fossil_bad.sinc"       1 "FOSSIL"
run_test "[RAWDATA] bare 65535 literal detected"     "rawdata_bad.sinc"      1 "RAWDATA"
run_test "[RAWDATA] bare 4096 != literal detected"   "rawdata_hex_bad.sinc"  1 "RAWDATA"
run_test "[RAWDATA] yoda comparison 4096 == x detected" "rawdata_yoda_bad.sinc" 1 "RAWDATA"
run_test "[SPLINTER] parallel zero-init detected"    "splinter_bad.sinc"     1 "SPLINTER"
run_test "[SPLINTER] 3+ splintered vars detected"    "splinter_3var_bad.sinc" 1 "SPLINTER"
run_test "[SPLINTER] independent clean state passes" "splinter_clean.sinc"   0 ""
run_test "[SPLINTER] idiomatic slice pairs pass"     "splinter_slice_clean.sinc" 0 ""
run_test "[WRAPPER] 1:1 forwarding wrapper detected" "wrapper_bad.sinc"      1 "WRAPPER"
run_test "[WRAPPER] impure 1:1 wrapper detected"     "wrapper_impure_bad.sinc" 1 "WRAPPER"
run_test "[DEAD WEIGHT] dead island cluster caught"  "dead_island_bad.sinc"  1 "DEAD WEIGHT"
run_test "[UNNECESSARY] dead overwrite detected"     "overwrite_bad.sinc"    1 "UNNECESSARY"
run_test "[LAZY] deep call nesting detected"         "nesting_bad.sinc"      1 "LAZY"
run_test "Helpers pass all checks without false pos" "helper_clean.sinc"     0 ""
run_test "Clean code passes all v3 checks"           "clean_v3.sinc"         0 ""

echo "========================================================================="
TOTAL=$((PASS + FAIL))
if [ "${FAIL}" -eq 0 ]; then
    echo " ALL ${TOTAL} V3 TESTS PASSED"
    exit 0
else
    echo " ${FAIL}/${TOTAL} V3 TESTS FAILED"
    exit 1
fi
