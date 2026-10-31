#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
import random

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def find_bin(name):
    bin_path = os.path.join(ROOT_DIR, "bin", name)
    if os.path.isfile(bin_path):
        return bin_path
    return os.path.join(ROOT_DIR, name)

SINC_BIN = find_bin("sinc.elf")
PACKAGER_BIN = find_bin("packager_bin")

if not os.path.isfile(SINC_BIN) or not os.path.isfile(PACKAGER_BIN):
    print("Error: sinc.elf or packager_bin missing.", file=sys.stderr)
    sys.exit(1)

# Expressions to test differentially against GCC
# All variables a, b, c, d, e, f, g will be provided dynamically via runtime helpers.
STRUCTURED_EXPRESSIONS = [
    # Basic operator precedence
    "a + b * c",
    "(a + b) * c",
    "a * b + c * d",
    "a - b - c - d",
    "(a - b) - (c - d)",
    "a * b / c + d",
    "a + b / c * d",
    
    # Shifts and arithmetic
    "a << (b + c)",
    "(a << b) + c",
    "a >> (b & 3)",
    "(a + b) >> c",
    
    # Bitwise operators
    "a | b & c",
    "(a | b) & c",
    "a ^ b | c & d",
    "(a ^ b) | (c & d)",
    "a & b ^ c | d",
    
    # Deep compound expressions
    "((a * b + c) >> 2) ^ (d + e * f)",
    "(a & 15) * (b & 7) + (c & 31)",
    "(a + b + c + d + e) & 255",
    "((a << 3) + (b << 2) + c) / d",
    "((a ^ b) + (c & d)) - ((e | f) / g)",
    "(a * b - c * d) + (e * f - g)",
    "((a + b) * (c + d)) / ((e + f) | 1)",
    "(a & b) | (c ^ d) + (e >> 1)",
    "a * a + b * b + c * c",
    "(a - b) * (c - d) + (e - f) * g",
    "((a | b) & (c | d)) ^ ((e & f) | g)",
    "((a * 3 + b * 5) / (c | 1)) & 255",

    # Negation & Power-of-2 Multiplications
    "-a + b",
    "-(a * b) + c",
    "a * 2 + b * 2",
    "((a * 2) + b) * 2 - c",
    "-(a - b) - (-c)",
    "((a * 2 + b * 4) / ((c | 1) * 2)) & 255",
]

def generate_sinc_source(expr, var_values):
    lines = [
        "fn helper(x) [",
        "    sum = 0;",
        "    loop (i:5 = 0 .. 1) [",
        "        sum = sum + x;",
        "    ]",
        "    ret sum;",
        "]",
        "",
        "fn main() [",
    ]
    for var, val in var_values.items():
        lines.append(f"    {var} = helper({val});")
    lines.append(f"    res = ({expr}) & 255;")
    lines.append("    ret res;")
    lines.append("]")
    return "\n".join(lines) + "\n"

def generate_c_source(expr, var_values):
    lines = [
        "#include <stdint.h>",
        "static volatile int64_t v_helper(int64_t x) { return x; }",
        "int main(void) {",
    ]
    for var, val in var_values.items():
        lines.append(f"    int64_t {var} = v_helper({val});")
    lines.append(f"    int64_t res = ({expr}) & 255;")
    lines.append("    return (int)(res & 255);")
    lines.append("}")
    return "\n".join(lines) + "\n"

def run_differential_test(expr_id, expr, var_values, work_dir):
    sinc_src = generate_sinc_source(expr, var_values)
    c_src = generate_c_source(expr, var_values)

    sinc_path = os.path.join(work_dir, f"test_{expr_id}.sinc")
    safe_path = os.path.join(work_dir, f"test_{expr_id}.safe")
    sinc_elf = os.path.join(work_dir, f"test_{expr_id}_sinc.elf")
    c_path = os.path.join(work_dir, f"test_{expr_id}.c")
    gcc_elf = os.path.join(work_dir, f"test_{expr_id}_gcc.elf")

    with open(sinc_path, "w") as f:
        f.write(sinc_src)
    with open(c_path, "w") as f:
        f.write(c_src)

    # Compile SINC
    res = subprocess.run([SINC_BIN, sinc_path, safe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        return False, f"SINC compilation failed for: {expr}"

    res = subprocess.run([PACKAGER_BIN, safe_path, sinc_elf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        return False, f"Packager failed for: {expr}"

    os.chmod(sinc_elf, 0o755)

    # Compile GCC
    res = subprocess.run(["gcc", "-O2", c_path, "-o", gcc_elf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        return False, f"GCC compilation failed for: {expr}"

    # Execute SINC
    sinc_proc = subprocess.run([sinc_elf])
    sinc_exit = sinc_proc.returncode & 255

    # Execute GCC
    gcc_proc = subprocess.run([gcc_elf])
    gcc_exit = gcc_proc.returncode & 255

    if sinc_exit != gcc_exit:
        return False, f"Mismatch in {expr}: SINC exit={sinc_exit}, GCC exit={gcc_exit} (vars={var_values})"

    return True, f"Match exit={sinc_exit}"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Differential oracle testing: SINC vs GCC")
    parser.add_argument("--random-rounds", type=int, default=20, help="Number of random parameter rounds per expression")
    args = parser.parse_args()

    random.seed(1337)
    total = 0
    passed = 0

    print("Running differential oracle testing (SINC vs GCC)...")
    with tempfile.TemporaryDirectory(prefix="sinc_oracle_") as work_dir:
        for idx, expr in enumerate(STRUCTURED_EXPRESSIONS):
            # Test default small values
            vars_needed = sorted(list(set(c for c in expr if c in "abcdefg")))
            default_vals = {v: (i + 2) for i, v in enumerate(vars_needed)}
            # Ensure non-zero divisors
            for k in default_vals:
                if default_vals[k] == 0:
                    default_vals[k] = 1

            total += 1
            ok, msg = run_differential_test(f"{idx}_base", expr, default_vals, work_dir)
            if ok:
                passed += 1
            else:
                print(f"FAIL: {msg}")
                sys.exit(1)

            # Test randomized values
            for r in range(args.random_rounds):
                rand_vals = {}
                for v in vars_needed:
                    val = random.randint(1, 30)
                    rand_vals[v] = val
                total += 1
                ok, msg = run_differential_test(f"{idx}_rnd_{r}", expr, rand_vals, work_dir)
                if ok:
                    passed += 1
                else:
                    print(f"FAIL: {msg}")
                    sys.exit(1)

    print(f"Differential Oracle: {passed}/{total} tests passed with bitwise GCC parity.")

if __name__ == "__main__":
    main()
