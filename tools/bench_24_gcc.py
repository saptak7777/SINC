#!/usr/bin/env python3
# ==============================================================================
# tools/bench_24_gcc.py
# SINC vs. GCC -O3 24-Workload Performance Comparison Engine
# Supports standard GCC -O3, Profile-Guided Optimization (--pgo), or --both
# ==============================================================================
import os
import sys
import glob
import subprocess
import time
import statistics
import math
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(ROOT_DIR, "bench")
def find_bin(name):
    bin_path = os.path.join(ROOT_DIR, "bin", name)
    if os.path.isfile(bin_path):
        return bin_path
    return os.path.join(ROOT_DIR, name)

SINC_BIN = find_bin("sinc.elf")
PACKAGER_BIN = find_bin("packager_bin")
TMP_DIR = "/tmp/sinc_bench_24"

os.makedirs(TMP_DIR, exist_ok=True)

if not os.path.isfile(SINC_BIN) or not os.path.isfile(PACKAGER_BIN):
    print(f"Error: Missing {SINC_BIN} or {PACKAGER_BIN}", file=sys.stderr)
    sys.exit(1)

available_cpus = os.sched_getaffinity(0) if hasattr(os, "sched_getaffinity") else {0}
target_cpu = "2" if 2 in available_cpus else str(min(available_cpus))
pin_cmd = ["taskset", "-c", target_cpu]

def measure_execution_ms(cmd, runs=5, warmup=1):
    for _ in range(warmup):
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    times = []
    exit_code = 0
    for _ in range(runs):
        t0 = time.perf_counter()
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
        exit_code = res.returncode & 255
    return statistics.median(times), exit_code

def compile_sinc(bname):
    sinc_src = os.path.join(BENCH_DIR, f"{bname}.sinc")
    out_safe = os.path.join(TMP_DIR, f"{bname}.safe")
    out_elf = os.path.join(TMP_DIR, f"{bname}_sinc.elf")
    r1 = subprocess.run([SINC_BIN, sinc_src, out_safe], capture_output=True)
    if r1.returncode != 0:
        return None
    r2 = subprocess.run([PACKAGER_BIN, out_safe, out_elf], capture_output=True)
    if r2.returncode != 0:
        return None
    os.chmod(out_elf, 0o755)
    return out_elf

def compile_gcc(bname, use_pgo=False):
    c_src = os.path.join(BENCH_DIR, f"{bname}.c")
    out_elf = os.path.join(TMP_DIR, f"{bname}_gcc_pgo.elf" if use_pgo else f"{bname}_gcc.elf")
    if not use_pgo:
        cmd = ["gcc", "-O3", "-march=native", "-fno-exceptions", "-fno-rtti", c_src, "-o", out_elf, "-lm"]
        r = subprocess.run(cmd, capture_output=True)
        return out_elf if r.returncode == 0 else None
    else:
        prof_dir = os.path.join(TMP_DIR, f"prof_{bname}")
        shutil.rmtree(prof_dir, ignore_errors=True)
        os.makedirs(prof_dir, exist_ok=True)
        cmd_gen = ["gcc", "-O3", "-march=native", f"-fprofile-generate={prof_dir}", c_src, "-o", out_elf, "-lm"]
        r1 = subprocess.run(cmd_gen, capture_output=True)
        if r1.returncode != 0:
            return None
        # Profile run
        subprocess.run(pin_cmd + [out_elf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd_use = ["gcc", "-O3", "-march=native", f"-fprofile-use={prof_dir}", "-fprofile-correction", c_src, "-o", out_elf, "-lm"]
        r2 = subprocess.run(cmd_use, capture_output=True)
        return out_elf if r2.returncode == 0 else None

def run_suite(mode="standard"):
    # mode: 'standard', 'pgo', or 'both'
    benchmarks = sorted([os.path.basename(f)[:-5] for f in glob.glob(os.path.join(BENCH_DIR, "*.sinc"))])
    print("=" * 115)
    mode_name = "GCC -O3 + PGO (Profile-Guided Optimization)" if mode == "pgo" else ("GCC -O3 Standard vs. PGO vs. SINC" if mode == "both" else "GCC -O3 Standard")
    print(f"SINC 24-BENCHMARK PERFORMANCE ENGINE vs. {mode_name} (Core {target_cpu})")
    print("=" * 115)

    if mode == "both":
        hdr = f"{'Benchmark':<24} | {'SINC (ms)':>10} | {'GCC (ms)':>10} | {'Ratio':>7} | {'PGO (ms)':>10} | {'PGO Ratio':>9} | {'Status'}"
    else:
        hdr = f"{'Benchmark':<24} | {'SINC (ms)':>10} | {'GCC (ms)':>10} | {'Ratio':>7} | {'SINC Speedup':>12} | {'Exit Match'}"
    print(hdr)
    print("-" * 115)

    ratios_std = []
    ratios_pgo = []

    for bname in benchmarks:
        sinc_elf = compile_sinc(bname)
        if not sinc_elf:
            print(f"{bname:<24} | SINC COMPILE FAIL")
            continue
        sinc_time, sinc_exit = measure_execution_ms(pin_cmd + [sinc_elf])

        gcc_elf_std = compile_gcc(bname, use_pgo=False)
        if not gcc_elf_std:
            print(f"{bname:<24} | GCC COMPILE FAIL")
            continue
        gcc_time_std, gcc_exit_std = measure_execution_ms(pin_cmd + [gcc_elf_std])

        ratio_std = sinc_time / gcc_time_std if gcc_time_std > 0 else 1.0
        ratios_std.append(ratio_std)

        if mode == "both":
            gcc_elf_pgo = compile_gcc(bname, use_pgo=True)
            gcc_time_pgo, gcc_exit_pgo = measure_execution_ms(pin_cmd + [gcc_elf_pgo])
            ratio_pgo = sinc_time / gcc_time_pgo if gcc_time_pgo > 0 else 1.0
            ratios_pgo.append(ratio_pgo)
            exit_ok = (sinc_exit == gcc_exit_std == gcc_exit_pgo)
            stat = "MATCH" if exit_ok else f"ERR({sinc_exit}!={gcc_exit_std})"
            print(f"{bname:<24} | {sinc_time:>10.2f} | {gcc_time_std:>10.2f} | {ratio_std:>6.2f}x | {gcc_time_pgo:>10.2f} | {ratio_pgo:>8.2f}x | {stat}")
        elif mode == "pgo":
            gcc_elf_pgo = compile_gcc(bname, use_pgo=True)
            gcc_time_pgo, gcc_exit_pgo = measure_execution_ms(pin_cmd + [gcc_elf_pgo])
            ratio_pgo = sinc_time / gcc_time_pgo if gcc_time_pgo > 0 else 1.0
            ratios_pgo.append(ratio_pgo)
            exit_ok = (sinc_exit == gcc_exit_pgo)
            speedup = f"{1.0/ratio_pgo:.2f}x" if ratio_pgo < 1.0 else f"-{ratio_pgo:.2f}x"
            print(f"{bname:<24} | {sinc_time:>10.2f} | {gcc_time_pgo:>10.2f} | {ratio_pgo:>6.2f}x | {speedup:>12} | {'MATCH' if exit_ok else 'DIFF'}")
        else:
            exit_ok = (sinc_exit == gcc_exit_std)
            speedup = f"{1.0/ratio_std:.2f}x faster" if ratio_std < 1.0 else f"{ratio_std:.2f}x slower"
            print(f"{bname:<24} | {sinc_time:>10.2f} | {gcc_time_std:>10.2f} | {ratio_std:>6.2f}x | {speedup:>12} | {'MATCH' if exit_ok else 'DIFF'}")

    print("=" * 115)
    geomean_std = math.exp(sum(math.log(r) for r in ratios_std) / len(ratios_std)) if ratios_std else 1.0
    print(f"GEOMETRIC MEAN (Standard GCC -O3) : SINC is {geomean_std:.2f}x relative to GCC ({1.0/geomean_std:.2f}x speedup)")

    if ratios_pgo:
        geomean_pgo = math.exp(sum(math.log(r) for r in ratios_pgo) / len(ratios_pgo))
        print(f"GEOMETRIC MEAN (GCC -O3 + PGO)    : SINC is {geomean_pgo:.2f}x relative to GCC+PGO ({1.0/geomean_pgo:.2f}x speedup)")
    print("=" * 115)

if __name__ == "__main__":
    if "--both" in sys.argv:
        run_suite("both")
    elif "--pgo" in sys.argv:
        run_suite("pgo")
    else:
        run_suite("standard")
