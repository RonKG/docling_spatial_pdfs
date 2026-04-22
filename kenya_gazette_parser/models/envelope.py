"""Top-level Envelope and supporting models for kenya_gazette_parser.

Note: ``Warning`` shadows the Python built-in ``Warning``; callers mixing both
should import as ``from kenya_gazette_parser.models import Warning as GazetteWarning``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from kenya_gazette_parser.models.base import StrictBase
from kenya_gazette_parser.models.notice import Corrigendum, Notice


class GazetteIssue(StrictBase):
    gazette_issue_id: str
    masthead_text: str
    parse_confidence: float
    volume: str | None = None
    issue_no: int | None = None
    publication_date: date | None = None
    supplement_no: int | None = None


class DocumentConfidence(StrictBase):
    layout: float
    ocr_quality: float
    notice_split: float
    composite: float
    counts: dict[Literal["high", "medium", "low"], int]
    mean_composite: float
    min_composite: float
    n_notices: int
    ocr_reasons: list[str] = []


class LayoutInfo(StrictBase):
    layout_confidence: float
    pages: list[dict[str, Any]]


class Warning(StrictBase):
    kind: str
    message: str
    where: dict[str, Any] | None = None


class Cost(StrictBase):
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    usd_estimate: float | None = None


class Envelope(StrictBase):
    library_version: str
    schema_version: str
    output_format_version: int
    extracted_at: datetime
    pdf_sha256: str
    issue: GazetteIssue
    notices: list[Notice]
    corrigenda: list[Corrigendum]
    document_confidence: DocumentConfidence
    layout_info: LayoutInfo
    warnings: list[Warning]
    cost: Cost | None = None
