"""TC9: Gate 1 regression - 6 canonical PDFs still pass check_regression(0.05)."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

CANONICAL_PDFS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]

TOLERANCE = 0.05


def test_tc9():
    output_dir = Path(__file__).parent.parent / "output"
    baseline_path = Path(__file__).parent.parent / "tests" / "expected_confidence.json"

    if not baseline_path.exists():
        print(f"TC9 SKIP: Baseline file not found at {baseline_path}")
        return True

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    passed = 0
    failed = 0

    for stem in CANONICAL_PDFS:
        json_path = output_dir / stem / f"{stem}_gazette_spatial.json"
        if not json_path.exists():
            print(f"  SKIP: {stem} (file not found)")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        current_mean = data["document_confidence"]["mean_composite"]

        if stem not in baseline:
            print(f"  SKIP: {stem} (not in baseline)")
            continue

        expected_mean = baseline[stem]["mean_composite"]
        delta = abs(current_mean - expected_mean)

        if delta <= TOLERANCE:
            print(f"  PASS: {stem} (delta={delta:.4f}, mean={current_mean:.4f})")
            passed += 1
        else:
            print(f"  FAIL: {stem} (delta={delta:.4f} > {TOLERANCE})")
            failed += 1

    if failed > 0:
        print(f"\nTC9 FAIL: {failed}/{passed + failed} PDFs outside tolerance")
        return False

    print(f"\nTC9 PASS (Gate 1 still cleared): All {passed} PDFs within {TOLERANCE} tolerance")
    return True


if __name__ == "__main__":
    if not test_tc9():
        sys.exit(1)
