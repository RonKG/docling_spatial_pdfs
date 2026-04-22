r"""F19 helper: re-process the 6 canonical PDFs through the notebook pipeline.

Loads every code cell from ``gazette_docling_pipeline_spatial.ipynb`` up to and
including the cell that defines ``GazettePipeline``, executes them in a fresh
namespace, then calls ``pipeline.process_pdf(...)`` for each canonical PDF.

Skips the "convenience" cells at the bottom of the notebook (calibration
runner, confidence report, LLM validation, etc.) so nothing accidentally kicks
off a second pipeline run while we are still defining helpers.

Run from repo root: `.\.venv\Scripts\python.exe scripts\f19_run_pipeline.py`.
Optional args: one or more canonical PDF stems to re-process only a subset.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"
PDF_DIR_CANDIDATES = [REPO / "pdfs", REPO / "Kenya Gazette PDFs"]

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]

# Anything whose source begins with any of these snippets is considered a test /
# driver cell and is skipped; we only want the definition cells that produce a
# working ``GazettePipeline``.
SKIP_PREFIXES = (
    "check_regression(",
    "update_regression_fixture(",
    "# F12 Test:",
    "# F14 Test",
    "_rep = confidence_report(",
    "ENABLE_LLM_VALIDATION = True",
    "# %pip install openai",
    "# sample_for_calibration()",
)


def _should_skip(src: str) -> bool:
    stripped = src.strip()
    if not stripped:
        return True
    for pref in SKIP_PREFIXES:
        if stripped.startswith(pref):
            return True
    return False


def _resolve_pdf_path(stem: str) -> Path:
    for base in PDF_DIR_CANDIDATES:
        p = base / f"{stem}.pdf"
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Could not find canonical PDF for stem {stem!r} under {PDF_DIR_CANDIDATES}"
    )


def _load_notebook_code(notebook_path: Path) -> str:
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    chunks: list[str] = []
    stop_after_idx: int | None = None
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "class GazettePipeline" in src:
            chunks.append(src)
            stop_after_idx = idx
            break
        if _should_skip(src):
            continue
        chunks.append(src)
    if stop_after_idx is None:
        raise RuntimeError("Did not find GazettePipeline class in notebook.")
    return "\n\n".join(chunks)


def _run_inprocess(stems: list[str]) -> int:
    """Run all requested PDFs in the current process (fast-start)."""
    code = _load_notebook_code(NOTEBOOK)
    import types

    mod_name = "_notebook_runtime"
    module = types.ModuleType(mod_name)
    module.__file__ = str(NOTEBOOK)
    sys.modules[mod_name] = module
    exec(compile(code, str(NOTEBOOK), "exec"), module.__dict__)

    Pipeline = module.__dict__["GazettePipeline"]
    pipeline = Pipeline()

    for stem in stems:
        pdf_path = _resolve_pdf_path(stem)
        print(f"\n=== Processing: {pdf_path.name} ===", flush=True)
        pipeline.process_pdf(pdf_path)
    return 0


def _run_subprocess_per_pdf(stems: list[str]) -> int:
    """Run each PDF in its own Python subprocess; frees memory between runs."""
    import subprocess

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

    if inprocess or len(stems) <= 1:
        return _run_inprocess(stems)
    return _run_subprocess_per_pdf(stems)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
