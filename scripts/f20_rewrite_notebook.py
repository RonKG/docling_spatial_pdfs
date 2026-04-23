r"""F20 helper: rewrite gazette_docling_pipeline_spatial.ipynb in place.

Replaces the helper-definition cells with either:

* A clean F20 imports block at the top of the notebook.
* A thin ``GazettePipeline`` shim that calls ``build_envelope`` then writes
  the same five ``output/{stem}/`` files ``process_pdf`` wrote before F20.
* Empty placeholder comments for cells whose helpers have fully migrated
  into ``kenya_gazette_parser/`` submodules.

Cells that were notebook-only (UX: run_pdfs, selection, calibration,
confidence report, LLM, visual inspection) are left untouched.

Run from repo root: ``.\.venv\Scripts\python.exe scripts\f20_rewrite_notebook.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"

IMPORTS_CELL = """\
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.types.doc.labels import DocItemLabel

from kenya_gazette_parser import __version__ as LIBRARY_VERSION
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
from kenya_gazette_parser.models import Envelope

PROJECT_ROOT = Path.cwd().resolve()
PDF_DIR = PROJECT_ROOT / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("PDF_DIR:", PDF_DIR)
print("OUTPUT_DIR:", OUTPUT_DIR)
print("LIBRARY_VERSION:", LIBRARY_VERSION, "SCHEMA_VERSION:", SCHEMA_VERSION)
"""

MOVED_MASTHEAD_CELL = """\
# F11 masthead parsing has moved to kenya_gazette_parser.masthead.parse_masthead.
# The old inline smoke test (test_parse_masthead) is retained by the canonical-PDF
# regression in scripts/f20_regression_check.py; there is no notebook-local
# duplicate to keep in sync.
"""

MOVED_SPLITTING_CELL = """\
# Notice splitting, corrigenda extraction, and trailing-content detection have
# moved to kenya_gazette_parser.{splitting,corrigenda,trailing}. The helpers
# below (`extract_title_from_docling`, `docling_export_summary`,
# `highlight_gazette_notices_in_markdown`) are notebook-only demo utilities;
# they stay here until F21 introduces write_envelope.


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


_GAZETTE_NOTICE_MD_LINE = re.compile(
    r"^(\\#\\# )?(GAZETTE NOTICE NO\\. \\d+)\\s*$",
    re.MULTILINE,
)

_GAZETTE_NOTICE_HIGHLIGHT_STYLE = (
    'style="background-color:#fff3cd;color:#1a1a1a;padding:0.15em 0.35em;'
    'border-radius:3px;font-weight:600;"'
)


def highlight_gazette_notices_in_markdown(md: str) -> str:
    \"\"\"Wrap standalone GAZETTE NOTICE NO. lines for visible highlight in Markdown HTML preview.\"\"\"

    def repl(m: re.Match) -> str:
        notice = m.group(2)
        inner = f'<span {_GAZETTE_NOTICE_HIGHLIGHT_STYLE}>{notice}</span>'
        if m.group(1):
            return f"## {inner}"
        return inner

    return _GAZETTE_NOTICE_MD_LINE.sub(repl, md)
"""

MOVED_SCORING_CELL = """\
# Confidence scoring has moved to kenya_gazette_parser.scoring:
#   score_notice_number, score_structure, score_spatial, score_boundary,
#   score_table, composite_confidence, score_notice, score_notices,
#   compute_document_confidence. See the top-of-notebook imports.
"""

MOVED_DOWNSTREAM_CELL = """\
# Downstream confidence helpers (filter_notices, partition_by_band,
# aggregate_confidence, explain) have moved to kenya_gazette_parser.scoring.
"""

MOVED_SPATIAL_CELL = """\
# Spatial reading-order reorder + layout confidence have moved to
# kenya_gazette_parser.spatial. D2 fix: `reorder_by_spatial_position_with_confidence`
# no longer emits `n_pages`; `envelope_builder.build_envelope_dict` now
# passes `layout_info` through verbatim.
"""

MOVED_IDENTITY_CELL = """\
# Identity and versioning helpers have moved to:
#   * kenya_gazette_parser.__version__ (LIBRARY_VERSION, SCHEMA_VERSION)
#   * kenya_gazette_parser.identity (make_extracted_at, compute_pdf_sha256,
#     make_gazette_issue_id, make_notice_id).
# D1 fix: the notebook no longer declares LIBRARY_VERSION / SCHEMA_VERSION;
# both are imported from the package at the top of this notebook.
"""

PIPELINE_SHIM_CELL = """\
# F20: `process_pdf` is now a thin shim over `kenya_gazette_parser.pipeline.build_envelope`.
# The pure-compute path lives in the library; the notebook demo still writes the
# same five output/{stem}/ side files as before (F21 will move those into
# `write_envelope`). `envelope_builder.build_envelope_dict` and
# `_estimate_ocr_quality` have also moved into the package.


@dataclass
class GazettePipeline:
    converter: DocumentConverter = field(default_factory=DocumentConverter)
    include_full_docling_dict: bool = False

    def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
        pdf_path = Path(pdf_path).resolve()

        env = build_envelope(
            pdf_path,
            converter=self.converter,
            include_full_docling_dict=self.include_full_docling_dict,
        )
        record = env.model_dump(mode="json")

        pdf_output_dir = OUTPUT_DIR / pdf_path.stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)

        out_json = pdf_output_dir / f"{pdf_path.stem}_gazette_spatial.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # Regenerate the diagnostic side files from a second pass through Docling.
        # This keeps the notebook demo byte-for-byte compatible with the pre-F20
        # output tree (Docling conversion is deterministic for these files).
        result = self.converter.convert(str(pdf_path))
        doc = result.document
        plain = doc.export_to_text()
        md = doc.export_to_markdown()
        doc_dict = doc.export_to_dict()
        plain_spatial, _layout = reorder_by_spatial_position_with_confidence(doc_dict)

        out_spatial_txt = pdf_output_dir / f"{pdf_path.stem}_spatial.txt"
        with open(out_spatial_txt, "w", encoding="utf-8") as f:
            f.write(plain_spatial)

        out_markdown_default = pdf_output_dir / f"{pdf_path.stem}_docling_markdown.md"
        with open(out_markdown_default, "w", encoding="utf-8") as f:
            f.write(highlight_gazette_notices_in_markdown(md))

        out_markdown_spatial = pdf_output_dir / f"{pdf_path.stem}_spatial_markdown.md"
        with open(out_markdown_spatial, "w", encoding="utf-8") as f:
            f.write(highlight_gazette_notices_in_markdown(plain_spatial))

        docling_only = pdf_output_dir / f"{pdf_path.stem}_docling.json"
        with open(docling_only, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, ensure_ascii=False, indent=2)

        print(f"Wrote: {out_json}")
        print(f"Wrote: {out_spatial_txt}")
        print(f"Wrote: {out_markdown_default}")
        print(f"Wrote: {out_markdown_spatial}")
        print(f"Wrote: {docling_only}")
        return record


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


# Map: cell index -> new source. Cells not listed are left untouched.
REPLACEMENTS = {
    2: IMPORTS_CELL,
    3: MOVED_MASTHEAD_CELL,
    5: MOVED_SPLITTING_CELL,
    7: MOVED_SCORING_CELL,
    8: MOVED_DOWNSTREAM_CELL,
    10: MOVED_SPATIAL_CELL,
    12: MOVED_IDENTITY_CELL,
    13: PIPELINE_SHIM_CELL,
}


def _split_source(src: str) -> list[str]:
    """Jupyter stores cell source as a list of lines each ending in '\\n'."""
    if not src:
        return []
    lines = src.splitlines(keepends=True)
    # Ensure last line retains its trailing newline if there was one in src.
    # (splitlines(keepends=True) preserves existing newlines correctly.)
    return lines


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
