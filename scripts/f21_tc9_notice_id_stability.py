r"""F21 TC9: Gate 2 notice_id stability vs the F20 on-disk baseline.

Loads the current ``output/{stem}/{stem}_gazette_spatial.json`` (written by
``scripts/f21_tc8_regression.py``) and compares notice_id lists
element-wise to the baseline JSON at ``HEAD:output/{stem}/..._gazette_spatial.json``.

5/6 PDFs must match exactly. CXXVIINo 63 is allowed to be a strict prefix
(or superset) of the committed baseline, per the documented F20 session-log
G1 OCR non-determinism behavior.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]

OCR_UNSTABLE_STEM = "Kenya Gazette Vol CXXVIINo 63"


def _notice_ids(env: dict) -> list[str]:
    notices = env.get("notices") or env.get("gazette_notices") or []
    return [n["notice_id"] for n in notices]


def _load_current(stem: str) -> dict:
    p = REPO / "output" / stem / f"{stem}_gazette_spatial.json"
    if not p.exists():
        raise FileNotFoundError(f"Current output missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _load_baseline(stem: str) -> dict:
    rel = f"output/{stem}/{stem}_gazette_spatial.json"
    res = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if res.returncode != 0:
        raise RuntimeError(f"git show HEAD:{rel} failed: {res.stderr.strip()}")
    return json.loads(res.stdout)


def main() -> int:
    exact_ok: list[str] = []
    prefix_ok: list[tuple[str, int, int]] = []
    fails: list[str] = []

    for stem in CANONICAL_STEMS:
        try:
            cur = _load_current(stem)
            base = _load_baseline(stem)
        except Exception as exc:
            fails.append(f"{stem}: load error {exc}")
            continue

        cur_ids = _notice_ids(cur)
        base_ids = _notice_ids(base)

        if cur_ids == base_ids:
            exact_ok.append(stem)
            print(f"  {stem}: OK exact-match ({len(cur_ids)} ids)")
            continue

        # Prefix-match tolerance for CXXVIINo 63 (OCR non-determinism G1).
        is_prefix = (
            cur_ids == base_ids[: len(cur_ids)]
            or base_ids == cur_ids[: len(base_ids)]
        )
        if stem == OCR_UNSTABLE_STEM and is_prefix:
            prefix_ok.append((stem, len(cur_ids), len(base_ids)))
            print(
                f"  {stem}: OK prefix-match cur={len(cur_ids)} base={len(base_ids)} "
                f"(documented G1 OCR non-determinism)"
            )
            continue

        fails.append(
            f"{stem}: cur_len={len(cur_ids)} base_len={len(base_ids)} "
            f"first_diff_at_index="
            f"{next((i for i, (a, b) in enumerate(zip(cur_ids, base_ids)) if a != b), 'n/a')}"
        )
        print(f"  {stem}: FAIL")

    if fails:
        print("TC9 FAIL")
        for line in fails:
            print(f"  {line}")
        return 1

    if prefix_ok:
        summary = "; ".join(
            f"{stem} cur={c}/base={b}" for stem, c, b in prefix_ok
        )
        print(
            f"TC9 OK ({len(exact_ok)}/{len(CANONICAL_STEMS)} exact; "
            f"{len(prefix_ok)} prefix-match ({summary}))"
        )
    else:
        print(f"TC9 OK ({len(exact_ok)}/{len(CANONICAL_STEMS)} exact)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
