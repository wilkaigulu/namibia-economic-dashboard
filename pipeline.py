"""Pipeline orchestrator.

Changes from v1:
  * v1 called subprocess.run() with no check=True, so EVERY step could fail and
    the pipeline would still print "Pipeline Complete" and the CI job would
    still commit. That was the single most dangerous thing in the repo.
  * v1 never ran src/extract/climate.py or src/transform/climate_risk.py, so
    climate data was frozen at whatever was last committed by hand.
  * uses sys.executable rather than "python" (on a bare runner "python" may not
    exist, or may be Python 2).
  * --offline skips the two network steps, so you can rebuild the warehouse
    from committed CSVs without touching the APIs.

Usage:
    python pipeline.py              # full refresh
    python pipeline.py --offline    # rebuild from committed CSVs only
    python pipeline.py --only transform load validate
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from common import ensure_dirs, get_logger

log = get_logger("pipeline")

STEPS = [
    ("extract",   "World Bank indicators",   "src/extract/world_bank.py",        True),
    ("extract",   "NASA POWER climate",      "src/extract/climate.py",           True),
    ("transform", "Climate risk indices",    "src/transform/climate_risk.py",    False),
    ("load",      "Build star schema",       "src/load/build_warehouse.py",      False),
    ("validate",  "Data quality gate",       "src/validate/validate_data.py",    False),
]


def run_step(label: str, script: str) -> float:
    log.info("=" * 70)
    log.info("%s  (%s)", label, script)
    log.info("=" * 70)
    started = time.perf_counter()
    subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)
    return time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="skip steps that hit an external API")
    parser.add_argument("--only", nargs="+", metavar="STAGE",
                        choices=["extract", "transform", "load", "validate"],
                        help="run only these stages")
    args = parser.parse_args()

    ensure_dirs()

    selected = [
        s for s in STEPS
        if (not args.only or s[0] in args.only)
        and not (args.offline and s[3])
    ]

    if args.offline:
        log.info("offline mode: skipping network extracts")

    timings: list[tuple[str, float]] = []
    for _stage, label, script, _net in selected:
        try:
            timings.append((label, run_step(label, script)))
        except subprocess.CalledProcessError as exc:
            log.error("STEP FAILED: %s (exit %s). Pipeline aborted — nothing downstream ran, "
                      "so the warehouse still holds the last good build.", label, exc.returncode)
            return exc.returncode

    log.info("=" * 70)
    for label, seconds in timings:
        log.info("%-28s %6.1fs", label, seconds)
    log.info("pipeline complete (%.1fs total)", sum(t for _, t in timings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
