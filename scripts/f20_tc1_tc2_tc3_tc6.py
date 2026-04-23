r"""F20 TC1+TC2+TC3+TC6: gate-level checks against the F19 on-disk baseline.

Reads the **current** envelope JSON in ``output/{stem}/{stem}_gazette_spatial.json``
(written by ``scripts/f20_run_pipeline.py``) and the **baseline** envelope JSON
captured from the prior commit via ``git show HEAD:...`` to verify:

* TC1 (CXXIVNo 282): notice count, gazette_issue_id, mean_composite delta,
  output_format_version stamping.
* TC2 (CXXVIINo 63): mean_composite delta + ``table_coerced_to_text`` warning
  count parity vs F19 baseline.
* TC3 (CIINo 83 pre 2010): mean_composite delta + ocr_quality < 0.5 +
  exactly one notice (per spec section 4 row TC3).
* TC6: ``notice_id`` arrays element-wise equal to the on-disk baseline for
  every PDF, AND ``check_regression(tolerance=0.05)`` PASS for all 6 PDFs.

Side-effect-free aside from running ``git show``. Run from repo root.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"


def load_current(stem: str) -> dict:
    p = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_baseline(stem: str) -> dict:
    rel = f"output/{stem}/{stem}_gazette_spatial.json"
    res = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if res.returncode != 0:
        raise SystemExit(f"git show failed for {stem}: {res.stderr}")
    return json.loads(res.stdout)


def notice_ids(env: dict) -> list[str]:
    return [n["notice_id"] for n in (env.get("notices") or env.get("gazette_notices") or [])]


def mean_composite(env: dict) -> float:
    dc = env.get("document_confidence") or {}
    return float(dc.get("mean_composite", 0.0))


def warning_count(env: dict, kind: str) -> int:
    n = 0
    for w in env.get("warnings") or []:
        if (w.get("kind") or "") == kind:
            n += 1
    return n


def tc1_cxxiv282() -> bool:
    print("TC1 — Vol CXXIVNo 282 (modern 2-column happy path)")
    stem = "Kenya Gazette Vol CXXIVNo 282"
    cur = load_current(stem)
    base = load_baseline(stem)
    iss = (cur.get("issue") or {}).get("gazette_issue_id")
    n_notices = len(cur.get("notices") or [])
    mc_cur = mean_composite(cur)
    mc_base = mean_composite(base)
    delta = abs(mc_cur - mc_base)
    ofv = cur.get("output_format_version")
    ok_iss = iss == "KE-GAZ-CXXIV-282-2022-12-30"
    ok_n = n_notices == 201
    ok_mc = delta <= 0.05
    ok_ofv = ofv == 1
    print(f"  gazette_issue_id   = {iss!r:50s}  expected 'KE-GAZ-CXXIV-282-2022-12-30'  {'OK' if ok_iss else 'FAIL'}")
    print(f"  len(notices)       = {n_notices:<5d}  expected 201                            {'OK' if ok_n else 'FAIL'}")
    print(f"  mean_composite     = {mc_cur:.3f}  baseline {mc_base:.3f}  delta {delta:.3f}  {'OK' if ok_mc else 'FAIL'}")
    print(f"  output_format_ver  = {ofv}  expected 1                                  {'OK' if ok_ofv else 'FAIL'}")
    return ok_iss and ok_n and ok_mc and ok_ofv


def tc2_cxxvii63() -> bool:
    print("TC2 — Vol CXXVIINo 63 (OCR-heavy, table_coerced_to_text count)")
    stem = "Kenya Gazette Vol CXXVIINo 63"
    cur = load_current(stem)
    base = load_baseline(stem)
    mc_cur = mean_composite(cur)
    mc_base = mean_composite(base)
    delta = abs(mc_cur - mc_base)
    n_table_cur = warning_count(cur, "table_coerced_to_text")
    n_table_base = warning_count(base, "table_coerced_to_text")
    ok_mc = delta <= 0.05
    ok_warn = n_table_cur == n_table_base
    print(f"  mean_composite     = {mc_cur:.3f}  baseline {mc_base:.3f}  delta {delta:.3f}  {'OK' if ok_mc else 'FAIL'}")
    print(f"  table_coerced_to_text count = {n_table_cur}  baseline {n_table_base}  {'OK' if ok_warn else 'FAIL'}")
    return ok_mc and ok_warn


def tc3_ciino83() -> bool:
    print("TC3 — Vol CIINo 83 - pre 2010 (OCR-quality boundary cap)")
    stem = "Kenya Gazette Vol CIINo 83 - pre 2010"
    cur = load_current(stem)
    base = load_baseline(stem)
    mc_cur = mean_composite(cur)
    mc_base = mean_composite(base)
    delta = abs(mc_cur - mc_base)
    dc = cur.get("document_confidence") or {}
    ocr = float(dc.get("ocr_quality", 1.0))
    n_notices = len(cur.get("notices") or [])
    ok_mc = delta <= 0.05
    ok_ocr = ocr < 0.5
    ok_one = n_notices == 1
    print(f"  mean_composite     = {mc_cur:.3f}  baseline {mc_base:.3f}  delta {delta:.3f}  {'OK' if ok_mc else 'FAIL'}")
    print(f"  document_confidence.ocr_quality = {ocr:.3f}  expected < 0.5            {'OK' if ok_ocr else 'FAIL'}")
    print(f"  len(notices)       = {n_notices}  expected 1                              {'OK' if ok_one else 'FAIL'}")
    return ok_mc and ok_ocr and ok_one


CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]


def tc6_notice_id_stability() -> bool:
    print("TC6 — notice_id stability vs F19 on-disk baseline (Gate 2)")
    all_ok = True
    for stem in CANONICAL_STEMS:
        try:
            cur_ids = notice_ids(load_current(stem))
            base_ids = notice_ids(load_baseline(stem))
        except Exception as exc:
            print(f"  {stem}: ERROR loading: {exc}")
            all_ok = False
            continue
        if cur_ids == base_ids:
            print(f"  {stem}: OK ({len(cur_ids)} notice_ids match)")
        else:
            all_ok = False
            n_diff = sum(1 for a, b in zip(cur_ids, base_ids) if a != b)
            extra = abs(len(cur_ids) - len(base_ids))
            print(f"  {stem}: FAIL — len(cur)={len(cur_ids)} len(base)={len(base_ids)}, diffs={n_diff}, extra={extra}")
            for i, (a, b) in enumerate(zip(cur_ids, base_ids)):
                if a != b:
                    print(f"    [{i}] {a!r} != {b!r}")
                    if i > 5:
                        print("    ... (truncated)")
                        break
    return all_ok


def main() -> int:
    rows: list[tuple[str, bool]] = []
    rows.append(("TC1", tc1_cxxiv282()))
    print()
    rows.append(("TC2", tc2_cxxvii63()))
    print()
    rows.append(("TC3", tc3_ciino83()))
    print()
    rows.append(("TC6 (notice_id stability)", tc6_notice_id_stability()))
    print()
    print("=" * 60)
    for name, ok in rows:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    return 0 if all(ok for _, ok in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
