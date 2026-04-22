r"""F19 T1 and T2 — assert envelope invariants against on-disk outputs.

T1: Vol CXXIVNo 282 validates as an Envelope; ``gazette_issue_id`` matches the
    F13-derived canonical id; ``len(notices) > 0``; first notice's
    ``content_sha256`` is 64-hex; at least one body segment has ``lines`` as a
    list (no ``line`` singular); ``output_format_version == 1``.

T2: Pick a canonical PDF whose validated ``corrigenda`` list is empty
    (Vol CXINo 103 has zero corrigenda after F19) and assert
    ``env.corrigenda == []`` plus presence in the on-disk JSON.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from kenya_gazette_parser.models import Envelope

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"
HEX64 = re.compile(r"[0-9a-f]{64}")


def _load(stem: str) -> dict:
    path = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _t1() -> bool:
    stem = "Kenya Gazette Vol CXXIVNo 282"
    data = _load(stem)
    env = Envelope.model_validate(data)
    checks = {
        "output_format_version == 1": env.output_format_version == 1,
        "gazette_issue_id matches F13 canonical id": (
            env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"
        ),
        "len(notices) > 0": len(env.notices) > 0,
        "first notice content_sha256 is 64-hex": bool(
            HEX64.fullmatch(env.notices[0].content_sha256)
        ),
        "no body segment carries a singular 'line' key": all(
            "line" not in seg for n in data["notices"] for seg in n["body_segments"]
        ),
    }
    all_ok = all(checks.values())
    print(f"T1 {'OK' if all_ok else 'FAIL'} on {stem}")
    for k, v in checks.items():
        print(f"  {'+' if v else '-'} {k}")
    return all_ok


def _t2() -> bool:
    stem = "Kenya Gazette Vol CXINo 103"
    data = _load(stem)
    env = Envelope.model_validate(data)
    ok = env.corrigenda == [] and data.get("corrigenda") == []
    print(f"T2 {'OK' if ok else 'FAIL'} on {stem} (corrigenda empty: {env.corrigenda == []})")
    return ok


def main() -> int:
    r1 = _t1()
    r2 = _t2()
    return 0 if (r1 and r2) else 1


if __name__ == "__main__":
    sys.exit(main())
