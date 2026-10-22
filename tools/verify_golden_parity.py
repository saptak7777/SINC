#!/usr/bin/env python3
# ==============================================================================
# tools/verify_golden_parity.py
# SINC Master Golden Verification Suite & Baseline Engine
# ==============================================================================
import os
import sys
import subprocess
import hashlib
import json
import glob
import shutil
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY_DIR = os.path.join(ROOT_DIR, "verify")
RESULTS_PATH = os.path.join(VERIFY_DIR, "results.json")

def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def build_golden_baseline(sinc_bin, packager_bin, packager_o):
    print("=" * 105)
    print("BUILDING SINC GOLDEN BASELINE VERIFICATION SUITE IN verify/")
    print("=" * 105)

    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    commit_short = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], cwd=ROOT_DIR, text=True).strip()

    seed_dir = os.path.join(VERIFY_DIR, "seed")
    bench_dir = os.path.join(VERIFY_DIR, "benchmarks_24")
    test_dir = os.path.join(VERIFY_DIR, "native_tests")
    bug_dir = os.path.join(VERIFY_DIR, "bug_tests")
    ffi_dir = os.path.join(VERIFY_DIR, "ffi_tests")

    shutil.rmtree(VERIFY_DIR, ignore_errors=True)
    os.makedirs(seed_dir, exist_ok=True)
    os.makedirs(bench_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(bug_dir, exist_ok=True)
    os.makedirs(ffi_dir, exist_ok=True)

    # 1. Compiler Seed & Self-Hosting
    print("[1/5] Locking Seed Compiler Binaries (sinc.elf, sinc.safe, packager_bin, packager_o)...")
    subprocess.run([os.path.join(ROOT_DIR, "build.sh"), "--assemble-only", "/tmp/compiler_assembled.sinc"], check=True)
    seed_safe = os.path.join(seed_dir, "sinc.safe")
    subprocess.run([sinc_bin, "/tmp/compiler_assembled.sinc", seed_safe], check=True)
    shutil.copy2(sinc_bin, os.path.join(seed_dir, "sinc.elf"))
    shutil.copy2(packager_bin, os.path.join(seed_dir, "packager_bin"))
    shutil.copy2(packager_o, os.path.join(seed_dir, "packager_o"))

    # 2. 24 Benchmarks
    print("[2/5] Compiling and Packaging all 24 Benchmarks...")
    bench_meta = {}
    bench_files = sorted(glob.glob(os.path.join(ROOT_DIR, "bench", "*.sinc")))
    assert len(bench_files) == 24, f"Expected 24 benchmarks, found {len(bench_files)}"

    for sf in bench_files:
        bname = os.path.basename(sf)[:-5]
        safe_out = os.path.join(bench_dir, f"{bname}.safe")
        elf_out = os.path.join(bench_dir, f"{bname}.elf")
        subprocess.run([sinc_bin, sf, safe_out], check=True)
        subprocess.run([packager_bin, safe_out, elf_out], check=True)
        os.chmod(elf_out, 0o755)
        exit_code = subprocess.run([elf_out]).returncode & 255
        bench_meta[bname] = {
            "exit_code": exit_code,
            "safe_sz": os.path.getsize(safe_out),
            "safe_sha": sha256_file(safe_out),
            "elf_sz": os.path.getsize(elf_out),
            "elf_sha": sha256_file(elf_out),
        }

    # 3. 103 Native Tests
    print("[3/5] Compiling and Packaging all 103 Native Tests...")
    native_meta = {}
    all_files = sorted(glob.glob(os.path.join(ROOT_DIR, "tests", "native", "*.sinc")))
    native_files = []
    for tf in all_files:
        with open(tf, "r") as f:
            if "KNOWN DEFECT" in f.read():
                continue
        native_files.append(tf)
    assert len(native_files) >= 103, f"Expected at least 103 native tests, found {len(native_files)}"

    pos_count = 0
    neg_count = 0

    for tf in native_files:
        tname = os.path.basename(tf)[:-5]
        with open(tf, "r") as f:
            src = f.read()
        compile_error = None
        expected_exit = None
        for line in src.splitlines():
            if line.startswith("// COMPILE_ERROR:"):
                compile_error = int(line.split(":")[1].strip())
            elif line.startswith("// EXPECT:"):
                expected_exit = int(line.split(":")[1].strip())

        if compile_error is not None:
            neg_count += 1
            native_meta[tname] = {
                "type": "negative_rejection",
                "compile_error": compile_error,
            }
        elif expected_exit is not None:
            pos_count += 1
            safe_out = os.path.join(test_dir, f"{tname}.safe")
            elf_out = os.path.join(test_dir, f"{tname}.elf")
            subprocess.run([sinc_bin, tf, safe_out], check=True)
            subprocess.run([packager_bin, safe_out, elf_out], check=True)
            os.chmod(elf_out, 0o755)
            exit_code = subprocess.run([elf_out]).returncode & 255
            assert exit_code == expected_exit, f"Exit mismatch for {tname}: got {exit_code}, expected {expected_exit}"
            native_meta[tname] = {
                "type": "positive_execution",
                "exit_code": exit_code,
                "safe_sz": os.path.getsize(safe_out),
                "safe_sha": sha256_file(safe_out),
                "elf_sz": os.path.getsize(elf_out),
                "elf_sha": sha256_file(elf_out),
            }
        else:
            raise ValueError(f"Test {tf} missing // EXPECT: or // COMPILE_ERROR:")

    print(f"  Processed {pos_count} positive execution tests and {neg_count} negative rejection tests.")

    # 4. Bug Tests (4 Verified Regressions)
    print("[4/5] Locking Bug Verification Suite (4 Historical Regressions)...")
    bug_meta = {}

    # Bug 1: Loop Syntax Error tape corruption
    b1_src = "fn main() [\n    loop (i = 0 .. 10) [\n        if (i % 4 == 0) [\n            ret 1;\n        ]\n    ]\n    ret 0;\n]"
    b1_path = os.path.join(bug_dir, "bug1_loop_syntax_err.sinc")
    with open(b1_path, "w") as f: f.write(b1_src + "\n")
    res1 = subprocess.run([sinc_bin, b1_path, "/tmp/bug1.safe"], capture_output=True)
    bug_meta["bug1_loop_syntax_err"] = {
        "type": "compiler_rejection",
        "expected_exit": 7,
        "actual_exit": res1.returncode,
        "sha256": sha256_file(b1_path)
    }

    # Bug 2: CLI Driver Nonexistent FD Bypass
    res2 = subprocess.run([sinc_bin, "/tmp/definitely_nonexistent_sinc_file_99999.sinc", "/tmp/nonexistent.safe"], capture_output=True)
    bug_meta["bug2_nonexistent_fd"] = {
        "type": "cli_driver_error",
        "expected_exit": 2,
        "actual_exit": res2.returncode,
    }

    # Bug 3: SAR Negative Right Shift
    b3_src = "fn main() [\n    val = -100;\n    shifted = val >> 2;\n    if (shifted == -25) [\n        ret 42;\n    ]\n    ret 99;\n]"
    b3_path = os.path.join(bug_dir, "bug3_sar_negative.sinc")
    b3_safe = os.path.join(bug_dir, "bug3_sar_negative.safe")
    b3_elf = os.path.join(bug_dir, "bug3_sar_negative.elf")
    with open(b3_path, "w") as f: f.write(b3_src + "\n")
    subprocess.run([sinc_bin, b3_path, b3_safe], check=True)
    subprocess.run([packager_bin, b3_safe, b3_elf], check=True)
    os.chmod(b3_elf, 0o755)
    exit3 = subprocess.run([b3_elf]).returncode & 255
    assert exit3 == 42
    bug_meta["bug3_sar_negative"] = {
        "type": "runtime_execution",
        "expected_exit": 42,
        "actual_exit": exit3,
        "safe_sz": os.path.getsize(b3_safe),
        "safe_sha": sha256_file(b3_safe),
        "elf_sz": os.path.getsize(b3_elf),
        "elf_sha": sha256_file(b3_elf),
    }

    # Bug 4: BMI variable SAR shift
    b4_src = "fn test_variable_sar(val, amt) [\n    ret val >> amt;\n]\n\nfn main() [\n    z = -100;\n    t3 = test_variable_sar(z, 2);\n    if (t3 == -25) [\n        ret 10;\n    ]\n    ret 90;\n]"
    b4_path = os.path.join(bug_dir, "bug4_bmi_sar_variable.sinc")
    b4_safe = os.path.join(bug_dir, "bug4_bmi_sar_variable.safe")
    b4_elf = os.path.join(bug_dir, "bug4_bmi_sar_variable.elf")
    with open(b4_path, "w") as f: f.write(b4_src + "\n")
    subprocess.run([sinc_bin, b4_path, b4_safe], check=True)
    subprocess.run([packager_bin, b4_safe, b4_elf], check=True)
    os.chmod(b4_elf, 0o755)
    exit4 = subprocess.run([b4_elf]).returncode & 255
    assert exit4 == 10
    bug_meta["bug4_bmi_sar_variable"] = {
        "type": "runtime_execution",
        "expected_exit": 10,
        "actual_exit": exit4,
        "safe_sz": os.path.getsize(b4_safe),
        "safe_sha": sha256_file(b4_safe),
        "elf_sz": os.path.getsize(b4_elf),
        "elf_sha": sha256_file(b4_elf),
    }

    # 5. FFI Integration Tests (5 Cases)
    print("[5/5] Locking C FFI Integration Test Suite (5 Object Link Cases)...")
    ffi_meta = {}

    # Case 1: Fib
    c1_sinc = "fn fib_fast() [\n    a = 0;\n    b = 1;\n    loop (i:100 = 0 .. 40) [\n        tmp = a + b;\n        a = b;\n        b = tmp;\n    ]\n    ret a;\n]"
    c1_harness = "#include <stdio.h>\n#include <stdint.h>\n#include <assert.h>\nextern int64_t sinc_fib(void);\nint main(void) {\n    int64_t val = sinc_fib();\n    assert(val == 102334155LL);\n    return 0;\n}"
    c1_sinc_path = os.path.join(ffi_dir, "kernel_fib.sinc")
    c1_safe_path = os.path.join(ffi_dir, "kernel_fib.safe")
    c1_o_path = os.path.join(ffi_dir, "kernel_fib.o")
    c1_c_path = os.path.join(ffi_dir, "harness_fib.c")
    with open(c1_sinc_path, "w") as f: f.write(c1_sinc + "\n")
    with open(c1_c_path, "w") as f: f.write(c1_harness + "\n")
    subprocess.run([sinc_bin, c1_sinc_path, c1_safe_path], check=True)
    subprocess.run([packager_o, c1_safe_path, c1_o_path, "sinc_fib"], check=True)
    subprocess.run(["gcc", "-O3", c1_c_path, c1_o_path, "-no-pie", "-o", "/tmp/ffi_app1"], check=True)
    subprocess.run(["/tmp/ffi_app1"], check=True)
    ffi_meta["test1_fib_scalar"] = {
        "symbol": "sinc_fib",
        "expected_value": 102334155,
        "safe_sz": os.path.getsize(c1_safe_path),
        "safe_sha": sha256_file(c1_safe_path),
        "o_sz": os.path.getsize(c1_o_path),
        "o_sha": sha256_file(c1_o_path),
    }

    # Case 2: Poly3
    c2_sinc = "fn poly3(a, b, c) [\n    ret (a * a) + (b * c) + 42;\n]"
    c2_harness = """#include <stdio.h>
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
    c2_sinc_path = os.path.join(ffi_dir, "kernel_poly.sinc")
    c2_safe_path = os.path.join(ffi_dir, "kernel_poly.safe")
    c2_o_path = os.path.join(ffi_dir, "kernel_poly.o")
    c2_c_path = os.path.join(ffi_dir, "harness_poly.c")
    with open(c2_sinc_path, "w") as f: f.write(c2_sinc + "\n")
    with open(c2_c_path, "w") as f: f.write(c2_harness + "\n")
    subprocess.run([sinc_bin, c2_sinc_path, c2_safe_path], check=True)
    subprocess.run([packager_o, c2_safe_path, c2_o_path, "sinc_poly3"], check=True)
    subprocess.run(["gcc", "-O3", c2_c_path, c2_o_path, "-no-pie", "-o", "/tmp/ffi_app2"], check=True)
    subprocess.run(["/tmp/ffi_app2"], check=True)
    ffi_meta["test2_poly3_spine_abi"] = {
        "symbol": "sinc_poly3",
        "expected_value": 742,
        "safe_sz": os.path.getsize(c2_safe_path),
        "safe_sha": sha256_file(c2_safe_path),
        "o_sz": os.path.getsize(c2_o_path),
        "o_sha": sha256_file(c2_o_path),
    }

    # Case 3: In-Place Large Array Mutation
    c3_sinc = "fn transform_array!(buf, len, multiplier) [\n    loop (i:10000000 = 0 .. len) [\n        buf@[i] = buf@[i] * multiplier;\n    ]\n    ret len;\n]"
    c3_harness = """#include <stdio.h>
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
    c3_sinc_path = os.path.join(ffi_dir, "kernel_array.sinc")
    c3_safe_path = os.path.join(ffi_dir, "kernel_array.safe")
    c3_o_path = os.path.join(ffi_dir, "kernel_array.o")
    c3_c_path = os.path.join(ffi_dir, "harness_array.c")
    with open(c3_sinc_path, "w") as f: f.write(c3_sinc + "\n")
    with open(c3_c_path, "w") as f: f.write(c3_harness + "\n")
    subprocess.run([sinc_bin, c3_sinc_path, c3_safe_path], check=True)
    subprocess.run([packager_o, c3_safe_path, c3_o_path, "sinc_transform_array"], check=True)
    subprocess.run(["gcc", "-O3", c3_c_path, c3_o_path, "-no-pie", "-o", "/tmp/ffi_app3"], check=True)
    subprocess.run(["/tmp/ffi_app3"], check=True)
    ffi_meta["test3_transform_array_mutation"] = {
        "symbol": "sinc_transform_array",
        "expected_elements": 1000000,
        "safe_sz": os.path.getsize(c3_safe_path),
        "safe_sha": sha256_file(c3_safe_path),
        "o_sz": os.path.getsize(c3_o_path),
        "o_sha": sha256_file(c3_o_path),
    }

    # Case 4: Multi-Object Linking
    c4_a_sinc = "fn compute_a(x) [\n    ret x * 3;\n]"
    c4_b_sinc = "fn compute_b(x) [\n    ret x + 100;\n]"
    c4_harness = """#include <stdio.h>
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
    c4_a_sinc_path = os.path.join(ffi_dir, "mod_a.sinc")
    c4_a_safe_path = os.path.join(ffi_dir, "mod_a.safe")
    c4_a_o_path = os.path.join(ffi_dir, "mod_a.o")
    c4_b_sinc_path = os.path.join(ffi_dir, "mod_b.sinc")
    c4_b_safe_path = os.path.join(ffi_dir, "mod_b.safe")
    c4_b_o_path = os.path.join(ffi_dir, "mod_b.o")
    c4_c_path = os.path.join(ffi_dir, "harness_multi.c")
    with open(c4_a_sinc_path, "w") as f: f.write(c4_a_sinc + "\n")
    with open(c4_b_sinc_path, "w") as f: f.write(c4_b_sinc + "\n")
    with open(c4_c_path, "w") as f: f.write(c4_harness + "\n")
    subprocess.run([sinc_bin, c4_a_sinc_path, c4_a_safe_path], check=True)
    subprocess.run([packager_o, c4_a_safe_path, c4_a_o_path, "sinc_compute_a"], check=True)
    subprocess.run([sinc_bin, c4_b_sinc_path, c4_b_safe_path], check=True)
    subprocess.run([packager_o, c4_b_safe_path, c4_b_o_path, "sinc_compute_b"], check=True)
    subprocess.run(["gcc", "-O3", c4_c_path, c4_a_o_path, c4_b_o_path, "-no-pie", "-o", "/tmp/ffi_app4"], check=True)
    subprocess.run(["/tmp/ffi_app4"], check=True)
    ffi_meta["test4_multi_object_linking"] = {
        "symbol_a": "sinc_compute_a",
        "symbol_b": "sinc_compute_b",
        "expected_value": 175,
        "mod_a_safe_sha": sha256_file(c4_a_safe_path),
        "mod_a_o_sha": sha256_file(c4_a_o_path),
        "mod_b_safe_sha": sha256_file(c4_b_safe_path),
        "mod_b_o_sha": sha256_file(c4_b_o_path),
    }

    # Case 5: Complex AVX-512 Vectorized Loop
    c5_src_path = os.path.join(ROOT_DIR, "tests", "native", "avx512_eight_lane_reduction.sinc")
    c5_safe_path = os.path.join(ffi_dir, "kernel_vec.safe")
    c5_o_path = os.path.join(ffi_dir, "kernel_vec.o")
    c5_harness = "#include <stdio.h>\n#include <stdint.h>\n#include <assert.h>\nextern int64_t sinc_avx512_accum(void);\nint main(void) {\n    int64_t res = sinc_avx512_accum();\n    assert((res & 255) == 144);\n    return 0;\n}"
    c5_c_path = os.path.join(ffi_dir, "harness_vec.c")
    with open(c5_c_path, "w") as f: f.write(c5_harness + "\n")
    subprocess.run([sinc_bin, c5_src_path, c5_safe_path], check=True)
    subprocess.run([packager_o, c5_safe_path, c5_o_path, "sinc_avx512_accum"], check=True)
    subprocess.run(["gcc", "-O3", c5_c_path, c5_o_path, "-no-pie", "-o", "/tmp/ffi_app5"], check=True)
    subprocess.run(["/tmp/ffi_app5"], check=True)
    ffi_meta["test5_avx512_vector_link"] = {
        "symbol": "sinc_avx512_accum",
        "expected_value": 144,
        "safe_sz": os.path.getsize(c5_safe_path),
        "safe_sha": sha256_file(c5_safe_path),
        "o_sz": os.path.getsize(c5_o_path),
        "o_sha": sha256_file(c5_o_path),
    }

    # Master results.json
    master = {
        "commit": commit_hash,
        "commit_short": commit_short,
        "commit_message": commit_msg,
        "seed_compiler": {
            "elf_sha": sha256_file(os.path.join(seed_dir, "sinc.elf")),
            "safe_sha": sha256_file(os.path.join(seed_dir, "sinc.safe")),
            "packager_bin_sha": sha256_file(os.path.join(seed_dir, "packager_bin")),
            "packager_o_sha": sha256_file(os.path.join(seed_dir, "packager_o")),
        },
        "benchmarks_24": bench_meta,
        "native_tests": native_meta,
        "bug_tests": bug_meta,
        "ffi_tests": ffi_meta,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(master, f, indent=2)

    with open(os.path.join(VERIFY_DIR, "commit.txt"), "w") as f:
        f.write(f"Commit: {commit_hash}\nShort: {commit_short}\nMessage: {commit_msg}\n")

    print("\nSUCCESS: Golden Baseline fully built and locked in verify/!")
    return 0

def audit_golden_baseline(sinc_bin, packager_bin, packager_o):
    if not os.path.isfile(RESULTS_PATH):
        print(f"Error: Golden baseline manifest not found at {RESULTS_PATH}", file=sys.stderr)
        print("Run 'python3 tools/verify_golden_parity.py --build' to generate it.", file=sys.stderr)
        return 2

    with open(RESULTS_PATH, "r") as f:
        master = json.load(f)

    baseline_commit = master.get("commit_short", "Unknown")
    baseline_msg = master.get("commit_message", "")

    print("=" * 105)
    print(f"SINC COMPREHENSIVE GOLDEN VERIFICATION SUITE: CURRENT vs BASELINE ({baseline_commit})")
    print(f"Baseline Commit : {master.get('commit')} ({baseline_msg})")
    print(f"Current Compiler: {sinc_bin} ({os.path.getsize(sinc_bin):,} bytes)")
    print("=" * 105)

    total_checks = 0
    passed_checks = 0
    drifts = []

    def record(name, category, ok, detail=""):
        nonlocal total_checks, passed_checks
        total_checks += 1
        if ok:
            passed_checks += 1
        else:
            drifts.append((category, name, detail))

    work_dir = tempfile.mkdtemp(prefix="sinc_verify_")

    try:
        # Tier 1: Compiler Self-Hosting Determinism
        print("\n[TIER 1] Compiler Self-Hosting Bitwise Determinism")
        print("-" * 105)
        assembled_src = os.path.join(work_dir, "compiler_assembled.sinc")
        self_safe = os.path.join(work_dir, "sinc_self.safe")
        subprocess.run([os.path.join(ROOT_DIR, "build.sh"), "--assemble-only", assembled_src], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res_self = subprocess.run([sinc_bin, assembled_src, self_safe], capture_output=True)

        if res_self.returncode != 0:
            print(f"  Self-hosting compilation failed (exit code {res_self.returncode})")
            record("Self-Hosting", "Compiler", False, f"Compile failed exit {res_self.returncode}")
        else:
            curr_self_sha = sha256_file(self_safe)
            base_self_sha = master["seed_compiler"]["safe_sha"]
            match_self = (curr_self_sha == base_self_sha)
            record("Self-Hosting Bytecode", "Compiler", match_self, f"{curr_self_sha[:10]} vs {base_self_sha[:10]}")
            status = "MATCH" if match_self else "DIFF"
            print(f"  {'Self-Hosted sinc.safe':<32} | {status:<8} | SHA: {curr_self_sha[:12]}... (Base: {base_self_sha[:12]}...)")

        # Tier 2: 24 Full Optimization Benchmarks
        print("\n[TIER 2] 24 Optimization Benchmarks (Bitwise Safe/ELF & Exit Code Parity)")
        print("-" * 105)
        hdr_bench = f"{'Benchmark':<24} | {'Safe Match':<10} | {'ELF Match':<10} | {'Exit Match':<10} | {'Exit (Curr/Base)':<17} | {'Status'}"
        print(hdr_bench)
        print("-" * 105)

        bench_data = master.get("benchmarks_24", {})
        bench_safe_matches = 0
        bench_elf_matches = 0
        bench_exit_matches = 0
        bench_identical_count = 0
        bench_changed_count = 0
        bench_changed_list = []

        for bname, base_info in sorted(bench_data.items()):
            src = os.path.join(ROOT_DIR, "bench", f"{bname}.sinc")
            b_safe = os.path.join(work_dir, f"{bname}.safe")
            b_elf = os.path.join(work_dir, f"{bname}.elf")

            r1 = subprocess.run([sinc_bin, src, b_safe], capture_output=True)
            if r1.returncode != 0:
                print(f"{bname:<24} | COMPILE FAIL")
                record(bname, "Benchmarks", False, "Compilation failed")
                bench_changed_count += 1
                bench_changed_list.append(bname)
                continue

            r2 = subprocess.run([packager_bin, b_safe, b_elf], capture_output=True)
            if r2.returncode != 0:
                print(f"{bname:<24} | PACKAGE FAIL")
                record(bname, "Benchmarks", False, "Packaging failed")
                bench_changed_count += 1
                bench_changed_list.append(bname)
                continue

            os.chmod(b_elf, 0o755)
            run_res = subprocess.run([b_elf])
            exit_code = run_res.returncode & 255

            safe_sha = sha256_file(b_safe)
            elf_sha = sha256_file(b_elf)

            safe_match = (safe_sha == base_info["safe_sha"])
            elf_match = (elf_sha == base_info["elf_sha"])
            exit_match = (exit_code == base_info["exit_code"])
            is_identical = safe_match and elf_match and exit_match

            if safe_match: bench_safe_matches += 1
            if elf_match: bench_elf_matches += 1
            if exit_match: bench_exit_matches += 1
            if is_identical:
                bench_identical_count += 1
            else:
                bench_changed_count += 1
                bench_changed_list.append(bname)

            record(f"{bname} safe_sha", "Benchmarks", safe_match, f"{safe_sha[:8]} vs {base_info['safe_sha'][:8]}")
            record(f"{bname} elf_sha", "Benchmarks", elf_match, f"{elf_sha[:8]} vs {base_info['elf_sha'][:8]}")
            record(f"{bname} exit", "Benchmarks", exit_match, f"exit {exit_code} vs {base_info['exit_code']}")

            safe_str = "MATCH" if safe_match else "DIFF"
            elf_str = "MATCH" if elf_match else "DIFF"
            exit_str = "MATCH" if exit_match else "DIFF"
            exit_val_str = f"{exit_code} / {base_info['exit_code']}" if exit_code != base_info['exit_code'] else f"{exit_code}"
            status_str = "IDENTICAL" if is_identical else "CHANGED"
            print(f"{bname:<24} | {safe_str:<10} | {elf_str:<10} | {exit_str:<10} | {exit_val_str:<17} | {status_str}")

        print(f"\n  Benchmark Audit: Total Identical={bench_identical_count}/24, Total Changed={bench_changed_count}/24")
        print(f"  Component Parity: Safe={bench_safe_matches}/24, ELF={bench_elf_matches}/24, Exit={bench_exit_matches}/24")
        if bench_changed_list:
            print(f"  Changed Benchmarks: {bench_changed_list}")

        # Tier 3: 103 Native Test Suite
        print("\n[TIER 3] 103 Native Test Suite (92 Execution + 11 Negative Rejections)")
        print("-" * 105)
        native_data = master.get("native_tests", {})
        t_safe_matches = 0
        t_elf_matches = 0
        t_exit_matches = 0
        t_rej_matches = 0

        for tname, base_info in sorted(native_data.items()):
            src = os.path.join(ROOT_DIR, "tests", "native", f"{tname}.sinc")
            if base_info["type"] == "negative_rejection":
                out_safe = os.path.join(work_dir, f"{tname}_neg.safe")
                res = subprocess.run([sinc_bin, src, out_safe], capture_output=True)
                rej_match = (res.returncode == base_info["compile_error"])
                if rej_match: t_rej_matches += 1
                record(f"{tname} rejection", "Native Tests", rej_match, f"exit {res.returncode} vs {base_info['compile_error']}")
            else:
                t_safe = os.path.join(work_dir, f"{tname}.safe")
                t_elf = os.path.join(work_dir, f"{tname}.elf")
                r1 = subprocess.run([sinc_bin, src, t_safe], capture_output=True)
                if r1.returncode != 0:
                    record(tname, "Native Tests", False, "Compilation failed")
                    continue
                r2 = subprocess.run([packager_bin, t_safe, t_elf], capture_output=True)
                if r2.returncode != 0:
                    record(tname, "Native Tests", False, "Packaging failed")
                    continue
                os.chmod(t_elf, 0o755)
                r_run = subprocess.run([t_elf])
                exit_code = r_run.returncode & 255

                safe_sha = sha256_file(t_safe)
                elf_sha = sha256_file(t_elf)

                safe_match = (safe_sha == base_info["safe_sha"])
                elf_match = (elf_sha == base_info["elf_sha"])
                exit_match = (exit_code == base_info["exit_code"])

                if safe_match: t_safe_matches += 1
                if elf_match: t_elf_matches += 1
                if exit_match: t_exit_matches += 1

                record(f"{tname} safe_sha", "Native Tests", safe_match, f"{safe_sha[:8]} vs {base_info['safe_sha'][:8]}")
                record(f"{tname} elf_sha", "Native Tests", elf_match, f"{elf_sha[:8]} vs {base_info['elf_sha'][:8]}")
                record(f"{tname} exit", "Native Tests", exit_match, f"exit {exit_code} vs {base_info['exit_code']}")

        print(f"  Positive Execution Tests: Safe={t_safe_matches}/92, ELF={t_elf_matches}/92, Exit={t_exit_matches}/92")
        print(f"  Negative Rejection Tests: Rejection Exit Codes={t_rej_matches}/11")

        # Tier 4: 4 Bug Regression Suite
        print("\n[TIER 4] 4 Bug & Vulnerability Regressions")
        print("-" * 105)
        bug_data = master.get("bug_tests", {})

        b1_src = os.path.join(VERIFY_DIR, "bug_tests", "bug1_loop_syntax_err.sinc")
        r_b1 = subprocess.run([sinc_bin, b1_src, os.path.join(work_dir, "b1.safe")], capture_output=True)
        b1_ok = (r_b1.returncode == bug_data["bug1_loop_syntax_err"]["expected_exit"])
        record("Bug 1: Loop Syntax Error Code", "Bug Tests", b1_ok, f"exit {r_b1.returncode} vs 7")
        print(f"  [Bug 1] Loop Syntax Error-Code Mutation Guard : {'PASS' if b1_ok else 'FAIL'} (exit {r_b1.returncode})")

        r_b2 = subprocess.run([sinc_bin, "/tmp/nonexistent_file_99999.sinc", os.path.join(work_dir, "b2.safe")], capture_output=True)
        b2_ok = (r_b2.returncode == bug_data["bug2_nonexistent_fd"]["expected_exit"])
        record("Bug 2: CLI Driver Nonexistent FD Bypass", "Bug Tests", b2_ok, f"exit {r_b2.returncode} vs 2")
        print(f"  [Bug 2] CLI Driver Nonexistent FD Bypass Guard: {'PASS' if b2_ok else 'FAIL'} (exit {r_b2.returncode})")

        b3_src = os.path.join(VERIFY_DIR, "bug_tests", "bug3_sar_negative.sinc")
        b3_safe = os.path.join(work_dir, "b3.safe")
        b3_elf = os.path.join(work_dir, "b3.elf")
        subprocess.run([sinc_bin, b3_src, b3_safe], check=True, capture_output=True)
        subprocess.run([packager_bin, b3_safe, b3_elf], check=True, capture_output=True)
        os.chmod(b3_elf, 0o755)
        r_b3 = subprocess.run([b3_elf])
        b3_exit = r_b3.returncode & 255
        b3_safe_match = (sha256_file(b3_safe) == bug_data["bug3_sar_negative"]["safe_sha"])
        b3_ok = (b3_exit == 42 and b3_safe_match)
        record("Bug 3: Negative SAR Arithmetic Shift", "Bug Tests", b3_ok, f"exit {b3_exit} safe_match={b3_safe_match}")
        print(f"  [Bug 3] Arithmetic Right Shift (SAR) on Negatives: {'PASS' if b3_ok else 'FAIL'} (exit {b3_exit}, Safe Match: {b3_safe_match})")

        b4_src = os.path.join(VERIFY_DIR, "bug_tests", "bug4_bmi_sar_variable.sinc")
        b4_safe = os.path.join(work_dir, "b4.safe")
        b4_elf = os.path.join(work_dir, "b4.elf")
        subprocess.run([sinc_bin, b4_src, b4_safe], check=True, capture_output=True)
        subprocess.run([packager_bin, b4_safe, b4_elf], check=True, capture_output=True)
        os.chmod(b4_elf, 0o755)
        r_b4 = subprocess.run([b4_elf])
        b4_exit = r_b4.returncode & 255
        b4_safe_match = (sha256_file(b4_safe) == bug_data["bug4_bmi_sar_variable"]["safe_sha"])
        b4_ok = (b4_exit == 10 and b4_safe_match)
        record("Bug 4: BMI Variable SAR Asserted Shift", "Bug Tests", b4_ok, f"exit {b4_exit} safe_match={b4_safe_match}")
        print(f"  [Bug 4] BMI Variable SAR Assertion Integrity   : {'PASS' if b4_ok else 'FAIL'} (exit {b4_exit}, Safe Match: {b4_safe_match})")

        # Tier 5: 5 C FFI & ELF .o Integration
        print("\n[TIER 5] 5 C FFI & ELF .o Integration Tests")
        print("-" * 105)
        ffi_data = master.get("ffi_tests", {})

        # Case 1: Fib
        c1_sinc = os.path.join(VERIFY_DIR, "ffi_tests", "kernel_fib.sinc")
        c1_safe = os.path.join(work_dir, "c1.safe")
        c1_o = os.path.join(work_dir, "c1.o")
        c1_harness = os.path.join(VERIFY_DIR, "ffi_tests", "harness_fib.c")
        c1_app = os.path.join(work_dir, "c1_app")
        subprocess.run([sinc_bin, c1_sinc, c1_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c1_safe, c1_o, "sinc_fib"], check=True, capture_output=True)
        subprocess.run(["gcc", "-O3", c1_harness, c1_o, "-no-pie", "-o", c1_app], check=True, capture_output=True)
        r_c1 = subprocess.run([c1_app])
        c1_safe_match = (sha256_file(c1_safe) == ffi_data["test1_fib_scalar"]["safe_sha"])
        c1_o_match = (sha256_file(c1_o) == ffi_data["test1_fib_scalar"]["o_sha"])
        c1_ok = (r_c1.returncode == 0 and c1_safe_match and c1_o_match)
        record("FFI 1: Zero-Arg Scalar ABI", "FFI Tests", c1_ok, f"exit {r_c1.returncode}")
        print(f"  [FFI 1] Zero-Arg Scalar ABI (sinc_fib)          : {'PASS' if c1_ok else 'FAIL'} (Safe: {c1_safe_match}, .o: {c1_o_match})")

        # Case 2: Poly3
        c2_sinc = os.path.join(VERIFY_DIR, "ffi_tests", "kernel_poly.sinc")
        c2_safe = os.path.join(work_dir, "c2.safe")
        c2_o = os.path.join(work_dir, "c2.o")
        c2_harness = os.path.join(VERIFY_DIR, "ffi_tests", "harness_poly.c")
        c2_app = os.path.join(work_dir, "c2_app")
        subprocess.run([sinc_bin, c2_sinc, c2_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c2_safe, c2_o, "sinc_poly3"], check=True, capture_output=True)
        subprocess.run(["gcc", "-O3", c2_harness, c2_o, "-no-pie", "-o", c2_app], check=True, capture_output=True)
        r_c2 = subprocess.run([c2_app])
        c2_safe_match = (sha256_file(c2_safe) == ffi_data["test2_poly3_spine_abi"]["safe_sha"])
        c2_o_match = (sha256_file(c2_o) == ffi_data["test2_poly3_spine_abi"]["o_sha"])
        c2_ok = (r_c2.returncode == 0 and c2_safe_match and c2_o_match)
        record("FFI 2: Multi-Arg SPINE ABI", "FFI Tests", c2_ok, f"exit {r_c2.returncode}")
        print(f"  [FFI 2] Multi-Arg SPINE ABI (sinc_poly3)        : {'PASS' if c2_ok else 'FAIL'} (Safe: {c2_safe_match}, .o: {c2_o_match})")

        # Case 3: In-Place Array Mutation
        c3_sinc = os.path.join(VERIFY_DIR, "ffi_tests", "kernel_array.sinc")
        c3_safe = os.path.join(work_dir, "c3.safe")
        c3_o = os.path.join(work_dir, "c3.o")
        c3_harness = os.path.join(VERIFY_DIR, "ffi_tests", "harness_array.c")
        c3_app = os.path.join(work_dir, "c3_app")
        subprocess.run([sinc_bin, c3_sinc, c3_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c3_safe, c3_o, "sinc_transform_array"], check=True, capture_output=True)
        subprocess.run(["gcc", "-O3", c3_harness, c3_o, "-no-pie", "-o", c3_app], check=True, capture_output=True)
        r_c3 = subprocess.run([c3_app])
        c3_safe_match = (sha256_file(c3_safe) == ffi_data["test3_transform_array_mutation"]["safe_sha"])
        c3_o_match = (sha256_file(c3_o) == ffi_data["test3_transform_array_mutation"]["o_sha"])
        c3_ok = (r_c3.returncode == 0 and c3_safe_match and c3_o_match)
        record("FFI 3: In-Place Array Mutation", "FFI Tests", c3_ok, f"exit {r_c3.returncode}")
        print(f"  [FFI 3] In-Place Array Mutation (1,000,000 elem): {'PASS' if c3_ok else 'FAIL'} (Safe: {c3_safe_match}, .o: {c3_o_match})")

        # Case 4: Multi-Object Linking
        c4_a_sinc = os.path.join(VERIFY_DIR, "ffi_tests", "mod_a.sinc")
        c4_a_safe = os.path.join(work_dir, "c4_a.safe")
        c4_a_o = os.path.join(work_dir, "c4_a.o")
        c4_b_sinc = os.path.join(VERIFY_DIR, "ffi_tests", "mod_b.sinc")
        c4_b_safe = os.path.join(work_dir, "c4_b.safe")
        c4_b_o = os.path.join(work_dir, "c4_b.o")
        c4_harness = os.path.join(VERIFY_DIR, "ffi_tests", "harness_multi.c")
        c4_app = os.path.join(work_dir, "c4_app")
        subprocess.run([sinc_bin, c4_a_sinc, c4_a_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c4_a_safe, c4_a_o, "sinc_compute_a"], check=True, capture_output=True)
        subprocess.run([sinc_bin, c4_b_sinc, c4_b_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c4_b_safe, c4_b_o, "sinc_compute_b"], check=True, capture_output=True)
        subprocess.run(["gcc", "-O3", c4_harness, c4_a_o, c4_b_o, "-no-pie", "-o", c4_app], check=True, capture_output=True)
        r_c4 = subprocess.run([c4_app])
        c4_a_safe_match = (sha256_file(c4_a_safe) == ffi_data["test4_multi_object_linking"]["mod_a_safe_sha"])
        c4_a_o_match = (sha256_file(c4_a_o) == ffi_data["test4_multi_object_linking"]["mod_a_o_sha"])
        c4_b_safe_match = (sha256_file(c4_b_safe) == ffi_data["test4_multi_object_linking"]["mod_b_safe_sha"])
        c4_b_o_match = (sha256_file(c4_b_o) == ffi_data["test4_multi_object_linking"]["mod_b_o_sha"])
        c4_ok = (r_c4.returncode == 0 and c4_a_safe_match and c4_a_o_match and c4_b_safe_match and c4_b_o_match)
        record("FFI 4: Multi-Object Linking", "FFI Tests", c4_ok, f"exit {r_c4.returncode}")
        print(f"  [FFI 4] Multi-Object SINC Linking (mod_a+mod_b) : {'PASS' if c4_ok else 'FAIL'} (Safe: {c4_a_safe_match and c4_b_safe_match}, .o: {c4_a_o_match and c4_b_o_match})")

        # Case 5: AVX-512 Vector Kernel
        c5_sinc = os.path.join(ROOT_DIR, "tests", "native", "avx512_eight_lane_reduction.sinc")
        c5_safe = os.path.join(work_dir, "c5.safe")
        c5_o = os.path.join(work_dir, "c5.o")
        c5_harness = os.path.join(VERIFY_DIR, "ffi_tests", "harness_vec.c")
        c5_app = os.path.join(work_dir, "c5_app")
        subprocess.run([sinc_bin, c5_sinc, c5_safe], check=True, capture_output=True)
        subprocess.run([packager_o, c5_safe, c5_o, "sinc_avx512_accum"], check=True, capture_output=True)
        subprocess.run(["gcc", "-O3", c5_harness, c5_o, "-no-pie", "-o", c5_app], check=True, capture_output=True)
        r_c5 = subprocess.run([c5_app])
        c5_safe_match = (sha256_file(c5_safe) == ffi_data["test5_avx512_vector_link"]["safe_sha"])
        c5_o_match = (sha256_file(c5_o) == ffi_data["test5_avx512_vector_link"]["o_sha"])
        c5_ok = (r_c5.returncode == 0 and c5_safe_match and c5_o_match)
        record("FFI 5: AVX-512 Vector Linking", "FFI Tests", c5_ok, f"exit {r_c5.returncode}")
        print(f"  [FFI 5] AVX-512 Vector Auto-Reduction to C      : {'PASS' if c5_ok else 'FAIL'} (Safe: {c5_safe_match}, .o: {c5_o_match})")

    finally:
        subprocess.run(["rm", "-rf", work_dir])

    print("\n" + "=" * 105)
    print(f"GOLDEN BASELINE INTEGRITY AUDIT SUMMARY (BASELINE: {baseline_commit}):")
    print(f"  Total Invariants Verified: {passed_checks}/{total_checks}")

    if len(drifts) == 0:
        print("\nSTATUS: 100% BITWISE & FUNCTIONAL PARITY WITH GOLDEN BASELINE!")
        print("ALL 5 TIERS (COMPILER SEED, 24 BENCHES, 103 TESTS, 4 BUGS, 5 FFI) VERIFIED ZERO REGRESSIONS.")
        print("=" * 105)
        return 0
    else:
        print(f"\nALERT: {len(drifts)} BEHAVIORAL OR BITWISE DRIFTS DETECTED!")
        print("-" * 105)
        for cat, item, detail in drifts:
            print(f"  ! [{cat}] {item} -> {detail}")
        print("=" * 105)
        return 1

if __name__ == "__main__":
    is_build = "--build" in sys.argv or "--update" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    def find_bin(name):
        bin_path = os.path.join(ROOT_DIR, "bin", name)
        if os.path.isfile(bin_path):
            return bin_path
        return os.path.join(ROOT_DIR, name)

    sinc_bin = os.path.abspath(args[0]) if len(args) > 0 else find_bin("sinc.elf")
    packager_bin = os.path.abspath(args[1]) if len(args) > 1 else find_bin("packager_bin")
    packager_o = find_bin("packager_o")

    if is_build:
        sys.exit(build_golden_baseline(sinc_bin, packager_bin, packager_o))
    else:
        sys.exit(audit_golden_baseline(sinc_bin, packager_bin, packager_o))
