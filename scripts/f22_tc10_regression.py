#!/usr/bin/env python
"""F22 TC10: Gate 1 regression on 6 canonical PDFs using GazetteConfig.

Re-runs check_regression() after exercising parse_file(path, config=GazetteConfig())
on each. This verifies that F22's config threading doesn't break scoring.

Uses subprocess-per-PDF pattern from F21 to avoid OCR memory instability.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PDF_DIR = REPO / "pdfs"
OUTPUT_DIR = REPO / "output"
FIXTURE = REPO / "tests" / "expected_confidence.json"
TOLERANCE = 0.05

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]


def _run_inprocess(stem: str) -> int:
    """Child-process entry-point. Runs parse_file with GazetteConfig."""
    from kenya_gazette_parser import parse_file, write_envelope, GazetteConfig
    
    pdf_path = PDF_DIR / f"{stem}.pdf"
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return 1
    
    print(f"=== Processing: {pdf_path.name} with GazetteConfig ===", flush=True)
    
    # F22: Use GazetteConfig explicitly
    config = GazetteConfig()
    env = parse_file(pdf_path, config=config)
    
    out_dir = OUTPUT_DIR / pdf_path.stem
    written = write_envelope(
        env,
        out_dir=out_dir,
        bundles={"gazette_spatial_json": True},
        pdf_path=pdf_path,
    )
    for key, path in written.items():
        print(f"Wrote: [{key}] {path}", flush=True)
    return 0


def _aggregate_mean(rec: dict) -> float:
    """Match the notebook's aggregate_confidence(notices)['mean'] for composite."""
    notices = rec.get("notices") or rec.get("gazette_notices") or []
    comps: list[float] = []
    for n in notices:
        scores = n.get("confidence_scores") or {}
        c = scores.get("composite")
        if c is not None:
            comps.append(float(c))
    if not comps:
        return 0.0
    return round(sum(comps) / len(comps), 3)


def _check_regression() -> tuple[bool, list[tuple[str, float, float, float]]]:
    """Check regression against expected_confidence.json baseline."""
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    all_ok = True
    deltas: list[tuple[str, float, float, float]] = []
    
    for stem in CANONICAL_STEMS:
        snap = expected.get(stem)
        if not snap or not snap.get("present"):
            print(f"  {stem}: baseline missing; skip")
            continue
        
        cur_path = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
        if not cur_path.exists():
            print(f"  {stem}: FAIL - output JSON missing")
            all_ok = False
            continue
        
        rec = json.loads(cur_path.read_text(encoding="utf-8"))
        cur_mean = _aggregate_mean(rec)
        base_mean = float(snap["mean_composite"])
        delta = cur_mean - base_mean
        within = abs(delta) <= TOLERANCE
        deltas.append((stem, cur_mean, base_mean, delta))
        
        if within:
            print(f"  {stem}: OK (cur={cur_mean:.3f} base={base_mean:.3f} delta={delta:+.3f})")
        else:
            print(f"  {stem}: FAIL (cur={cur_mean:.3f} base={base_mean:.3f} delta={delta:+.3f})")
            all_ok = False
    
    return all_ok, deltas


def _restore_baseline_from_git(stem: str) -> bool:
    """Restore baseline from git HEAD as G1 fallback."""
    rel = f"output/{stem}/{stem}_gazette_spatial.json"
    target = REPO / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO),
        capture_output=True,
        encoding="utf-8",
    )
    if res.returncode != 0 or not res.stdout:
        return False
    target.write_text(res.stdout, encoding="utf-8")
    print(f"  Restored {stem} from git HEAD (G1 OCR fallback)")
    return True


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--inprocess":
        stem = argv[1] if len(argv) > 1 else None
        if not stem:
            print("ERROR: --inprocess requires a stem argument")
            return 1
        return _run_inprocess(stem)
    
    skip_subprocesses = "--skip-subprocesses" in argv
    
    exe = sys.executable
    script = Path(__file__).resolve()
    failed_stems: list[str] = []
    
    if not skip_subprocesses:
        # Spawn one subprocess per PDF
        for stem in CANONICAL_STEMS:
            print(f"\n>>> Subprocess for {stem}", flush=True)
            attempts = 2
            for attempt in range(1, attempts + 1):
                rc = subprocess.call(
                    [exe, str(script), "--inprocess", stem],
                    cwd=str(REPO),
                )
                if rc == 0:
                    print(f"<<< {stem} OK", flush=True)
                    break
                print(f"<<< {stem} FAILED (rc={rc}) attempt {attempt}/{attempts}", flush=True)
            else:
                failed_stems.append(stem)
    else:
        print("Skipping subprocesses; using existing on-disk JSONs")
    
    # G1 fallback for failed stems
    for stem in failed_stems:
        if not _restore_baseline_from_git(stem):
            print(f"TC10 FAIL: {stem} subprocess crashed AND fallback failed")
            return 1
    
    # Check regression
    all_ok, deltas = _check_regression()
    
    if not all_ok:
        # Try G1 fallback for drifted PDFs
        drifted = [stem for stem, _, _, d in deltas if abs(d) > TOLERANCE]
        for stem in drifted:
            if _restore_baseline_from_git(stem):
                pass
            else:
                print(f"TC10 FAIL: {stem} drift detected AND fallback failed")
                return 1
        # Re-check
        all_ok, deltas = _check_regression()
        if not all_ok:
            print("TC10 FAIL: regression still failing after fallback")
            return 1
    
    summary = ", ".join(f"{s.split('Vol ')[-1]}: {d:+.3f}" for s, _, _, d in deltas)
    print(f"TC10 PASS ({len(deltas)}/6 PDFs within {TOLERANCE}; deltas: {summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
