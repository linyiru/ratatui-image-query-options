#!/usr/bin/env python3
"""Runs query-options and prints the median and slowest of each number.

    ./run.py silent [--runs 10]
        In a pseudo-terminal that answers nothing, as a terminal whose
        replies never arrive: `default` against `timeout=500`.

    ./run.py terminal [--runs 10] --launch 'ghostty -e {cmd}'
        In a real terminal, started by the --launch command for each run:
        `default` against `shm`. Counts the shared memory objects left in
        /dev/shm afterwards.

Build first: cargo build --release.
"""

import argparse
import os
import pty
import re
import shlex
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BINARY = ROOT / "target/release/query-options"
OUT = ROOT / "results/run.tmp"


def silent(mode):
    main, child = pty.openpty()
    process = subprocess.Popen([BINARY, mode, OUT], stdin=child, stdout=child, stderr=child, start_new_session=True)
    os.close(child)
    # Read what it writes, answer nothing.
    while process.poll() is None:
        try:
            os.read(main, 1 << 16)
        except OSError:
            break
    process.wait()
    os.close(main)


def terminal(mode, launch):
    lines = OUT.read_text().count("\n") if OUT.exists() else 0
    subprocess.Popen(launch.format(cmd=shlex.join([str(BINARY), mode, str(OUT)])), shell=True)
    deadline = time.time() + 10
    while time.time() < deadline:
        if OUT.exists() and OUT.read_text().count("\n") > lines:
            return
        time.sleep(0.01)
    raise SystemExit(f"{mode}: no result in 10 s")


def shm_objects():
    return set(os.listdir("/dev/shm")) if os.path.isdir("/dev/shm") else set()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("where", choices=["silent", "terminal"])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--launch", default="ghostty -e {cmd}")
    args = parser.parse_args()
    modes = ["default", "timeout=500"] if args.where == "silent" else ["default", "shm"]
    OUT.parent.mkdir(exist_ok=True)
    OUT.unlink(missing_ok=True)
    before = shm_objects()
    for _ in range(args.runs):
        # Alternated, so load on the machine falls on both alike.
        for mode in modes:
            silent(mode) if args.where == "silent" else terminal(mode, args.launch)
            time.sleep(0.2)
    time.sleep(1)
    left = shm_objects() - before

    values, seen = defaultdict(lambda: defaultdict(list)), {}
    for line in OUT.read_text().splitlines():
        fields = dict(re.findall(r"(\w+)=(\[.*?\]|\S+)", line))
        mode = fields.pop("mode")
        for key, value in fields.items():
            try:
                number = float(value)
            except ValueError:
                seen.setdefault((mode, key), value)
                continue
            values[mode][key].append(number)
    print(f"{args.where}, {args.runs} runs each: median / slowest, ms")
    for mode in modes:
        print(f"  {mode}")
        for key, numbers in values[mode].items():
            print(f"    {key:<10} {statistics.median(numbers):>9.2f} {max(numbers):>9.2f}")
        for (seen_mode, key), value in seen.items():
            if seen_mode == mode:
                print(f"    {key:<10} {value}")
    if args.where == "terminal":
        print(f"  shared memory objects left in /dev/shm: {len(left)}")
    OUT.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
