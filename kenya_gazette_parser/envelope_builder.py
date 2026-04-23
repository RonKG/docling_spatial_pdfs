"""Flat-to-nested envelope adapter (F19).

Turns the flat record emitted by the pipeline orchestration into the nested
shape the ``Envelope`` Pydantic model accepts. Dict-in / dict-out: no model
imports here. The adapter:

* drops pipeline-internal keys (``pdf_title``, ``pdf_file_name``, ``pages``,
  ``docling``, ...);
* nests issue fields under ``"issue"``;
* renames ``gazette_notices`` -> ``notices``;
* passes ``layout_info`` through verbatim (F20 D2 fix: the source no longer
  emits ``n_pages``, so the old F19 prune step is gone);
* synthesizes a sentinel ``scope="notice_references_other"`` + placeholder
  ``Provenance`` for every corrigendum, paired with one
  ``Warning(kind="corrigendum_scope_defaulted", ...)`` (F31 bridge);
* coerces ``type="table"`` body segments to ``"text"`` + paired
  ``Warning(kind="table_coerced_to_text", ...)`` (M5 bridge);
* stamps ``output_format_version=1``;
* raises ``KeyError`` on any unknown top-level key so contract drift cannot
  leak silently.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_envelope_dict"]


def build_envelope_dict(record_flat: dict[str, Any]) -> dict[str, Any]:
    """Transform the flat ``pipeline.build_envelope`` record into contract-``Envelope`` shape."""
    _DROP = {
        "pdf_title", "pdf_file_name", "pdf_path", "pdf_size_bytes",
        "pages", "docling", "gazette_issue_id",
    }
    _PASS = {
        "pdf_sha256", "library_version", "schema_version", "extracted_at",
        "warnings", "document_confidence", "layout_info",
    }
    _ISSUE = {
        "volume", "issue_no", "publication_date", "supplement_no",
        "masthead_text", "parse_confidence",
    }
    _OTHER = {"corrigenda", "gazette_notices"}

    expected = _DROP | _PASS | _ISSUE | _OTHER
    unknown = set(record_flat.keys()) - expected
    if unknown:
        raise KeyError(
            f"build_envelope_dict: unknown top-level key(s) {sorted(unknown)}"
        )

    warnings_out: list[dict[str, Any]] = [
        dict(w) for w in (record_flat.get("warnings") or [])
    ]

    corrigenda_out: list[dict[str, Any]] = []
    for cor in record_flat.get("corrigenda") or []:
        target_notice_no = cor.get("referenced_notice_no")
        target_year_raw = cor.get("referenced_year")
        if target_year_raw is None:
            target_year: int | None = None
        else:
            target_year = int(target_year_raw)
        corrigenda_out.append({
            "scope": "notice_references_other",
            "raw_text": cor.get("raw_text", ""),
            "provenance": {
                "header_match": "inferred",
                "line_span": [0, 0],
                "raw_header_line": None,
                "stitched_from": [],
            },
            "target_notice_no": target_notice_no,
            "target_year": target_year,
            "amendment": cor.get("correction_text"),
        })
        warnings_out.append({
            "kind": "corrigendum_scope_defaulted",
            "message": (
                "Corrigendum scope and provenance defaulted; real extraction "
                "deferred to F31"
            ),
            "where": {"notice_no": target_notice_no, "page_no": None},
        })

    notices_out: list[dict[str, Any]] = []
    for n in record_flat.get("gazette_notices") or []:
        n_out = dict(n)
        segments_out: list[dict[str, Any]] = []
        for seg in n_out.get("body_segments") or []:
            if seg.get("type") == "table":
                segments_out.append({
                    "type": "text",
                    "lines": list(seg.get("raw_lines") or []),
                })
                warnings_out.append({
                    "kind": "table_coerced_to_text",
                    "message": (
                        "Table body segment coerced to text; richer table "
                        "segment type deferred to roadmap M5"
                    ),
                    "where": {
                        "notice_no": n_out.get("gazette_notice_no"),
                        "notice_id": n_out.get("notice_id"),
                    },
                })
            else:
                segments_out.append(seg)
        n_out["body_segments"] = segments_out
        notices_out.append(n_out)

    issue = {
        "gazette_issue_id": record_flat["gazette_issue_id"],
        "masthead_text": record_flat["masthead_text"],
        "parse_confidence": record_flat["parse_confidence"],
        "volume": record_flat.get("volume"),
        "issue_no": record_flat.get("issue_no"),
        "publication_date": record_flat.get("publication_date"),
        "supplement_no": record_flat.get("supplement_no"),
    }

    return {
        "library_version": record_flat["library_version"],
        "schema_version": record_flat["schema_version"],
        "output_format_version": 1,
        "extracted_at": record_flat["extracted_at"],
        "pdf_sha256": record_flat["pdf_sha256"],
        "issue": issue,
        "notices": notices_out,
        "corrigenda": corrigenda_out,
        "document_confidence": record_flat["document_confidence"],
        "layout_info": record_flat["layout_info"],
        "warnings": warnings_out,
    }
