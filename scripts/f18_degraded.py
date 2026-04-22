"""F18 T4: four degraded inputs that must each raise pydantic.ValidationError."""

from __future__ import annotations

from pydantic import ValidationError

from kenya_gazette_parser.models import (
    BodySegment,
    Corrigendum,
    DocumentConfidence,
    Notice,
)


def _expect_validation_error(label: str, fn) -> ValidationError:
    try:
        fn()
    except ValidationError as exc:
        return exc
    raise AssertionError(f"{label}: expected ValidationError, none raised")


def main() -> None:
    _expect_validation_error(
        "(a) BodySegment unknown literal",
        lambda: BodySegment(type="heading", text="X", page_no=1),  # type: ignore[arg-type]
    )

    _expect_validation_error(
        "(b) DocumentConfidence invalid counts key",
        lambda: DocumentConfidence(
            layout=1.0,
            ocr_quality=1.0,
            notice_split=1.0,
            composite=1.0,
            counts={"unknown_tier": 5},  # type: ignore[arg-type]
            mean_composite=0.0,
            min_composite=0.0,
            n_notices=0,
        ),
    )

    valid_notice = {
        "notice_id": "KE-GAZ-X-1-2026-01-01:1",
        "gazette_issue_id": "KE-GAZ-X-1-2026-01-01",
        "title_lines": ["A Title"],
        "gazette_notice_full_text": "Body text.",
        "body_segments": [{"type": "text", "lines": ["Body text."]}],
        "other_attributes": {},
        "provenance": {"header_match": "strict", "line_span": [0, 1]},
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
    err_c = _expect_validation_error(
        "(c) Notice with stray top-level key",
        lambda: Notice.model_validate({**valid_notice, "unknown_field": "x"}),
    )
    err_c_str = str(err_c)
    assert "unknown_field" in err_c_str, (
        f"(c) error string missing 'unknown_field': {err_c_str}"
    )
    assert "extra_forbidden" in err_c_str, (
        f"(c) error string missing 'extra_forbidden': {err_c_str}"
    )

    _expect_validation_error(
        "(d) Corrigendum invalid scope literal",
        lambda: Corrigendum(
            scope="bogus",  # type: ignore[arg-type]
            raw_text="...",
            provenance={"header_match": "strict", "line_span": [0, 1]},  # type: ignore[arg-type]
        ),
    )

    print("T4 OK")


if __name__ == "__main__":
    main()
