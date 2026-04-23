"""Per-notice + per-document confidence scoring (F5/F6).

Lifted verbatim from the notebook. Stdlib-only (``re``, ``collections``).
All scorers operate on plain dicts so scoring has no ``models`` dependency.

Module layout per F20 spec section 2b:

* Public scorers: ``score_notice_number``, ``score_structure``,
  ``score_spatial``, ``score_boundary``, ``score_table``,
  ``composite_confidence``, ``score_notice``, ``score_notices``,
  ``compute_document_confidence``.
* Public triage helpers: ``aggregate_confidence``, ``filter_notices``,
  ``partition_by_band``, ``explain``.
* Private: ``_clip``, ``_estimate_ocr_quality`` (Q4 resolution: the
  document-level OCR score lives with the other confidence helpers).

``_TERMINAL_PUNCT`` and ``_ends_with_terminal_punct`` are duplicated locally
(they also live in ``splitting.py``); duplicating these two tiny primitives
keeps the module stdlib-only and avoids a scoring -> splitting edge in the
dependency graph.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

__all__ = [
    "score_notice_number",
    "score_structure",
    "score_spatial",
    "score_boundary",
    "score_table",
    "composite_confidence",
    "score_notice",
    "score_notices",
    "compute_document_confidence",
    "aggregate_confidence",
    "filter_notices",
    "partition_by_band",
    "explain",
]


_LEGAL_MARKERS = (
    "IN EXERCISE", "IT IS NOTIFIED", "IN PURSUANCE", "PURSUANT TO",
    "WHEREAS", "TAKE NOTICE", "Dated the", "(Cap. ", "(No. ",
)
_SIGNATURE_RE = re.compile(r"^\s*[A-Z][A-Z .,'-]{4,}\s*,?\s*$", re.M)
_DATE_LINE_RE = re.compile(
    r"\bDated\s+the\s+\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4}", re.I
)

_TERMINAL_PUNCT = (".", "!", "?", '"', "'", ")", "]")


def _clip(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _ends_with_terminal_punct(text: str) -> bool:
    s = (text or "").rstrip()
    if not s:
        return False
    return s[-1] in _TERMINAL_PUNCT


def score_notice_number(num: str | None) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if num is None or not str(num).strip():
        return 0.0, ["empty notice number"]
    s = str(num).strip()
    if re.fullmatch(r"\d{2,6}", s):
        return 1.0, []
    if re.fullmatch(r"\d+/\d{4}", s):
        reasons.append("notice number in year/number form")
        return 0.6, reasons
    if re.fullmatch(r"\d+[A-Za-z]", s):
        reasons.append("notice number has trailing letter")
        return 0.5, reasons
    if re.fullmatch(r"\d{7,}", s):
        reasons.append("notice number is unusually long")
        return 0.4, reasons
    if re.fullmatch(r"\d{1}", s):
        reasons.append("single-digit notice number is suspicious")
        return 0.3, reasons
    if re.fullmatch(r"[^\d]+", s):
        reasons.append("notice number has no digits")
        return 0.1, reasons
    reasons.append("notice number has unexpected shape")
    return 0.3, reasons


def score_structure(
    title_lines: list[str],
    body_segments: list[dict[str, Any]],
    derived_table: dict[str, Any] | None,
    text: str,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    body_len = len(text or "")
    non_blank_lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    n_lines = len(non_blank_lines)

    if body_len < 50:
        reasons.append(f"body very short ({body_len} chars)")
        score -= 0.6
    elif body_len < 120:
        reasons.append(f"body short ({body_len} chars)")
        score -= 0.2
    elif body_len > 100_000:
        reasons.append(f"body very long ({body_len} chars) -- possible merge")
        score -= 0.3

    if n_lines <= 2:
        reasons.append("only header/no body content")
        score -= 0.4

    has_marker = any(m.lower() in (text or "").lower() for m in _LEGAL_MARKERS)
    has_date = bool(_DATE_LINE_RE.search(text or ""))
    has_sig = bool(_SIGNATURE_RE.search(text or ""))
    has_table = bool(derived_table) or any(
        s.get("type") == "table" for s in (body_segments or [])
    )
    signals = sum([has_marker, has_date, has_sig])

    if signals == 0 and not has_table:
        reasons.append("no legal marker, date, or signature found")
        score -= 0.3
    elif signals <= 1 and not has_table:
        reasons.append("only one structural marker present")
        score -= 0.1

    if not title_lines:
        reasons.append("no title lines extracted")
        score -= 0.05

    return _clip(score), reasons


def score_spatial(text: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    if not text:
        return 0.0, ["empty text"]

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return _clip(score), reasons

    mid_break = 0
    for i in range(len(lines) - 1):
        cur = lines[i].rstrip()
        nxt = lines[i + 1].lstrip()
        if not cur or not nxt:
            continue
        if cur[-1] in _TERMINAL_PUNCT or cur[-1] in ",;:-":
            continue
        if nxt[:1].islower():
            mid_break += 1
    if mid_break >= 3:
        reasons.append(f"{mid_break} mid-sentence breaks (possible column interleaving)")
        score -= min(0.5, 0.1 * mid_break)

    words = re.findall(r"\w+", text.lower())
    n_words = len(words)
    if n_words > 50:
        grams = [" ".join(words[i:i + 6]) for i in range(n_words - 5)]
        counts = Counter(grams)
        repeats = sum(1 for _, c in counts.items() if c >= 2)
        if repeats >= 3:
            reasons.append(f"{repeats} repeated 6-grams (possible column merge)")
            score -= min(0.3, 0.05 * repeats)

    if n_words > 100:
        mid_cap = 0
        for _m in re.finditer(r"(?<=[a-z]{3})\s+([A-Z][a-z]{3,})", text):
            mid_cap += 1
        density = mid_cap / max(1, n_words)
        if density > 0.10 and mid_cap > 20:
            reasons.append(
                f"high mid-sentence cap density {density:.2f} "
                f"({mid_cap}/{n_words} words)"
            )
            score -= min(0.15, density * 0.5)

    return _clip(score), reasons


def score_boundary(
    header_match: str,
    text: str,
    line_span: tuple[int, int] | list[int],
    next_line_span: tuple[int, int] | list[int] | None,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0

    if header_match == "strict":
        pass
    elif header_match == "recovered":
        reasons.append("header recovered from noisy line (capped at 0.6)")
        score = min(score, 0.6)
    elif header_match == "inferred":
        reasons.append("header inferred (capped at 0.4)")
        score = min(score, 0.4)
    else:
        reasons.append("no notice header found")
        score = min(score, 0.2)

    span_len = 0
    if line_span and len(line_span) == 2:
        span_len = int(line_span[1]) - int(line_span[0])
    if span_len <= 1:
        reasons.append("span is a single line")
        score -= 0.4
    elif span_len < 3:
        reasons.append("span is very short")
        score -= 0.2

    ends_clean = _ends_with_terminal_punct(text or "")
    if not ends_clean:
        reasons.append("text does not end with terminal punctuation")
        score -= 0.15

    if next_line_span and len(next_line_span) == 2 and line_span and len(line_span) == 2:
        gap = int(next_line_span[0]) - int(line_span[1])
        if gap > 20:
            reasons.append(f"gap of {gap} lines to next notice -- possible missing content")
            score -= 0.2

    return _clip(score), reasons


def score_table(derived_table: dict[str, Any] | None) -> tuple[float, list[str]]:
    if not derived_table:
        return 1.0, []
    reasons: list[str] = []
    score = 1.0
    rows = derived_table.get("rows") or []
    if not rows:
        return 0.2, ["derived_table has no rows"]

    repairs = derived_table.get("repairs") or []
    if repairs:
        reasons.append(f"{len(repairs)} merged-row repairs applied")
        score -= min(0.3, 0.05 * len(repairs))

    serials: list[int] = []
    for r in rows:
        m = re.match(r"^(\d+)$", str(r.get("s_no") or "").strip())
        if m:
            serials.append(int(m.group(1)))
    if len(serials) >= 2:
        jumps = sum(1 for a, b in zip(serials, serials[1:]) if b - a != 1)
        if jumps:
            reasons.append(f"{jumps} non-sequential serial jumps")
            score -= min(0.3, 0.05 * jumps)

    name_lens = [len((r.get("name") or "").strip()) for r in rows if r.get("name")]
    if name_lens:
        mean = sum(name_lens) / len(name_lens)
        over = sum(1 for n in name_lens if n > mean * 3)
        if over >= max(1, len(rows) // 10):
            reasons.append("some cells dramatically longer than others (likely merged)")
            score -= 0.15

    return _clip(score), reasons


def composite_confidence(scores: dict[str, float]) -> float:
    """Weighted mean of the rule-based dimensions.

    Weights match ``docs/data-quality-confidence-scoring.md``:
    notice_number 0.30, structure 0.25, spatial 0.25, boundary 0.20.
    ``table`` is folded in (weight 0.15) only when a ``derived_table`` was
    present.
    """
    base = (
        scores.get("notice_number", 0.0) * 0.30
        + scores.get("structure", 0.0) * 0.25
        + scores.get("spatial", 0.0) * 0.25
        + scores.get("boundary", 0.0) * 0.20
    )
    t = scores.get("table")
    if t is None:
        return _clip(base)
    return _clip(base * 0.85 + t * 0.15)


def score_notice(
    entry: dict[str, Any],
    next_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach ``confidence_scores`` and ``confidence_reasons`` to a notice in place."""
    text = entry.get("gazette_notice_full_text") or ""
    prov = entry.get("provenance") or {}
    line_span = prov.get("line_span") or [
        (entry.get("other_attributes") or {}).get("char_span_start_line", 0),
        (entry.get("other_attributes") or {}).get("char_span_end_line", 0),
    ]
    next_line_span = None
    if next_entry is not None:
        np_prov = next_entry.get("provenance") or {}
        next_line_span = np_prov.get("line_span")

    nn_s, nn_r = score_notice_number(entry.get("gazette_notice_no"))
    st_s, st_r = score_structure(
        entry.get("title_lines") or [],
        entry.get("body_segments") or [],
        entry.get("derived_table"),
        text,
    )
    sp_s, sp_r = score_spatial(text)
    bd_s, bd_r = score_boundary(
        prov.get("header_match", "strict"),
        text,
        line_span,
        next_line_span,
    )
    tb_s, tb_r = score_table(entry.get("derived_table"))

    scores: dict[str, float] = {
        "notice_number": round(nn_s, 3),
        "structure": round(st_s, 3),
        "spatial": round(sp_s, 3),
        "boundary": round(bd_s, 3),
    }
    if entry.get("derived_table"):
        scores["table"] = round(tb_s, 3)
    scores["composite"] = round(composite_confidence(scores), 3)

    reasons: list[str] = []
    for prefix, rs in (
        ("notice_number", nn_r), ("structure", st_r), ("spatial", sp_r),
        ("boundary", bd_r), ("table", tb_r if entry.get("derived_table") else []),
    ):
        for msg in rs:
            reasons.append(f"{prefix}: {msg}")

    entry["confidence_scores"] = scores
    entry["confidence_reasons"] = reasons
    return entry


def score_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score a list of notices; uses next-entry context for boundary scoring."""
    for i, entry in enumerate(notices):
        nxt = notices[i + 1] if i + 1 < len(notices) else None
        score_notice(entry, nxt)
    return notices


def compute_document_confidence(
    notices: list[dict[str, Any]],
    layout_confidence: float = 1.0,
    ocr_quality: float = 1.0,
) -> dict[str, Any]:
    """Aggregate per-notice scores into a document-level summary."""
    counts = {"high": 0, "medium": 0, "low": 0}
    composites: list[float] = []
    for n in notices:
        c = (n.get("confidence_scores") or {}).get("composite")
        if c is None:
            continue
        composites.append(float(c))
        if c >= 0.80:
            counts["high"] += 1
        elif c >= 0.50:
            counts["medium"] += 1
        else:
            counts["low"] += 1
    total = len(composites) or 1
    notice_split = 1.0 - (counts["low"] / total)
    composite = (
        (sum(composites) / len(composites)) * 0.6
        + layout_confidence * 0.2
        + ocr_quality * 0.2
    ) if composites else (layout_confidence * 0.5 + ocr_quality * 0.5)
    return {
        "layout": round(_clip(layout_confidence), 3),
        "ocr_quality": round(_clip(ocr_quality), 3),
        "notice_split": round(_clip(notice_split), 3),
        "composite": round(_clip(composite), 3),
        "counts": counts,
        "mean_composite": round(sum(composites) / len(composites), 3) if composites else 0.0,
        "min_composite": round(min(composites), 3) if composites else 0.0,
        "n_notices": len(notices),
    }


def filter_notices(
    notices: list[dict[str, Any]],
    min_composite: float = 0.70,
) -> list[dict[str, Any]]:
    """Return only notices whose composite meets the threshold."""
    out: list[dict[str, Any]] = []
    for n in notices:
        c = (n.get("confidence_scores") or {}).get("composite")
        if c is not None and float(c) >= min_composite:
            out.append(n)
    return out


def partition_by_band(
    notices: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group notices by confidence band (high / medium / low / unscored)."""
    bands: dict[str, list[dict[str, Any]]] = {
        "high": [], "medium": [], "low": [], "unscored": []
    }
    for n in notices:
        c = (n.get("confidence_scores") or {}).get("composite")
        if c is None:
            bands["unscored"].append(n)
        elif c >= 0.80:
            bands["high"].append(n)
        elif c >= 0.50:
            bands["medium"].append(n)
        else:
            bands["low"].append(n)
    return bands


def aggregate_confidence(notices: list[dict[str, Any]]) -> dict[str, float]:
    """Summarize a notice list so analyses can quote a single confidence number."""
    cs: list[float] = [
        float((n.get("confidence_scores") or {}).get("composite"))
        for n in notices
        if (n.get("confidence_scores") or {}).get("composite") is not None
    ]
    if not cs:
        return {"mean": 0.0, "min": 0.0, "fraction_high": 0.0, "n": 0}
    return {
        "mean": round(sum(cs) / len(cs), 3),
        "min": round(min(cs), 3),
        "fraction_high": round(sum(1 for c in cs if c >= 0.80) / len(cs), 3),
        "n": len(cs),
    }


def explain(notice: dict[str, Any]) -> str:
    """Human-readable triage view for a single notice."""
    header = notice.get("gazette_notice_header") or "(no header)"
    no = notice.get("gazette_notice_no") or "?"
    scores = notice.get("confidence_scores") or {}
    reasons = notice.get("confidence_reasons") or []
    prov = notice.get("provenance") or {}
    llm = notice.get("llm_validation") or {}
    parts = [
        f"Notice {no}: {header}",
        f"  header_match={prov.get('header_match', '?')} "
        f"line_span={prov.get('line_span')} "
        f"stitched_from={prov.get('stitched_from') or []}",
        "  scores: " + ", ".join(f"{k}={v}" for k, v in scores.items()),
    ]
    if reasons:
        parts.append("  reasons:")
        for r in reasons:
            parts.append(f"    - {r}")
    if llm:
        parts.append(
            f"  llm: needs_review={llm.get('needs_human_review')} "
            f"issues={llm.get('issues') or []}"
        )
    return "\n".join(parts)


def _estimate_ocr_quality(
    doc_dict: dict[str, Any],
    plain_text: str,
) -> tuple[float, list[str]]:
    """Heuristic OCR-quality score for the whole document.

    Low score = likely a scanned pre-2010 gazette with garbled text. Signals:
      - fraction of non-letter gibberish characters in extracted text,
      - fraction of very short (<3 char) text elements in Docling output,
      - ratio of extractable text length to expected (pages * ~1500 chars).
    """
    reasons: list[str] = []
    if not plain_text:
        return 0.0, ["no extractable text"]

    letters = sum(1 for c in plain_text if c.isalpha())
    total = sum(1 for c in plain_text if not c.isspace())
    letter_ratio = letters / max(1, total)
    if letter_ratio < 0.65:
        reasons.append(f"low letter ratio {letter_ratio:.2f} (possible OCR noise)")

    texts = doc_dict.get("texts") or []
    if texts:
        short_elements = sum(
            1 for t in texts if len((t.get("text") or "").strip()) <= 2
        )
        short_ratio = short_elements / len(texts)
        if short_ratio > 0.25:
            reasons.append(
                f"{short_ratio:.0%} of text elements are 1-2 chars (OCR fragments)"
            )
    else:
        short_ratio = 0.0

    pages = doc_dict.get("pages") or {}
    n_pages = len(pages) if isinstance(pages, dict) else 0
    expected = max(1, n_pages * 1500)
    density = min(1.0, len(plain_text) / expected)
    if density < 0.3:
        reasons.append(f"text density {density:.2f} (sparse -- likely scanned)")

    score = min(letter_ratio * 1.1, 1.0) * 0.5 + (1.0 - short_ratio) * 0.3 + density * 0.2
    return _clip(score), reasons
