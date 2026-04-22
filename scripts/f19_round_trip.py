r"""F19 T4: round-trip every canonical ``_gazette_spatial.json`` through ``Envelope.model_validate``.

After F19 lands, each ``output/<stem>/<stem>_gazette_spatial.json`` is the
nested-shape Envelope dump. We re-load each file, validate via
``Envelope.model_validate``, and assert the contract invariants the spec
requires:

- ``output_format_version == 1``
- ``pdf_sha256`` is 64-hex
- every ``Notice.content_sha256`` is 64-hex
- every ``BodySegment.type`` is in ``{"text", "blank"}`` (proves carry-over 1)
- ``env.issue.gazette_issue_id == record["issue"]["gazette_issue_id"]``

Prints ``T4 OK (6/6)`` on success and exits non-zero on any failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from kenya_gazette_parser.models import Envelope

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"

CANONICAL_STEMS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]

HEX64 = re.compile(r"[0-9a-f]{64}")


def _check_one(stem: str) -> None:
    path = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
    if not path.exists():
        raise AssertionError(f"missing output file for {stem!r}: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    env = Envelope.model_validate(data)

    assert env.output_format_version == 1, (
        f"{stem}: output_format_version={env.output_format_version}"
    )
    assert HEX64.fullmatch(env.pdf_sha256), (
        f"{stem}: pdf_sha256 not 64-hex: {env.pdf_sha256!r}"
    )
    for i, n in enumerate(env.notices):
        assert HEX64.fullmatch(n.content_sha256), (
            f"{stem}: notice[{i}].content_sha256 not 64-hex: "
            f"{n.content_sha256!r}"
        )
        for j, seg in enumerate(n.body_segments):
            assert seg.type in {"text", "blank"}, (
                f"{stem}: notice[{i}].body_segments[{j}].type={seg.type!r}"
            )
    assert env.issue.gazette_issue_id == data["issue"]["gazette_issue_id"], (
        f"{stem}: issue.gazette_issue_id mismatch"
    )


def main() -> int:
    ok = 0
    failures: list[str] = []
    for stem in CANONICAL_STEMS:
        try:
            _check_one(stem)
        except Exception as exc:
            failures.append(f"{stem}: {exc}")
            print(f"FAIL {stem}: {exc}")
            continue
        ok += 1
        print(f"OK   {stem}")

    total = len(CANONICAL_STEMS)
    if failures:
        print(f"\nT4 FAIL ({ok}/{total})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nT4 OK ({ok}/{total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
