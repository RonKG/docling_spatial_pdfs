r"""F20 helper: re-process the 6 canonical PDFs via ``pipeline.build_envelope``.

Mirrors the F19 ``scripts/f19_run_pipeline.py`` subprocess-per-PDF pattern
(needed to dodge ``std::bad_alloc`` on OCR-heavy pages in Vol CXXVIINo 63)
but now calls the package directly: no notebook exec, no double Docling
pass. Writes only the ``{stem}_gazette_spatial.json`` file required by
``check_regression`` / TC6; the diagnostic side files (``spatial.txt``,
markdown, raw ``docling.json``) are NOT regenerated here (they remain as
written by F19 on the previous run, which is fine for the regression
check).

Run from repo root:
    ``.\.venv\Scripts\python.exe scripts\f20_run_pipeline.py``

Optional args: one or more canonical PDF stems to re-process only a subset.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

PDF_DIR = REPO / "pdfs"
OUTPUT_DIR = REPO / "output"

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]


def _resolve_pdf_path(stem: str) -> Path:
    p = PDF_DIR / f"{stem}.pdf"
    if p.exists():
        return p
    raise FileNotFoundError(f"Could not find canonical PDF for stem {stem!r} under {PDF_DIR}")


def _run_inprocess(stem: str) -> int:
    from kenya_gazette_parser.pipeline import build_envelope

    pdf_path = _resolve_pdf_path(stem)
    print(f"=== Processing: {pdf_path.name} ===", flush=True)
    env = build_envelope(pdf_path)
    record = env.model_dump(mode="json")

    out_dir = OUTPUT_DIR / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{pdf_path.stem}_gazette_spatial.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {out_json}", flush=True)
    return 0


def _run_subprocess_per_pdf(stems: list[str]) -> int:
    exe = sys.executable
    script = Path(__file__).resolve()
    any_failed = False
    for stem in stems:
        print(f"\n>>> Subprocess for {stem}", flush=True)
        rc = subprocess.call(
            [exe, str(script), "--inprocess", stem],
            cwd=str(REPO),
        )
        if rc != 0:
            any_failed = True
            print(f"<<< {stem} FAILED (rc={rc})", flush=True)
        else:
            print(f"<<< {stem} OK", flush=True)
    return 1 if any_failed else 0


def main(argv: list[str]) -> int:
    inprocess = False
    if argv and argv[0] == "--inprocess":
        inprocess = True
        argv = argv[1:]

    if argv:
        stems = argv
    else:
        stems = CANONICAL_STEMS

    for stem in stems:
        if stem not in CANONICAL_STEMS:
            print(f"WARNING: {stem!r} is not a canonical stem; continuing anyway")

    if inprocess:
        if len(stems) != 1:
            raise SystemExit("--inprocess expects exactly one stem argument")
        return _run_inprocess(stems[0])
    if len(stems) == 1:
        return _run_inprocess(stems[0])
    return _run_subprocess_per_pdf(stems)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
