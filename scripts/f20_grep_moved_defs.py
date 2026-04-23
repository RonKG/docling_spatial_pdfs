"""F20 section-6 check: ensure migrated ``def`` helpers no longer live in notebook source."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"

PATTERN = re.compile(
    r"def\s+("
    r"parse_masthead"
    r"|split_gazette_notices"
    r"|build_envelope_dict"
    r"|compute_pdf_sha256"
    r"|score_notice_number"
    r"|reorder_by_spatial_position(_with_confidence)?"
    r"|detect_trailing_content_cutoff"
    r"|extract_corrigenda"
    r"|score_structure|score_spatial|score_boundary|score_table"
    r"|composite_confidence|score_notice|score_notices"
    r"|compute_document_confidence|aggregate_confidence"
    r"|filter_notices|partition_by_band|explain"
    r"|make_extracted_at|make_gazette_issue_id|make_notice_id"
    r"|_estimate_ocr_quality|_clip"
    r"|_segment_body_lines|_strip_running_headers"
    r"|_split_on_multiple_spaces|_extract_title_stack|_repair_merged_rows"
    r"|_try_parse_s_no_table|_ends_with_terminal_punct"
    r"|_find_recovered_boundaries|_stitch_multipage_notices|_table_to_text"
    r"|compute_page_layout_confidence|_extract_elements|_get_page_dimensions"
    r"|_reorder_page|_cluster_y_bands|_classify_band"
    r")\("
)


def main() -> int:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    hits: list[tuple[int, int, str]] = []
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        for ln_idx, line in enumerate(src.splitlines()):
            if PATTERN.search(line):
                hits.append((cell_idx, ln_idx, line))
    print(f"Leaked migrated-def hits in source cells: {len(hits)}")
    for h in hits:
        print(f"  cell {h[0]} line {h[1]}: {h[2]!r}")
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
