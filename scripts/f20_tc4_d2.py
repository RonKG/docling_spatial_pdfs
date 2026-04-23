"""F20 TC4: D2 ``n_pages`` source fix + adapter pass-through unit check.

Two halves:

1. Call ``spatial.reorder_by_spatial_position_with_confidence`` on a handcrafted
   Docling-shaped dict and assert the returned info contains exactly the two
   contract-compliant keys ``{"layout_confidence", "pages"}`` (no stray
   ``"n_pages"``).
2. Feed ``envelope_builder.build_envelope_dict`` a handcrafted flat record
   with ``layout_info = {"layout_confidence": 0.5, "pages": []}`` and assert
   the returned envelope dict's ``layout_info`` is an identity pass-through.

No PDFs required. Pure-function unit test.
"""

from __future__ import annotations

import sys

from kenya_gazette_parser.envelope_builder import build_envelope_dict
from kenya_gazette_parser.spatial import reorder_by_spatial_position_with_confidence


def tc4_part1() -> bool:
    doc_dict = {
        "schema_name": "DoclingDocument",
        "version": "1.0",
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "content_layer": "body",
                "text": "GAZETTE NOTICE NO. 1",
                "prov": [{
                    "page_no": 1,
                    "bbox": {"l": 50, "t": 700, "r": 250, "b": 680},
                }],
            },
            {
                "self_ref": "#/texts/1",
                "label": "text",
                "content_layer": "body",
                "text": "A short body paragraph.",
                "prov": [{
                    "page_no": 1,
                    "bbox": {"l": 50, "t": 670, "r": 250, "b": 650},
                }],
            },
        ],
        "pages": {"1": {"page_no": 1, "size": {"width": 595, "height": 842}}},
    }
    text, info = reorder_by_spatial_position_with_confidence(doc_dict)
    keys = set(info.keys())
    expected = {"layout_confidence", "pages"}
    ok_keys = keys == expected
    ok_no_n_pages = "n_pages" not in info
    print(f"  reorder returned keys: {sorted(keys)}")
    print(f"  keys == {sorted(expected)}: {ok_keys}")
    print(f"  'n_pages' not in info:   {ok_no_n_pages}")
    return ok_keys and ok_no_n_pages


def tc4_part2() -> bool:
    flat = {
        "pdf_title": "Fake",
        "pdf_file_name": "Fake.pdf",
        "pdf_path": "Fake.pdf",
        "pdf_size_bytes": 0,
        "pdf_sha256": "0" * 64,
        "gazette_issue_id": "KE-GAZ-UNKNOWN-000000000000",
        "library_version": "0.1.0",
        "schema_version": "1.0",
        "extracted_at": "2026-04-21T00:00:00Z",
        "warnings": [],
        "pages": 1,
        "volume": None,
        "issue_no": None,
        "publication_date": None,
        "supplement_no": None,
        "masthead_text": "",
        "parse_confidence": 0.0,
        "document_confidence": {
            "layout": 1.0, "ocr_quality": 1.0, "notice_split": 1.0,
            "composite": 1.0,
            "counts": {"high": 0, "medium": 0, "low": 0},
            "mean_composite": 0.0, "min_composite": 0.0, "n_notices": 0,
            "ocr_reasons": [],
        },
        "layout_info": {"layout_confidence": 0.5, "pages": []},
        "docling": {},
        "corrigenda": [],
        "gazette_notices": [],
    }
    env_dict = build_envelope_dict(flat)
    returned = env_dict["layout_info"]
    ok_identity = returned is flat["layout_info"]
    ok_keys = set(returned.keys()) == {"layout_confidence", "pages"}
    ok_no_synth = "n_pages" not in returned and len(returned) == 2
    print(f"  adapter returned layout_info: {returned}")
    print(f"  same object as input ('is' check): {ok_identity}")
    print(f"  keys == {{'layout_confidence','pages'}}:    {ok_keys}")
    print(f"  no synthesized/dropped keys:              {ok_no_synth}")
    return ok_identity and ok_keys and ok_no_synth


def main() -> int:
    print("TC4 Part 1: reorder_by_spatial_position_with_confidence drops n_pages")
    part1 = tc4_part1()
    print("TC4 Part 1:", "PASS" if part1 else "FAIL")
    print()
    print("TC4 Part 2: build_envelope_dict passes layout_info through verbatim")
    part2 = tc4_part2()
    print("TC4 Part 2:", "PASS" if part2 else "FAIL")
    return 0 if (part1 and part2) else 1


if __name__ == "__main__":
    sys.exit(main())
