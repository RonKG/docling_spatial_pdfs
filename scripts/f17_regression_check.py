r"""F17 T5: regression check against tests/expected_confidence.json.

Reads existing JSON outputs under output/ and compares per-PDF mean composite
to the fixture. Mirrors `check_regression()` in the notebook exactly but runs
standalone so Agent 2 can verify T5 without opening Jupyter.

Run from repo root: `.\.venv\Scripts\python.exe scripts\f17_regression_check.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"
REGRESSION_FILE = REPO / "tests" / "expected_confidence.json"
TOLERANCE = 0.05


def aggregate_confidence(notices: list[dict]) -> dict[str, float]:
    cs: list[float] = []
    for n in notices:
        scores = n.get("confidence_scores") or {}
        composite = scores.get("composite")
        if composite is not None:
            cs.append(float(composite))
    if not cs:
        return {"mean": 0.0, "min": 0.0, "fraction_high": 0.0, "n": 0}
    return {
        "mean": round(sum(cs) / len(cs), 3),
        "min": round(min(cs), 3),
        "fraction_high": round(sum(1 for c in cs if c >= 0.80) / len(cs), 3),
        "n": len(cs),
    }


def check_regression(tolerance: float = TOLERANCE) -> bool:
    if not REGRESSION_FILE.exists():
        print(f"FAIL: No fixture at {REGRESSION_FILE}")
        return False

    expected = json.loads(REGRESSION_FILE.read_text(encoding="utf-8"))
    regressed = False
    checked = 0

    for name, snap in expected.items():
        if not snap.get("present"):
            continue
        cur_path = OUTPUT_DIR / name / f"{name}_gazette_spatial.json"
        if not cur_path.exists():
            print(f"  MISSING current output for {name}")
            regressed = True
            continue
        with open(cur_path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
        cur = aggregate_confidence(rec.get("notices") or rec.get("gazette_notices") or [])
        baseline = float(snap["mean_composite"])
        delta = cur["mean"] - baseline
        if delta < -tolerance:
            regressed = True
            print(
                f"REGRESSION: {name} mean composite {baseline:.3f} -> "
                f"{cur['mean']:.3f} (drop {-delta:.3f})"
            )
        else:
            print(
                f"OK: {name} mean composite {cur['mean']:.3f} "
                f"(baseline {baseline:.3f})"
            )
        checked += 1

    print(f"\nChecked {checked} PDF(s).")
    return not regressed


if __name__ == "__main__":
    ok = check_regression()
    if ok:
        print("T5 OK (no regression)")
        sys.exit(0)
    else:
        print("T5 FAIL (see output above)")
        sys.exit(1)
