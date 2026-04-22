"""F18 T3: minimal Notice and Envelope with all optional fields omitted."""

from __future__ import annotations

from kenya_gazette_parser.models import Envelope, Notice


def main() -> None:
    minimal_notice_dict: dict = {
        "notice_id": "KE-GAZ-X-1-2026-01-01:1",
        "gazette_issue_id": "KE-GAZ-X-1-2026-01-01",
        "title_lines": ["A Title"],
        "gazette_notice_full_text": "Body text.",
        "body_segments": [{"type": "text", "lines": ["Body text."]}],
        "other_attributes": {},
        "provenance": {
            "header_match": "strict",
            "line_span": [0, 1],
        },
        "confidence_scores": {
            "notice_number": 1.0,
            "structure": 1.0,
            "spatial": 1.0,
            "boundary": 1.0,
            "composite": 1.0,
        },
        "confidence_reasons": [],
        "content_sha256": "0" * 64,
    }

    notice_obj = Notice.model_validate(minimal_notice_dict)
    assert notice_obj.gazette_notice_no is None, "expected gazette_notice_no None"
    assert notice_obj.gazette_notice_header is None, "expected gazette_notice_header None"
    assert notice_obj.derived_table is None, "expected derived_table None"

    minimal_envelope_dict: dict = {
        "library_version": "0.1.0",
        "schema_version": "1.0",
        "output_format_version": 1,
        "extracted_at": "2026-04-21T00:00:00Z",
        "pdf_sha256": "0" * 64,
        "issue": {
            "gazette_issue_id": "KE-GAZ-X-1-2026-01-01",
            "masthead_text": "MASTHEAD",
            "parse_confidence": 1.0,
        },
        "notices": [],
        "corrigenda": [],
        "document_confidence": {
            "layout": 1.0,
            "ocr_quality": 1.0,
            "notice_split": 1.0,
            "composite": 1.0,
            "counts": {"high": 0, "medium": 0, "low": 0},
            "mean_composite": 0.0,
            "min_composite": 0.0,
            "n_notices": 0,
        },
        "layout_info": {
            "layout_confidence": 1.0,
            "pages": [],
        },
        "warnings": [],
    }

    env = Envelope.model_validate(minimal_envelope_dict)
    assert env.cost is None, "expected cost None"
    assert env.notices == [], "expected notices empty list"
    assert env.corrigenda == [], "expected corrigenda empty list"
    assert env.warnings == [], "expected warnings empty list"

    print("T3 OK")


if __name__ == "__main__":
    main()
