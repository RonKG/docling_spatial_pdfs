"""Notice and supporting models for kenya_gazette_parser."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from kenya_gazette_parser.models.base import StrictBase


class BodySegment(StrictBase):
    type: Literal["text", "blank"]
    lines: list[str]


class DerivedTable(StrictBase):
    # Sole exception to extra="forbid": the 2.x richer table schema can add
    # fields without breaking 1.0 consumers. Every other model in this package
    # is strict.
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        str_strip_whitespace=False,
    )

    rows: list[list[str]]
    columns: list[str] | None = None
    notice_id: str | None = None


class Provenance(StrictBase):
    header_match: Literal["strict", "recovered", "inferred", "none"]
    line_span: tuple[int, int]
    raw_header_line: str | None = None
    stitched_from: list[str] = Field(default_factory=list)
    ocr_quality: float | None = None


class ConfidenceScores(StrictBase):
    notice_number: float
    structure: float
    spatial: float
    boundary: float
    composite: float
    table: float | None = None


class Corrigendum(StrictBase):
    scope: Literal[
        "issue_level",
        "notice_is_corrigendum",
        "notice_references_other",
    ]
    raw_text: str
    provenance: Provenance
    target_notice_no: str | None = None
    target_year: int | None = None
    amendment: str | None = None


class Notice(StrictBase):
    notice_id: str
    gazette_issue_id: str
    title_lines: list[str]
    gazette_notice_full_text: str
    body_segments: list[BodySegment]
    other_attributes: dict[str, Any]
    provenance: Provenance
    confidence_scores: ConfidenceScores
    confidence_reasons: list[str]
    content_sha256: str
    gazette_notice_no: str | None = None
    gazette_notice_header: str | None = None
    derived_table: DerivedTable | None = None
