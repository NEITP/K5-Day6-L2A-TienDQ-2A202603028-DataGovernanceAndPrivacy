"""Single-command T02 submission runner and evaluator.

Usage:
    py -3.14 -m tools.t02_submission run
    py -3.14 -m tools.t02_submission evaluate

The run action creates both baseline and PoC outputs offline. The evaluate
action reports N/A when the student fixture has no GT labels; with labels, it
evaluates both runs and generates the comparison table.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT = Path("fixtures/t02_raw_qc/gt/labels.csv")


def run_command(args: list[str]) -> int:
    return subprocess.run([sys.executable, *args], cwd=ROOT, check=False).returncode


def run_pipelines() -> int:
    commands = [
        [
            "-m", "src.main", "--config", "configs/lab.yaml", "--track", "t02",
            "--output", "out/baseline", "--run-name", "baseline",
            "--pipeline", "src.examples.t02_laplacian_baseline", "--offline", "--seed", "42",
        ],
        [
            "-m", "src.main", "--config", "configs/lab.yaml", "--track", "t02",
            "--output", "out/poc", "--run-name", "poc", "--offline", "--seed", "42",
        ],
    ]
    for command in commands:
        code = run_command(command)
        if code:
            return code
    return 0


def evaluate_runs() -> int:
    gt_path = ROOT / GT
    if not gt_path.is_file():
        print(f"N/A: GT labels are not included in the student package ({GT}).")
        print("No Recall@20 or Precision@20 was calculated; no metrics were fabricated.")
        return 0

    runs = [
        ("baseline", "out/baseline/ranked_review.csv", "reports/metrics_baseline.json"),
        ("poc", "out/poc/ranked_review.csv", "reports/metrics_poc.json"),
    ]
    for run_name, prediction, metrics in runs:
        code = run_command([
            "-m", "src.evaluate", "--track", "t02", "--gt", GT.as_posix(),
            "--pred", prediction, "--run-name", run_name, "--out", metrics,
        ])
        if code:
            return code
    return run_command([
        "-m", "src.compare", "reports/metrics_baseline.json",
        "reports/metrics_poc.json", "--out", "reports/table1_baseline_vs_poc.md",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "evaluate"))
    action = parser.parse_args(argv).action
    return run_pipelines() if action == "run" else evaluate_runs()


if __name__ == "__main__":
    raise SystemExit(main())
