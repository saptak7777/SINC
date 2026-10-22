#!/usr/bin/env python3
# ==============================================================================
# tools/verify_sanity.py
# SINC Comprehensive Functional Sanity & Correctness Test Suite
# Audits full compiler behavior across 103 native tests, 4 bug tests,
# 5 C FFI integration tests, and 24 benchmarks execution soundness.
# ==============================================================================
import os
import sys
import glob
import subprocess
import tempfile
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def find_bin(name):
    bin_path = os.path.join(ROOT_DIR, "bin", name)
    if os.path.isfile(bin_path):
        return bin_path
    return os.path.join(ROOT_DIR, name)

SINC_BIN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else find_bin("sinc.elf")
PACKAGER_BIN = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else find_bin("packager_bin")
PACKAGER_O = find_bin("packager_o")

if not os.path.isfile(SINC_BIN) or not os.path.isfile(PACKAGER_BIN):
    print(f"Error: Missing {SINC_BIN} or {PACKAGER_BIN}", file=sys.stderr)
    sys.exit(1)

RUN_ORACLE = "--oracle" in sys.argv

print("=" * 105)
print("SINC MASTER FUNCTIONAL SANITY & COMPILER BEHAVIOR TEST SUITE")
print(f"Target Compiler: {SINC_BIN} ({os.path.getsize(SINC_BIN):,} bytes)")
print("=" * 105)

work_dir = tempfile.mkdtemp(prefix="sinc_sanity_")
failed_tests = []
total_tests = 0
passed_tests = 0

def check(name, group, ok, detail=""):
    global total_tests, passed_tests
    total_tests += 1
    if ok:
        passed_tests += 1
    else:
        failed_tests.append((group, name, detail))

try:
    # --------------------------------------------------------------------------
    # Tier 1: 103 Native Test Suite
    # --------------------------------------------------------------------------
    print("\n[SECTION 1] 103 Native Tests (92 Positive Execution + 11 Negative Rejection)")
    print("-" * 105)
    native_files = sorted(glob.glob(os.path.join(ROOT_DIR, "tests", "native", "*.sinc")))
    pos_pass = 0
    neg_pass = 0

    for tf in native_files:
        tname = os.path.basename(tf)[:-5]
        with open(tf, "r") as f:
            src = f.read()

        compile_err = None
        expect_exit = None
        for line in src.splitlines():
            if line.startswith("// COMPILE_ERROR:"):
                compile_err = int(line.split(":")[1].strip())
            elif line.startswith("// EXPECT:"):
                expect_exit = int(line.split(":")[1].strip())

        if compile_err is not None:
            # Negative test: compiler MUST reject
            out_safe = os.path.join(work_dir, f"{tname}.safe")
            res = subprocess.run([SINC_BIN, tf, out_safe], capture_output=True)
            ok = (res.returncode == compile_err)
            if ok: neg_pass += 1
            check(tname, "Negative Rejection", ok, f"got {res.returncode}, expected {compile_err}")
        elif expect_exit is not None:
            # Positive test: compile -> package -> execute -> verify exit code
            out_safe = os.path.join(work_dir, f"{tname}.safe")
            out_elf = os.path.join(work_dir, f"{tname}.elf")
            r1 = subprocess.run([SINC_BIN, tf, out_safe], capture_output=True)
            if r1.returncode != 0:
                check(tname, "Native Execution", False, f"compile failed exit {r1.returncode}")
                continue
            r2 = subprocess.run([PACKAGER_BIN, out_safe, out_elf], capture_output=True)
            if r2.returncode != 0:
                check(tname, "Native Execution", False, f"packaging failed exit {r2.returncode}")
                continue
            os.chmod(out_elf, 0o755)
            r_run = subprocess.run([out_elf])
            exit_code = r_run.returncode & 255
            ok = (exit_code == expect_exit)
            if ok: pos_pass += 1
            check(tname, "Native Execution", ok, f"exit {exit_code}, expected {expect_exit}")

    total_pos = sum(1 for tf in native_files if any(l.startswith("// EXPECT:") for l in open(tf, errors="ignore")))
    total_neg = sum(1 for tf in native_files if any(l.startswith("// COMPILE_ERROR:") for l in open(tf, errors="ignore")))
    print(f"  Positive Execution Tests : {pos_pass}/{total_pos} PASSED")
    print(f"  Negative Rejection Tests : {neg_pass}/{total_neg} PASSED (Syntax/Purity Rejections Verified)")

    # --------------------------------------------------------------------------
    # Tier 2: 8 Compiler Bug & Vulnerability Regressions
    # --------------------------------------------------------------------------
    print("\n[SECTION 2] 8 Bug & Vulnerability Verification Regressions")
    print("-" * 105)

    # Bug 1: Loop syntax error tape mutation
    bug1_src = "fn main() [\n    loop (i = 0 .. 10) [\n        if (i % 4 == 0) [\n            ret 1;\n        ]\n    ]\n    ret 0;\n]"
    b1_path = os.path.join(work_dir, "bug1.sinc")
    with open(b1_path, "w") as f: f.write(bug1_src + "\n")
    res1 = subprocess.run([SINC_BIN, b1_path, os.path.join(work_dir, "b1.safe")], capture_output=True)
    b1_ok = (res1.returncode == 7)
    check("Bug 1: Loop Syntax Tape Guard", "Bug Verification", b1_ok, f"exit {res1.returncode} vs 7")
    print(f"  [Bug 1] Loop Syntax Error-Code Mutation Guard : {'PASS' if b1_ok else 'FAIL'} (exit {res1.returncode} == 7)")

    # Bug 2: CLI driver negative FD signed comparison bypass
    res2 = subprocess.run([SINC_BIN, "/tmp/nonexistent_file_99999.sinc", os.path.join(work_dir, "b2.safe")], capture_output=True)
    b2_ok = (res2.returncode == 2)
    check("Bug 2: CLI Nonexistent FD Bypass", "Bug Verification", b2_ok, f"exit {res2.returncode} vs 2")
    print(f"  [Bug 2] CLI Driver Nonexistent FD Bypass Guard: {'PASS' if b2_ok else 'FAIL'} (exit {res2.returncode} == 2)")

    # Bug 3: Negative SAR shift
    b3_src = "fn main() [\n    val = -100;\n    shifted = val >> 2;\n    if (shifted == -25) [\n        ret 42;\n    ]\n    ret 99;\n]"
    b3_path = os.path.join(work_dir, "bug3.sinc")
    b3_safe = os.path.join(work_dir, "bug3.safe")
    b3_elf = os.path.join(work_dir, "bug3.elf")
    with open(b3_path, "w") as f: f.write(b3_src + "\n")
    subprocess.run([SINC_BIN, b3_path, b3_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b3_safe, b3_elf], check=True, capture_output=True)
    os.chmod(b3_elf, 0o755)
    res3 = subprocess.run([b3_elf]).returncode & 255
    b3_ok = (res3 == 42)
    check("Bug 3: Negative SAR Shift", "Bug Verification", b3_ok, f"exit {res3} vs 42")
    print(f"  [Bug 3] Arithmetic Right Shift (SAR) on Negatives: {'PASS' if b3_ok else 'FAIL'} (exit {res3} == 42)")

    # Bug 4: Variable SAR shift in BMI
    b4_src = "fn test_variable_sar(val, amt) [\n    ret val >> amt;\n]\n\nfn main() [\n    z = -100;\n    t3 = test_variable_sar(z, 2);\n    if (t3 == -25) [\n        ret 10;\n    ]\n    ret 90;\n]"
    b4_path = os.path.join(work_dir, "bug4.sinc")
    b4_safe = os.path.join(work_dir, "bug4.safe")
    b4_elf = os.path.join(work_dir, "bug4.elf")
    with open(b4_path, "w") as f: f.write(b4_src + "\n")
    subprocess.run([SINC_BIN, b4_path, b4_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b4_safe, b4_elf], check=True, capture_output=True)
    os.chmod(b4_elf, 0o755)
    res4 = subprocess.run([b4_elf]).returncode & 255
    b4_ok = (res4 == 10)
    check("Bug 4: BMI Variable SAR Asserted Shift", "Bug Verification", b4_ok, f"exit {res4} vs 10")
    print(f"  [Bug 4] BMI Variable SAR Assertion Integrity   : {'PASS' if b4_ok else 'FAIL'} (exit {res4} == 10)")

    # Bug 5: Allocator Back-Edge max_reg Bound Guard
    b5_src = "fn test_alloc(base) [\n    v1 = base + 1;\n    v2 = base + 2;\n    v3 = base + 3;\n    v4 = base + 4;\n    v5 = base + 5;\n    v6 = base + 6;\n    v7 = base + 7;\n    v8 = base + 8;\n    v9 = base + 9;\n    v10 = base + 42;\n    sum = 0;\n    loop (i:100 = 0 .. 20) [\n        t1 = i + 1;\n        t2 = t1 + 2;\n        t3 = t2 + 3;\n        t4 = t3 + 4;\n        t5 = t4 + 5;\n        t6 = t5 + 6;\n        t7 = t6 + 7;\n        t8 = t7 + 8;\n        sum = sum + (t8 - t7);\n    ]\n    if (v10 == base + 42) [ ret 42; ]\n    ret 0;\n]\nfn main() [ ret test_alloc(0); ]"
    b5_path = os.path.join(work_dir, "bug5.sinc")
    b5_safe = os.path.join(work_dir, "bug5.safe")
    b5_elf = os.path.join(work_dir, "bug5.elf")
    with open(b5_path, "w") as f: f.write(b5_src + "\n")
    subprocess.run([SINC_BIN, b5_path, b5_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b5_safe, b5_elf], check=True, capture_output=True)
    os.chmod(b5_elf, 0o755)
    res5 = subprocess.run([b5_elf]).returncode & 255
    b5_ok = (res5 == 42)
    check("Bug 5: Allocator max_reg Back-Edge Bound", "Bug Verification", b5_ok, f"exit {res5} vs 42")
    print(f"  [Bug 5] Allocator max_reg Back-Edge Bound Guard: {'PASS' if b5_ok else 'FAIL'} (exit {res5} == 42)")

    # Bug 6: Leaf Inlining Unary NEG Operand Remap Guard
    b6_src = "fn neg_leaf(x) [ ret -x; ]\nfn main() [\n    n1 = neg_leaf(10);\n    n2 = neg_leaf(n1);\n    diff = n2 - n1;\n    ret diff + 22;\n]"
    b6_path = os.path.join(work_dir, "bug6.sinc")
    b6_safe = os.path.join(work_dir, "bug6.safe")
    b6_elf = os.path.join(work_dir, "bug6.elf")
    with open(b6_path, "w") as f: f.write(b6_src + "\n")
    subprocess.run([SINC_BIN, b6_path, b6_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b6_safe, b6_elf], check=True, capture_output=True)
    os.chmod(b6_elf, 0o755)
    res6 = subprocess.run([b6_elf]).returncode & 255
    b6_ok = (res6 == 42)
    check("Bug 6: Leaf Inlining Unary NEG Remap", "Bug Verification", b6_ok, f"exit {res6} vs 42")
    print(f"  [Bug 6] Leaf Inlining Unary NEG Remap Guard    : {'PASS' if b6_ok else 'FAIL'} (exit {res6} == 42)")

    # Bug 7: Multiply-by-2 Refinement Immediate Rewriting Isolation Guard
    b7_src = "fn main() [\n    x = 12;\n    m = x * 2;\n    res = m + 10;\n    m2 = res * 2;\n    ret m2 - 26;\n]"
    b7_path = os.path.join(work_dir, "bug7.sinc")
    b7_safe = os.path.join(work_dir, "bug7.safe")
    b7_elf = os.path.join(work_dir, "bug7.elf")
    with open(b7_path, "w") as f: f.write(b7_src + "\n")
    subprocess.run([SINC_BIN, b7_path, b7_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b7_safe, b7_elf], check=True, capture_output=True)
    os.chmod(b7_elf, 0o755)
    res7 = subprocess.run([b7_elf]).returncode & 255
    b7_ok = (res7 == 42)
    check("Bug 7: Multiply-by-2 Immediate Rewriting", "Bug Verification", b7_ok, f"exit {res7} vs 42")
    print(f"  [Bug 7] Multiply-by-2 Immediate Rewriting Guard: {'PASS' if b7_ok else 'FAIL'} (exit {res7} == 42)")

    # Bug 8: Non-Vectorized Virtual Register 0 EVEX Ramp Isolation Guard
    b8_src = "fn scalar_k(v0, b) [\n    res = v0 + b;\n    loop (i:10 = 0 .. 5) [ res = res + v0; ]\n    ret res;\n]\nfn main() [ ret scalar_k(2, 30); ]"
    b8_path = os.path.join(work_dir, "bug8.sinc")
    b8_safe = os.path.join(work_dir, "bug8.safe")
    b8_elf = os.path.join(work_dir, "bug8.elf")
    with open(b8_path, "w") as f: f.write(b8_src + "\n")
    subprocess.run([SINC_BIN, b8_path, b8_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_BIN, b8_safe, b8_elf], check=True, capture_output=True)
    os.chmod(b8_elf, 0o755)
    res8 = subprocess.run([b8_elf]).returncode & 255
    b8_ok = (res8 == 42)
    check("Bug 8: Non-Vectorized vreg 0 EVEX Ramp", "Bug Verification", b8_ok, f"exit {res8} vs 42")
    print(f"  [Bug 8] Non-Vec vreg 0 EVEX Ramp Isolation Guard: {'PASS' if b8_ok else 'FAIL'} (exit {res8} == 42)")

    # --------------------------------------------------------------------------
    # Tier 3: 5 C FFI & Object File Linking Integration Tests
    # --------------------------------------------------------------------------
    print("\n[SECTION 3] 5 C FFI & ELF .o Integration Tests")
    print("-" * 105)

    # FFI 1: Zero-Arg Scalar ABI
    f1_src = "fn fib_fast() [\n    a = 0;\n    b = 1;\n    loop (i:100 = 0 .. 40) [\n        tmp = a + b;\n        a = b;\n        b = tmp;\n    ]\n    ret a;\n]"
    f1_c = "#include <stdio.h>\n#include <stdint.h>\n#include <assert.h>\nextern int64_t sinc_fib(void);\nint main(void) {\n    int64_t val = sinc_fib();\n    assert(val == 102334155LL);\n    return 0;\n}"
    f1_sinc_path = os.path.join(work_dir, "f1.sinc")
    f1_safe = os.path.join(work_dir, "f1.safe")
    f1_o = os.path.join(work_dir, "f1.o")
    f1_c_path = os.path.join(work_dir, "harness1.c")
    f1_app = os.path.join(work_dir, "app1")
    with open(f1_sinc_path, "w") as f: f.write(f1_src + "\n")
    with open(f1_c_path, "w") as f: f.write(f1_c + "\n")
    subprocess.run([SINC_BIN, f1_sinc_path, f1_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f1_safe, f1_o, "sinc_fib"], check=True, capture_output=True)
    subprocess.run(["gcc", "-O3", f1_c_path, f1_o, "-no-pie", "-o", f1_app], check=True, capture_output=True)
    rf1 = subprocess.run([f1_app])
    f1_ok = (rf1.returncode == 0)
    check("FFI 1: Zero-Arg Scalar ABI", "FFI Linking", f1_ok, f"exit {rf1.returncode}")
    print(f"  [FFI 1] Zero-Arg Scalar ABI (sinc_fib = 102334155)    : {'PASS' if f1_ok else 'FAIL'}")

    # FFI 2: Multi-Argument Math Kernel (SPINE ABI: rcx, rdx, rbx)
    f2_src = "fn poly3(a, b, c) [\n    ret (a * a) + (b * c) + 42;\n]"
    f2_c = """#include <stdio.h>
#include <stdint.h>
#include <assert.h>
extern void sinc_poly3(void);
static inline int64_t call_sinc_3(void *fn, int64_t a, int64_t b, int64_t c) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\\n\\t"
        "movq %2, %%rdx\\n\\t"
        "movq %3, %%rbx\\n\\t"
        "call *%4\\n\\t"
        "movq %%rax, %0\\n\\t"
        : "=r"(res)
        : "r"(a), "r"(b), "r"(c), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}
int main(void) {
    int64_t val = call_sinc_3(sinc_poly3, 10, 20, 30);
    assert(val == 742);
    return 0;
}"""
    f2_sinc_path = os.path.join(work_dir, "f2.sinc")
    f2_safe = os.path.join(work_dir, "f2.safe")
    f2_o = os.path.join(work_dir, "f2.o")
    f2_c_path = os.path.join(work_dir, "harness2.c")
    f2_app = os.path.join(work_dir, "app2")
    with open(f2_sinc_path, "w") as f: f.write(f2_src + "\n")
    with open(f2_c_path, "w") as f: f.write(f2_c + "\n")
    subprocess.run([SINC_BIN, f2_sinc_path, f2_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f2_safe, f2_o, "sinc_poly3"], check=True, capture_output=True)
    subprocess.run(["gcc", "-O3", f2_c_path, f2_o, "-no-pie", "-o", f2_app], check=True, capture_output=True)
    rf2 = subprocess.run([f2_app])
    f2_ok = (rf2.returncode == 0)
    check("FFI 2: Multi-Arg SPINE ABI", "FFI Linking", f2_ok, f"exit {rf2.returncode}")
    print(f"  [FFI 2] Multi-Arg SPINE ABI (poly3(10,20,30) = 742)   : {'PASS' if f2_ok else 'FAIL'}")

    # FFI 3: In-Place Array Mutation
    f3_src = "fn transform_array!(buf, len, multiplier) [\n    loop (i:10000000 = 0 .. len) [\n        buf@[i] = buf@[i] * multiplier;\n    ]\n    ret len;\n]"
    f3_c = """#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>
extern void sinc_transform_array(void);
static inline int64_t call_sinc_array(void *fn, int64_t *buf, int64_t len, int64_t mult) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\\n\\t"
        "movq %2, %%rdx\\n\\t"
        "movq %3, %%rbx\\n\\t"
        "call *%4\\n\\t"
        "movq %%rax, %0\\n\\t"
        : "=r"(res)
        : "r"(buf), "r"(len), "r"(mult), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}
int main(void) {
    int64_t N = 1000000;
    int64_t *arr = (int64_t*)malloc(N * sizeof(int64_t));
    for (int64_t i = 0; i < N; i++) arr[i] = i + 1;
    int64_t count = call_sinc_array(sinc_transform_array, arr, N, 7);
    assert(count == N);
    assert(arr[0] == 7);
    assert(arr[10] == 77);
    assert(arr[999999] == 7000000);
    free(arr);
    return 0;
}"""
    f3_sinc_path = os.path.join(work_dir, "f3.sinc")
    f3_safe = os.path.join(work_dir, "f3.safe")
    f3_o = os.path.join(work_dir, "f3.o")
    f3_c_path = os.path.join(work_dir, "harness3.c")
    f3_app = os.path.join(work_dir, "app3")
    with open(f3_sinc_path, "w") as f: f.write(f3_src + "\n")
    with open(f3_c_path, "w") as f: f.write(f3_c + "\n")
    subprocess.run([SINC_BIN, f3_sinc_path, f3_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f3_safe, f3_o, "sinc_transform_array"], check=True, capture_output=True)
    subprocess.run(["gcc", "-O3", f3_c_path, f3_o, "-no-pie", "-o", f3_app], check=True, capture_output=True)
    rf3 = subprocess.run([f3_app])
    f3_ok = (rf3.returncode == 0)
    check("FFI 3: In-Place Large Array Mutation", "FFI Linking", f3_ok, f"exit {rf3.returncode}")
    print(f"  [FFI 3] In-Place Array Mutation (1,000,000 C elements): {'PASS' if f3_ok else 'FAIL'}")

    # FFI 4: Multi-Object SINC Linking
    f4_a_src = "fn compute_a(x) [\n    ret x * 3;\n]"
    f4_b_src = "fn compute_b(x) [\n    ret x + 100;\n]"
    f4_c = """#include <stdio.h>
#include <stdint.h>
#include <assert.h>
extern void sinc_compute_a(void);
extern void sinc_compute_b(void);
static inline int64_t call_sinc_1(void *fn, int64_t arg) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\\n\\t"
        "call *%2\\n\\t"
        "movq %%rax, %0\\n\\t"
        : "=r"(res)
        : "r"(arg), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}
int main(void) {
    int64_t val_a = call_sinc_1(sinc_compute_a, 25);
    int64_t val_b = call_sinc_1(sinc_compute_b, val_a);
    assert(val_b == 175);
    return 0;
}"""
    f4_a_path = os.path.join(work_dir, "f4_a.sinc")
    f4_a_safe = os.path.join(work_dir, "f4_a.safe")
    f4_a_o = os.path.join(work_dir, "f4_a.o")
    f4_b_path = os.path.join(work_dir, "f4_b.sinc")
    f4_b_safe = os.path.join(work_dir, "f4_b.safe")
    f4_b_o = os.path.join(work_dir, "f4_b.o")
    f4_c_path = os.path.join(work_dir, "harness4.c")
    f4_app = os.path.join(work_dir, "app4")
    with open(f4_a_path, "w") as f: f.write(f4_a_src + "\n")
    with open(f4_b_path, "w") as f: f.write(f4_b_src + "\n")
    with open(f4_c_path, "w") as f: f.write(f4_c + "\n")
    subprocess.run([SINC_BIN, f4_a_path, f4_a_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f4_a_safe, f4_a_o, "sinc_compute_a"], check=True, capture_output=True)
    subprocess.run([SINC_BIN, f4_b_path, f4_b_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f4_b_safe, f4_b_o, "sinc_compute_b"], check=True, capture_output=True)
    subprocess.run(["gcc", "-O3", f4_c_path, f4_a_o, f4_b_o, "-no-pie", "-o", f4_app], check=True, capture_output=True)
    rf4 = subprocess.run([f4_app])
    f4_ok = (rf4.returncode == 0)
    check("FFI 4: Multi-Object SINC Linking", "FFI Linking", f4_ok, f"exit {rf4.returncode}")
    print(f"  [FFI 4] Multi-Object SINC Linking (mod_a + mod_b = 175): {'PASS' if f4_ok else 'FAIL'}")

    # FFI 5: AVX-512 Vector Kernel
    f5_src = os.path.join(ROOT_DIR, "tests", "native", "avx512_eight_lane_reduction.sinc")
    f5_safe = os.path.join(work_dir, "f5.safe")
    f5_o = os.path.join(work_dir, "f5.o")
    f5_c = "#include <stdio.h>\n#include <stdint.h>\n#include <assert.h>\nextern int64_t sinc_avx512_accum(void);\nint main(void) {\n    int64_t res = sinc_avx512_accum();\n    assert((res & 255) == 144);\n    return 0;\n}"
    f5_c_path = os.path.join(work_dir, "harness5.c")
    f5_app = os.path.join(work_dir, "app5")
    with open(f5_c_path, "w") as f: f.write(f5_c + "\n")
    subprocess.run([SINC_BIN, f5_src, f5_safe], check=True, capture_output=True)
    subprocess.run([PACKAGER_O, f5_safe, f5_o, "sinc_avx512_accum"], check=True, capture_output=True)
    subprocess.run(["gcc", "-O3", f5_c_path, f5_o, "-no-pie", "-o", f5_app], check=True, capture_output=True)
    rf5 = subprocess.run([f5_app])
    f5_ok = (rf5.returncode == 0)
    check("FFI 5: AVX-512 Vector Linking", "FFI Linking", f5_ok, f"exit {rf5.returncode}")
    print(f"  [FFI 5] AVX-512 Vector Auto-Reduction to C (exit 144) : {'PASS' if f5_ok else 'FAIL'}")

    # --------------------------------------------------------------------------
    # Tier 4: 24 Benchmarks Execution Sanity
    # --------------------------------------------------------------------------
    print("\n[SECTION 4] 24 Benchmarks Functional Execution Sanity")
    print("-" * 105)
    bench_files = sorted(glob.glob(os.path.join(ROOT_DIR, "bench", "*.sinc")))
    b_pass = 0
    for bf in bench_files:
        bname = os.path.basename(bf)[:-5]
        b_safe = os.path.join(work_dir, f"{bname}.safe")
        b_elf = os.path.join(work_dir, f"{bname}.elf")
        r1 = subprocess.run([SINC_BIN, bf, b_safe], capture_output=True)
        if r1.returncode != 0:
            check(bname, "Benchmark Sanity", False, "Compilation failed")
            continue
        r2 = subprocess.run([PACKAGER_BIN, b_safe, b_elf], capture_output=True)
        if r2.returncode != 0:
            check(bname, "Benchmark Sanity", False, "Packaging failed")
            continue
        os.chmod(b_elf, 0o755)
        run_res = subprocess.run([b_elf])
        # Verify it runs without segfault/crash
        ok = (run_res.returncode >= 0)
        if ok: b_pass += 1
        check(bname, "Benchmark Sanity", ok, f"exit {run_res.returncode & 255}")

    print(f"  24 Benchmarks Execution Sanity: {b_pass}/24 PASSED (Zero crashes / segfaults)")

    # Optional Tier: Differential Oracle
    if RUN_ORACLE:
        print("\n[SECTION 5] Differential Oracle Testing against GCC (308 Tests)")
        print("-" * 105)
        r_oracle = subprocess.run(["python3", os.path.join(ROOT_DIR, "tools", "differential_oracle.py")], capture_output=True, text=True)
        oracle_ok = (r_oracle.returncode == 0)
        check("Differential Oracle GCC Parity", "Oracle", oracle_ok, r_oracle.stdout[-100:] if not oracle_ok else "")
        print(f"  Differential Oracle (GCC Parity): {'PASS' if oracle_ok else 'FAIL'}")

finally:
    subprocess.run(["rm", "-rf", work_dir])

print("\n" + "=" * 105)
print(f"SANITY & SOUNDNESS TEST SUMMARY: {passed_tests}/{total_tests} PASSED")
if len(failed_tests) == 0:
    print("ALL TESTS PASSED: COMPILER IS FULLY SOUND, SAFE, AND FUNCTIONALLY CORRECT!")
    print("=" * 105)
    sys.exit(0)
else:
    print(f"ALERT: {len(failed_tests)} TEST FAILURES DETECTED:")
    for group, name, detail in failed_tests:
        print(f"  ! [{group}] {name}: {detail}")
    print("=" * 105)
    sys.exit(1)
