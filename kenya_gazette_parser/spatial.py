"""Spatial reading-order reorder + per-page layout confidence (F2).

Lifted verbatim from the notebook. Stdlib-only imports.

D2 source fix (F20): ``reorder_by_spatial_position_with_confidence`` no
longer emits an ``n_pages`` key in its returned info dict. Callers that want
the page count can read ``len(info["pages"])``. The contract ``LayoutInfo``
model only accepts ``{layout_confidence, pages}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "reorder_by_spatial_position",
    "reorder_by_spatial_position_with_confidence",
    "compute_page_layout_confidence",
]


@dataclass
class _BBoxElement:
    """Lightweight carrier for a text/table element with its spatial position."""

    page_no: int
    label: str
    content_layer: str
    text: str
    left: float
    top: float
    right: float
    bottom: float
    center_x: float
    self_ref: str

    @property
    def width(self) -> float:
        return self.right - self.left


def _table_to_text(data: dict[str, Any]) -> str:
    """Build a pipe-delimited text representation of a table from its grid data."""
    grid = data.get("grid")
    if not grid:
        cells = data.get("table_cells") or []
        return " | ".join(c.get("text", "") for c in cells if c.get("text"))
    rows: list[str] = []
    for row in grid:
        cols = [cell.get("text", "") for cell in row]
        rows.append(" | ".join(cols))
    return "\n".join(rows)


def _extract_elements(doc_dict: dict[str, Any]) -> list[_BBoxElement]:
    """Pull every text and table element that has provenance bbox data."""
    elements: list[_BBoxElement] = []

    for item in doc_dict.get("texts") or []:
        provs = item.get("prov") or []
        if not provs:
            continue
        prov = provs[0]
        bbox = prov.get("bbox")
        if not bbox:
            continue
        text = item.get("text") or item.get("orig") or ""
        if not text.strip():
            continue
        l, t, r, b = bbox["l"], bbox["t"], bbox["r"], bbox["b"]
        elements.append(_BBoxElement(
            page_no=prov["page_no"],
            label=item.get("label", "text"),
            content_layer=item.get("content_layer", "body"),
            text=text,
            left=l, top=t, right=r, bottom=b,
            center_x=(l + r) / 2,
            self_ref=item.get("self_ref", ""),
        ))

    for item in doc_dict.get("tables") or []:
        provs = item.get("prov") or []
        if not provs:
            continue
        prov = provs[0]
        bbox = prov.get("bbox")
        if not bbox:
            continue
        text = _table_to_text(item.get("data") or {})
        if not text.strip():
            continue
        l, t, r, b = bbox["l"], bbox["t"], bbox["r"], bbox["b"]
        elements.append(_BBoxElement(
            page_no=prov["page_no"],
            label="table",
            content_layer=item.get("content_layer", "body"),
            text=text,
            left=l, top=t, right=r, bottom=b,
            center_x=(l + r) / 2,
            self_ref=item.get("self_ref", ""),
        ))

    return elements


def _get_page_dimensions(doc_dict: dict[str, Any]) -> dict[int, tuple[float, float]]:
    """Return ``{page_no: (width, height)}`` from the pages map."""
    dims: dict[int, tuple[float, float]] = {}
    pages = doc_dict.get("pages") or {}
    for _key, pinfo in pages.items():
        sz = pinfo.get("size") or {}
        pno = pinfo.get("page_no")
        if pno is not None and sz:
            dims[pno] = (sz.get("width", 595.0), sz.get("height", 842.0))
    return dims


_FULLWIDTH_RATIO = 0.55
_FW_TRANSITION_TOLERANCE = 50.0


def _reorder_page(
    page_elements: list[_BBoxElement],
    page_width: float,
) -> list[_BBoxElement]:
    """Reorder elements on a single page: left col -> right col -> full-width bottom."""
    mid_x = page_width / 2.0
    text_area_width = page_width - 100

    furniture: list[_BBoxElement] = []
    left_candidates: list[_BBoxElement] = []
    right_candidates: list[_BBoxElement] = []
    full_width: list[_BBoxElement] = []

    for el in page_elements:
        if el.content_layer == "furniture":
            furniture.append(el)
            continue

        clearly_right = el.left >= mid_x
        clearly_left = el.right <= mid_x
        spans_both = el.left < mid_x and el.right > mid_x
        wide_enough = el.width > text_area_width * _FULLWIDTH_RATIO
        centered = (spans_both
                    and not wide_enough
                    and abs(el.center_x - mid_x) < 80
                    and el.width < text_area_width * 0.45)

        if spans_both and wide_enough:
            full_width.append(el)
        elif centered:
            full_width.append(el)
        elif clearly_right:
            right_candidates.append(el)
        elif clearly_left:
            left_candidates.append(el)
        elif el.center_x < mid_x:
            left_candidates.append(el)
        else:
            right_candidates.append(el)

    if not left_candidates or not right_candidates:
        all_body = left_candidates + right_candidates + full_width
        all_body.sort(key=lambda el: -el.top)
        return furniture + all_body

    fw_body = [el for el in full_width if el.content_layer != "furniture"]
    fw_transition_y: float | None = None

    if fw_body:
        fw_transition_y = max(el.top for el in fw_body)
        col_tops = [el.top for el in left_candidates + right_candidates]
        if col_tops:
            col_tops_sorted = sorted(col_tops, reverse=True)
            median_top = col_tops_sorted[len(col_tops_sorted) // 2]
            if fw_transition_y >= median_top:
                fw_transition_y = None

    if fw_transition_y is not None:
        threshold = fw_transition_y + _FW_TRANSITION_TOLERANCE
        left_col: list[_BBoxElement] = []
        for el in left_candidates:
            if el.top <= threshold:
                full_width.append(el)
            else:
                left_col.append(el)
        right_col: list[_BBoxElement] = []
        for el in right_candidates:
            if el.top <= threshold:
                full_width.append(el)
            else:
                right_col.append(el)
    else:
        left_col = list(left_candidates)
        right_col = list(right_candidates)
        if left_col and right_col:
            left_bottom = min(el.bottom for el in left_col)
            right_bottom = min(el.bottom for el in right_col)
            col_zone_bottom = max(left_bottom, right_bottom)
            left_col = [el for el in left_col if el.top >= col_zone_bottom]
            full_width.extend(
                el for el in left_candidates if el.top < col_zone_bottom
            )
            right_col = [el for el in right_col if el.top >= col_zone_bottom]
            full_width.extend(
                el for el in right_candidates if el.top < col_zone_bottom
            )

    key_y = lambda el: -el.top
    furniture.sort(key=key_y)
    left_col.sort(key=key_y)
    right_col.sort(key=key_y)
    full_width.sort(key=key_y)

    return furniture + left_col + right_col + full_width


def _cluster_y_bands(
    page_elements: list[_BBoxElement],
    gap_multiplier: float = 1.5,
) -> list[list[_BBoxElement]]:
    """Cluster elements into y-bands separated by vertical gaps."""
    body = [el for el in page_elements if el.content_layer != "furniture"]
    if not body:
        return []
    sorted_els = sorted(body, key=lambda e: -e.top)
    bands: list[list[_BBoxElement]] = []
    current: list[_BBoxElement] = [sorted_els[0]]
    for el in sorted_els[1:]:
        prev_band_bottom = min(b.bottom for b in current)
        height = max((b.top - b.bottom) for b in current) or 10.0
        gap = prev_band_bottom - el.top
        if gap > height * gap_multiplier:
            bands.append(current)
            current = [el]
        else:
            current.append(el)
    bands.append(current)
    return bands


def _classify_band(
    band: list[_BBoxElement],
    page_width: float,
) -> tuple[str, float]:
    """Classify a band as ``'one_col'``, ``'two_col'``, ``'full_width'``, or ``'mixed'``."""
    if not band:
        return "empty", 1.0
    mid = page_width / 2.0
    text_width = page_width - 100
    wide = [el for el in band if el.width > text_width * _FULLWIDTH_RATIO]
    if len(wide) >= max(1, len(band) // 2):
        if len(wide) == len(band):
            return "full_width", 1.0
        return "full_width", 0.8

    clearly_left = sum(1 for el in band if el.right <= mid)
    clearly_right = sum(1 for el in band if el.left >= mid)
    ambiguous = len(band) - clearly_left - clearly_right - len(wide)

    if clearly_left == 0 or clearly_right == 0:
        conf = 1.0 - (ambiguous / max(1, len(band)))
        return "one_col", max(0.5, conf)

    total = len(band)
    clear = clearly_left + clearly_right
    conf = clear / total
    if ambiguous / total > 0.3:
        return "mixed", max(0.3, conf)
    return "two_col", conf


def compute_page_layout_confidence(
    page_elements: list[_BBoxElement],
    page_width: float,
) -> dict[str, Any]:
    """Per-page layout confidence summary."""
    bands = _cluster_y_bands(page_elements)
    if not bands:
        return {"layout_confidence": 1.0, "bands": [], "mode": "empty"}
    band_infos: list[dict[str, Any]] = []
    weighted_conf = 0.0
    total_weight = 0
    modes: dict[str, int] = {}
    for band in bands:
        label, conf = _classify_band(band, page_width)
        weight = len(band)
        band_infos.append({"mode": label, "confidence": round(conf, 3), "n_elements": weight})
        weighted_conf += conf * weight
        total_weight += weight
        modes[label] = modes.get(label, 0) + 1
    avg = weighted_conf / max(1, total_weight)
    mode_label = max(modes.items(), key=lambda kv: kv[1])[0] if modes else "unknown"
    if len(modes) > 1:
        mode_label = f"hybrid ({mode_label} dominant)"
    return {
        "layout_confidence": round(avg, 3),
        "bands": band_infos,
        "mode": mode_label,
        "n_bands": len(bands),
    }


def reorder_by_spatial_position_with_confidence(
    doc_dict: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Reorder text elements by spatial position AND emit a layout-confidence report.

    Returns ``(plain_text, info)`` where ``info`` contains per-page layout
    confidence under ``"pages"`` plus the document-level aggregate under
    ``"layout_confidence"``. The returned dict is contract-compliant
    (``LayoutInfo`` accepts exactly those two keys); callers that want a page
    tally compute ``len(info["pages"])``.
    """
    elements = _extract_elements(doc_dict)
    dims = _get_page_dimensions(doc_dict)

    by_page: dict[int, list[_BBoxElement]] = {}
    for el in elements:
        by_page.setdefault(el.page_no, []).append(el)

    page_texts: list[str] = []
    page_infos: list[dict[str, Any]] = []
    weighted_sum = 0.0
    weight_total = 0
    for page_no in sorted(by_page):
        pw, _ph = dims.get(page_no, (595.0, 842.0))
        page_els = by_page[page_no]
        info = compute_page_layout_confidence(page_els, pw)
        info["page_no"] = page_no
        page_infos.append(info)
        ordered = _reorder_page(page_els, pw)
        page_texts.append(
            "\n\n".join(el.text for el in ordered if el.content_layer != "furniture")
        )
        n_body = sum(1 for el in page_els if el.content_layer != "furniture")
        weighted_sum += info["layout_confidence"] * n_body
        weight_total += n_body

    doc_layout_conf = weighted_sum / max(1, weight_total) if weight_total else 1.0
    return (
        "\n\n".join(page_texts),
        {
            "layout_confidence": round(doc_layout_conf, 3),
            "pages": page_infos,
        },
    )


def reorder_by_spatial_position(doc_dict: dict[str, Any]) -> str:
    """Backward-compatible wrapper: reorder and return only plain text.

    For two-column pages the reading order becomes:
      page header -> left column (top-to-bottom) -> right column
      (top-to-bottom) -> full-width zone at page bottom (top-to-bottom).
    Single-column pages are simply sorted top-to-bottom.
    """
    text, _info = reorder_by_spatial_position_with_confidence(doc_dict)
    return text
