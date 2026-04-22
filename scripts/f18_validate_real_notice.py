"""F18 T2: validate the first real notice from a known _gazette_spatial.json.

After F19 landed, the on-disk ``_gazette_spatial.json`` is in nested Envelope
shape (``notices`` instead of ``gazette_notices``) and every notice already
carries a ``content_sha256`` stamped by ``process_pdf``. The original
``adapt_notice_to_contract`` helper is retained as an identity function for
backward compatibility: F19 fixed body-segment shape at source, so there is
nothing to adapt at read time anymore.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kenya_gazette_parser.models import Notice

REAL_JSON = Path(
    "output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json"
)


def adapt_notice_to_contract(notice: dict) -> dict:
    # F19 fixed body-segment shape at source; helper retained as identity for backward compatibility.
    return notice


def main() -> None:
    with REAL_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    notices = data.get("notices") or data.get("gazette_notices") or []
    notice = notices[0]
    notice["content_sha256"] = hashlib.sha256(
        notice["gazette_notice_full_text"].encode("utf-8")
    ).hexdigest()
    adapt_notice_to_contract(notice)

    notice_obj = Notice.model_validate(notice)

    assert (
        notice_obj.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"
    ), f"unexpected gazette_issue_id: {notice_obj.gazette_issue_id}"
    assert (
        notice_obj.provenance.header_match == "strict"
    ), f"unexpected header_match: {notice_obj.provenance.header_match}"
    assert notice_obj.body_segments[0].type in {
        "text",
        "blank",
    }, f"unexpected body_segments[0].type: {notice_obj.body_segments[0].type}"

    print("T2 OK")


if __name__ == "__main__":
    main()
