r"""F21 helper: rewrite the notebook for the public-API + I/O split.

Three edits, all via ``nbformat``-safe JSON surgery (no hand-editing):

1. Cell 2 (imports block): add ``parse_file`` and ``write_envelope`` to the
   package import line so the collapsed shim can call them directly.
2. Cell 5 (``MOVED_SPLITTING_CELL``): delete the
   ``highlight_gazette_notices_in_markdown`` function and its two supporting
   constants. The single canonical copy now lives in
   :mod:`kenya_gazette_parser.io` as ``_highlight_gazette_notices_in_markdown``.
3. Cell 13 (``PIPELINE_SHIM_CELL``): collapse the double-Docling shim into a
   thin ``parse_file`` + ``write_envelope`` call, per spec section 2d.

Run from repo root:
    ``.\.venv\Scripts\python.exe scripts\f21_rewrite_notebook.py``
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"


NEW_IMPORTS_CELL = """\
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.types.doc.labels import DocItemLabel

from kenya_gazette_parser import (
    __version__ as LIBRARY_VERSION,
    parse_file,
    write_envelope,
    Envelope,
)
from kenya_gazette_parser.identity import (
    SCHEMA_VERSION,
    make_extracted_at,
    compute_pdf_sha256,
    make_gazette_issue_id,
    make_notice_id,
)
from kenya_gazette_parser.masthead import parse_masthead
from kenya_gazette_parser.spatial import (
    reorder_by_spatial_position,
    reorder_by_spatial_position_with_confidence,
    compute_page_layout_confidence,
)
from kenya_gazette_parser.splitting import split_gazette_notices
from kenya_gazette_parser.trailing import detect_trailing_content_cutoff
from kenya_gazette_parser.corrigenda import extract_corrigenda
from kenya_gazette_parser.scoring import (
    score_notice_number, score_structure, score_spatial, score_boundary,
    score_table, composite_confidence, score_notice, score_notices,
    compute_document_confidence, aggregate_confidence, filter_notices,
    partition_by_band, explain,
)
from kenya_gazette_parser.envelope_builder import build_envelope_dict
from kenya_gazette_parser.pipeline import build_envelope
from kenya_gazette_parser.models import Envelope  # noqa: F811 (re-imported for clarity)

PROJECT_ROOT = Path.cwd().resolve()
PDF_DIR = PROJECT_ROOT / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("PDF_DIR:", PDF_DIR)
print("OUTPUT_DIR:", OUTPUT_DIR)
print("LIBRARY_VERSION:", LIBRARY_VERSION, "SCHEMA_VERSION:", SCHEMA_VERSION)
"""


# Cell 5: keep the moved-to-submodules banner and the two small notebook-only
# demo helpers (``extract_title_from_docling``, ``docling_export_summary``),
# but DROP the highlight helper + its two constants. The single canonical
# copy now lives in ``kenya_gazette_parser/io.py``.
NEW_MOVED_SPLITTING_CELL = """\
# Notice splitting, corrigenda extraction, and trailing-content detection have
# moved to kenya_gazette_parser.{splitting,corrigenda,trailing}. The remaining
# helpers below (`extract_title_from_docling`, `docling_export_summary`) are
# notebook-only demo utilities. F21 moved the Markdown highlight helper into
# `kenya_gazette_parser.io._highlight_gazette_notices_in_markdown`; the
# previous notebook copy has been deleted.


def extract_title_from_docling(doc) -> str:
    for item in getattr(doc, "texts", []) or []:
        if getattr(item, "label", None) == DocItemLabel.TITLE and getattr(item, "text", None):
            return str(item.text).strip()
    return ""


def docling_export_summary(doc_dict: dict[str, Any]) -> dict[str, Any]:
    \"\"\"Small fingerprint of the Docling JSON without dumping huge trees twice.\"\"\"
    texts = doc_dict.get("texts") or []
    return {
        "schema_name": doc_dict.get("schema_name"),
        "version": doc_dict.get("version"),
        "name": doc_dict.get("name"),
        "texts_count": len(texts) if isinstance(texts, list) else None,
        "tables_count": len(doc_dict.get("tables") or []) if isinstance(doc_dict.get("tables"), list) else None,
        "pictures_count": len(doc_dict.get("pictures") or []) if isinstance(doc_dict.get("pictures"), list) else None,
        "pages_count": len(doc_dict.get("pages") or []) if isinstance(doc_dict.get("pages"), list) else None,
    }
"""


# Cell 13: thin shim per F21 spec section 2d.
NEW_PIPELINE_SHIM_CELL = """\
# F21: `process_pdf` is now a thin wrapper around
# `kenya_gazette_parser.parse_file` + `kenya_gazette_parser.write_envelope`.
# All disk I/O is in `write_envelope`; `parse_file` is pure. The notebook
# shim exists only so existing demo cells (`pipeline = GazettePipeline();
# run_pdfs(pipeline, CANONICAL_PDFS)`) keep working without rewrites.


@dataclass
class GazettePipeline:
    \"\"\"Thin notebook convenience wrapper around parse_file + write_envelope.\"\"\"

    converter: DocumentConverter = field(default_factory=DocumentConverter)
    include_full_docling_dict: bool = False  # reserved; F22 routes via write_envelope

    def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
        pdf_path = Path(pdf_path).resolve()
        env = parse_file(pdf_path)
        written = write_envelope(
            env,
            out_dir=OUTPUT_DIR / pdf_path.stem,
            pdf_path=pdf_path,
            converter=self.converter,
        )
        for _bundle_name, path in written.items():
            print(f"Wrote: {path}")
        return env.model_dump(mode="json")


def run_pdfs(pipeline: GazettePipeline, pdf_paths: list[Path]) -> list[dict[str, Any]]:
    \"\"\"Run the pipeline on an explicit ordered list of PDF paths.\"\"\"
    if not pdf_paths:
        print("No PDF paths to process.")
        return []
    results: list[dict[str, Any]] = []
    for p in pdf_paths:
        print("\\n--- Processing:", p.name, "---")
        results.append(pipeline.process_pdf(p))
    return results


def run_folder(pipeline: GazettePipeline, folder: Path | None = None) -> list[dict[str, Any]]:
    \"\"\"Process every *.pdf in folder (same as selection mode 'all').\"\"\"
    folder = Path(folder or PDF_DIR)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files in {folder}. Add .pdf files and re-run.")
        return []
    return run_pdfs(pipeline, pdfs)


def resolve_pdf_selection(
    mode: str,
    selected_names: list[str],
    folder: Path | None = None,
) -> list[Path]:
    \"\"\"Resolve 'all' or 'selected' to a list of existing PDF paths under folder.\"\"\"
    folder = Path(folder or PDF_DIR)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files in {folder}. Add .pdf files and re-run.")
        return []
    m = (mode or "all").strip().lower()
    if m == "all":
        return pdfs
    if m == "selected":
        if not selected_names:
            print("PDF_SELECTION_MODE is 'selected' but SELECTED_PDF_NAMES is empty. Nothing to do.")
            return []
        by_name = {p.name: p for p in pdfs}
        out: list[Path] = []
        missing: list[str] = []
        for raw in selected_names:
            name = raw.strip()
            if not name:
                continue
            p = by_name.get(name)
            if p is None:
                p = by_name.get(Path(name).name)
            if p is None:
                missing.append(name)
            elif p not in out:
                out.append(p)
        if missing:
            print("Warning: not found in", folder, ":", missing)
            print("Available PDFs:", [p.name for p in pdfs])
        return out
    raise ValueError('PDF_SELECTION_MODE must be "all" or "selected".')
"""


REPLACEMENTS = {
    2: NEW_IMPORTS_CELL,
    5: NEW_MOVED_SPLITTING_CELL,
    13: NEW_PIPELINE_SHIM_CELL,
}


def _split_source(src: str) -> list[str]:
    return src.splitlines(keepends=True) if src else []


def main() -> int:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for idx, new_src in REPLACEMENTS.items():
        cell = nb["cells"][idx]
        cell["source"] = _split_source(new_src)
        cell["outputs"] = []
        cell["execution_count"] = None
    NOTEBOOK.write_text(
        json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Rewrote {len(REPLACEMENTS)} cells in {NOTEBOOK.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
