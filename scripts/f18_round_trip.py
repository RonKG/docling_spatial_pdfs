"""F18 T5: model_dump(mode='json') round-trip preserves the source dict."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f18_validate_real_notice import adapt_notice_to_contract  # noqa: E402

from kenya_gazette_parser.models import Envelope, Notice  # noqa: E402

REAL_JSON = Path(
    "output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json"
)


def _normalize(d: dict) -> dict:
    return json.loads(json.dumps(d))


def main() -> None:
    with REAL_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    notice = data["gazette_notices"][0]
    notice["content_sha256"] = hashlib.sha256(
        notice["gazette_notice_full_text"].encode("utf-8")
    ).hexdigest()
    adapt_notice_to_contract(notice)

    before_notice = _normalize(notice)
    # exclude_unset keeps optional keys out of the dump when they weren't in
    # the source (e.g. derived_table, gazette_notice_no=None defaults). This
    # is the correct shape for round-trip equality against the source dict.
    after_notice = Notice.model_validate(notice).model_dump(
        mode="json", exclude_unset=True
    )
    assert before_notice == after_notice, (
        "Notice round-trip mismatch.\n"
        f"only-in-before: {set(before_notice) - set(after_notice)}\n"
        f"only-in-after:  {set(after_notice) - set(before_notice)}"
    )

    envelope_dict: dict = {
        "library_version": "0.1.0",
        "schema_version": "1.0",
        "output_format_version": 1,
        "extracted_at": "2026-04-20T03:35:08Z",
        "pdf_sha256": "a" * 64,
        "issue": {
            "gazette_issue_id": "KE-GAZ-CXXIV-282-2022-12-23",
            "masthead_text": "MASTHEAD",
            "parse_confidence": 0.95,
            "volume": "CXXIV",
            "issue_no": 282,
            "publication_date": "2022-12-23",
            "supplement_no": None,
        },
        "notices": [],
        "corrigenda": [],
        "document_confidence": {
            "layout": 1.0,
            "ocr_quality": 1.0,
            "notice_split": 1.0,
            "composite": 1.0,
            "counts": {"high": 1, "medium": 0, "low": 0},
            "mean_composite": 1.0,
            "min_composite": 1.0,
            "n_notices": 1,
            "ocr_reasons": [],
        },
        "layout_info": {"layout_confidence": 1.0, "pages": []},
        "warnings": [],
        "cost": None,
    }

    env_obj = Envelope.model_validate(envelope_dict)
    after_env = env_obj.model_dump(mode="json")

    expected_env = _normalize(envelope_dict)

    assert expected_env == after_env, (
        "Envelope round-trip mismatch.\n"
        f"expected: {expected_env}\n"
        f"after:    {after_env}"
    )
    assert after_env["issue"]["publication_date"] == "2022-12-23", (
        f"publication_date round-trip failed: {after_env['issue']['publication_date']}"
    )

    print("T5 OK")


if __name__ == "__main__":
    main()
