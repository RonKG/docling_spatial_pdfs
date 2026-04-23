r"""F21 TC7: parse_file(config=<non-None>) and parse_bytes(config=<non-None>)
raise NotImplementedError mentioning F22 and GazetteConfig.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import parse_bytes, parse_file  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CIINo 83 - pre 2010.pdf"


def _check_message(msg: str, where: str) -> None:
    assert "F22" in msg, f"{where}: message must contain 'F22', got: {msg!r}"
    assert "GazetteConfig" in msg, (
        f"{where}: message must contain 'GazetteConfig', got: {msg!r}"
    )


def main() -> int:
    try:
        parse_file(PDF, config={"llm": "optional"})
    except NotImplementedError as exc:
        _check_message(str(exc), "parse_file")
    else:
        print("TC7 FAIL: parse_file(config=...) did not raise NotImplementedError")
        return 1

    try:
        parse_bytes(b"", filename="anything.pdf", config={"llm": "optional"})
    except NotImplementedError as exc:
        _check_message(str(exc), "parse_bytes")
    else:
        print("TC7 FAIL: parse_bytes(config=...) did not raise NotImplementedError")
        return 1

    print("TC7 OK (parse_file + parse_bytes both raise NotImplementedError)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
