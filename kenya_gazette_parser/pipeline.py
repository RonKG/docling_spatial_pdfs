"""F20 orchestration: ``build_envelope`` (PDF path -> validated ``Envelope``).

This is the pure-compute body lifted out of the notebook's
``GazettePipeline.process_pdf``. File-I/O writes stay in the notebook's
demo cell (they move to F21's ``write_envelope``). ``build_envelope`` is
side-effect-free apart from the warnings it appends to the returned
envelope.

Carry-overs from F19 preserved verbatim (spec 2d "Non-negotiable
carry-overs"):

* ``Envelope.model_validate(build_envelope_dict(record))`` tail call is the
  last line; ``ValidationError`` is NOT caught.
* ``content_sha256`` stamping loop runs immediately after ``notice_id``
  stamping, before the adapter.
* OCR-quality boundary-cap pass runs after ``score_notices`` and before
  identity stamping.
* Corrigendum sentinel + paired warnings come from
  ``envelope_builder.build_envelope_dict`` (unchanged).
* ``type="table"`` body segment coercion + paired warnings come from the
  same adapter (unchanged).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kenya_gazette_parser.corrigenda import extract_corrigenda
from kenya_gazette_parser.envelope_builder import build_envelope_dict
from kenya_gazette_parser.identity import (
    LIBRARY_VERSION,
    SCHEMA_VERSION,
    compute_pdf_sha256,
    make_extracted_at,
    make_gazette_issue_id,
    make_notice_id,
)
from kenya_gazette_parser.masthead import parse_masthead
from kenya_gazette_parser.models import Envelope
from kenya_gazette_parser.scoring import (
    _estimate_ocr_quality,
    composite_confidence,
    compute_document_confidence,
    score_notices,
)
from kenya_gazette_parser.spatial import reorder_by_spatial_position_with_confidence

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

__all__ = ["build_envelope"]


def _docling_export_summary(doc_dict: dict[str, Any]) -> dict[str, Any]:
    """Small fingerprint of the Docling JSON without dumping huge trees twice."""
    texts = doc_dict.get("texts") or []
    return {
        "schema_name": doc_dict.get("schema_name"),
        "version": doc_dict.get("version"),
        "name": doc_dict.get("name"),
        "texts_count": len(texts) if isinstance(texts, list) else None,
        "tables_count": (
            len(doc_dict.get("tables") or [])
            if isinstance(doc_dict.get("tables"), list)
            else None
        ),
        "pictures_count": (
            len(doc_dict.get("pictures") or [])
            if isinstance(doc_dict.get("pictures"), list)
            else None
        ),
        "pages_count": (
            len(doc_dict.get("pages") or [])
            if isinstance(doc_dict.get("pages"), list)
            else None
        ),
    }


def build_envelope(
    pdf_path: Path,
    *,
    converter: "DocumentConverter | None" = None,
    include_full_docling_dict: bool = False,
) -> Envelope:
    """Pure-compute path from PDF on disk to a validated ``Envelope``.

    Orchestrates (in this order): Docling convert -> spatial reorder ->
    masthead parse -> OCR-quality estimate -> notice split -> notice scoring
    -> OCR-boundary capping -> identity stamping (``pdf_sha256``,
    ``gazette_issue_id``, ``notice_id``, ``content_sha256``) -> corrigenda
    extract -> document confidence -> flat record build ->
    ``build_envelope_dict`` adapter -> ``Envelope.model_validate``.

    Returns the validated ``Envelope``. Never writes to disk, never prints.
    ``ValidationError`` propagates uncaught (same rule as F19).
    """
    extracted_at = make_extracted_at()

    pdf_path = Path(pdf_path).resolve()
    stat = pdf_path.stat()

    if converter is None:
        from docling.document_converter import DocumentConverter  # lazy import
        converter = DocumentConverter()

    result = converter.convert(str(pdf_path))
    doc = result.document

    title_guess = _extract_title_from_docling(doc) or pdf_path.stem.replace("_", " ")
    page_count = len(doc.pages) if getattr(doc, "pages", None) else None

    plain = doc.export_to_text()
    md = doc.export_to_markdown()
    doc_dict = doc.export_to_dict()

    plain_spatial, layout_info = reorder_by_spatial_position_with_confidence(doc_dict)

    masthead_data = parse_masthead(plain_spatial)

    ocr_score, ocr_reasons = _estimate_ocr_quality(doc_dict, plain_spatial)

    notices = split_notices_safe(plain_spatial)

    if ocr_score < 0.5 and notices:
        for n in notices:
            prov = n.get("provenance") or {}
            if prov.get("header_match") == "strict":
                prov["ocr_quality"] = ocr_score
            n["provenance"] = prov
    notices = score_notices(notices)
    if ocr_score < 0.5:
        for n in notices:
            scores = n.get("confidence_scores") or {}
            if "boundary" in scores and scores["boundary"] > 0.6:
                scores["boundary"] = 0.6
                scores["composite"] = round(composite_confidence(scores), 3)
                n.setdefault("confidence_reasons", []).append(
                    "boundary: capped at 0.6 due to low OCR quality"
                )
                n["confidence_scores"] = scores

    pdf_sha256 = compute_pdf_sha256(pdf_path)
    gazette_issue_id, is_fallback = make_gazette_issue_id(masthead_data, pdf_sha256)

    warnings: list[dict[str, Any]] = []
    if is_fallback:
        warnings.append({
            "kind": "masthead.parse_failed",
            "message": "Required masthead field missing; using fallback issue id",
            "where": {"pdf_file_name": pdf_path.name},
        })

    for notice in notices:
        notice["gazette_issue_id"] = gazette_issue_id
        provenance = notice.get("provenance") or {}
        line_span = provenance.get("line_span", [0, 0])
        line_span_start = line_span[0] if line_span else 0
        notice["notice_id"] = make_notice_id(
            gazette_issue_id,
            notice.get("gazette_notice_no"),
            line_span_start,
        )

    for notice in notices:
        notice["content_sha256"] = hashlib.sha256(
            notice["gazette_notice_full_text"].encode("utf-8")
        ).hexdigest()

    corrigenda = extract_corrigenda(plain_spatial)
    if isinstance(corrigenda, list):
        for corrigendum in corrigenda:
            if isinstance(corrigendum, dict):
                corrigendum["gazette_issue_id"] = gazette_issue_id

    document_confidence = compute_document_confidence(
        notices,
        layout_confidence=layout_info.get("layout_confidence", 1.0),
        ocr_quality=ocr_score,
    )
    document_confidence["ocr_reasons"] = ocr_reasons

    parsed_fields = sum(1 for v in masthead_data.values() if v is not None)
    parse_confidence = 1.0 if parsed_fields >= 3 else (0.5 if parsed_fields >= 1 else 0.0)

    record: dict[str, Any] = {
        "pdf_title": title_guess,
        "pdf_file_name": pdf_path.name,
        "pdf_path": str(pdf_path),
        "pdf_size_bytes": stat.st_size,
        "pdf_sha256": pdf_sha256,
        "gazette_issue_id": gazette_issue_id,
        "library_version": LIBRARY_VERSION,
        "schema_version": SCHEMA_VERSION,
        "extracted_at": extracted_at,
        "warnings": warnings,
        "pages": page_count,
        "volume": masthead_data.get("volume"),
        "issue_no": masthead_data.get("issue_no"),
        "publication_date": masthead_data.get("publication_date"),
        "supplement_no": masthead_data.get("supplement_no"),
        "masthead_text": "\n".join(plain_spatial.split("\n")[:30]),
        "parse_confidence": parse_confidence,
        "document_confidence": document_confidence,
        "layout_info": layout_info,
        "docling": {
            "export_summary": _docling_export_summary(doc_dict),
            "full_markdown": md,
            "full_plain_text": plain,
            "full_plain_text_spatial": plain_spatial,
        },
        "corrigenda": corrigenda,
        "gazette_notices": notices,
    }

    if include_full_docling_dict:
        record["docling"]["full_docling_document_dict"] = doc_dict

    return Envelope.model_validate(build_envelope_dict(record))


def _extract_title_from_docling(doc) -> str:
    """Local copy of the notebook's ``extract_title_from_docling`` helper.

    The notebook retains the canonical version (it is also called from the
    thin ``GazettePipeline`` wrapper for its writable diagnostic payload).
    ``pipeline.build_envelope`` only needs a best-effort title guess, so
    this copy avoids forcing a ``docling-core`` import at package-load time.
    """
    try:
        from docling_core.types.doc.labels import DocItemLabel
    except Exception:
        DocItemLabel = None

    for item in getattr(doc, "texts", []) or []:
        label = getattr(item, "label", None)
        if DocItemLabel is not None and label == DocItemLabel.TITLE:
            text = getattr(item, "text", None)
            if text:
                return str(text).strip()
        elif label == "title":
            text = getattr(item, "text", None)
            if text:
                return str(text).strip()
    return ""


def split_notices_safe(plain_spatial: str) -> list[dict[str, Any]]:
    """Thin wrapper around ``split_gazette_notices`` with deferred import.

    ``splitting.py`` imports from ``trailing.py``; splitting is a heavy
    module (regex tables), so we keep it out of ``pipeline.py``'s module-
    load path and import on first call. Matches spec section 5 dependency
    graph (``pipeline`` -> ``splitting`` -> ``trailing``).
    """
    from kenya_gazette_parser.splitting import split_gazette_notices
    return split_gazette_notices(plain_spatial)
