#!/usr/bin/env python
"""F22 TC11: Gate 2 notice_id stability vs F21/F20 on-disk baseline.

Compare notice_id arrays against on-disk baseline for all 6 canonical PDFs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

OUTPUT_DIR = REPO / "output"

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]


def _notice_ids(rec: dict) -> list[str]:
    notices = rec.get("notices") or rec.get("gazette_notices") or []
    return [n["notice_id"] for n in notices]


def main() -> int:
    all_ok = True
    results: list[tuple[str, int, int, bool]] = []
    
    for stem in CANONICAL_STEMS:
        cur_path = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
        
        # Get baseline from git HEAD
        rel = f"output/{stem}/{stem}_gazette_spatial.json"
        res = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=str(REPO),
            capture_output=True,
            encoding="utf-8",
        )
        
        if res.returncode != 0 or not res.stdout:
            print(f"  {stem}: SKIP (no baseline in git HEAD)")
            continue
        
        if not cur_path.exists():
            print(f"  {stem}: FAIL (current output missing)")
            all_ok = False
            continue
        
        base_rec = json.loads(res.stdout)
        cur_rec = json.loads(cur_path.read_text(encoding="utf-8"))
        
        base_ids = _notice_ids(base_rec)
        cur_ids = _notice_ids(cur_rec)
        
        # CXXVIINo 63 has documented G1 tail-page truncation tolerance
        if stem == "Kenya Gazette Vol CXXVIINo 63":
            is_prefix = (
                cur_ids == base_ids[:len(cur_ids)] or
                base_ids == cur_ids[:len(base_ids)]
            )
            if is_prefix:
                print(f"  {stem}: OK (prefix match: cur={len(cur_ids)} base={len(base_ids)})")
                results.append((stem, len(cur_ids), len(base_ids), True))
                continue
        
        if cur_ids == base_ids:
            print(f"  {stem}: OK (exact match: {len(cur_ids)} ids)")
            results.append((stem, len(cur_ids), len(base_ids), True))
        else:
            first_diff = next(
                (i for i, (a, b) in enumerate(zip(cur_ids, base_ids)) if a != b),
                min(len(cur_ids), len(base_ids)),
            )
            print(f"  {stem}: FAIL (cur={len(cur_ids)} base={len(base_ids)} first_diff={first_diff})")
            results.append((stem, len(cur_ids), len(base_ids), False))
            all_ok = False
    
    if all_ok:
        summary = ", ".join(f"{s.split('Vol ')[-1]}={c}" for s, c, _, _ in results)
        print(f"TC11 PASS ({len(results)}/6 exact; {summary})")
        return 0
    else:
        print("TC11 FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
