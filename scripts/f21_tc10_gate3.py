r"""F21 TC10: Gate 3 end-to-end import + call on the pre-2010 OCR-heavy PDF.

``Vol CIINo 83 - pre 2010`` is deliberately chosen because it is the most
fragile canonical fixture (mean_composite 0.253, OCR-quality boundary
cap fires). If Gate 3 clears on this one, it clears on all six.

G1 subprocess isolation + retry
-------------------------------
Running ``parse_file`` in-process on this particular PDF occasionally
triggers the documented G1 Docling / RapidOCR ``std::bad_alloc`` /
access-violation crash (observed in this session: TC5/TC6 and a
direct TC10 invocation both killed their Python process with
Windows exit code 0xC0000005). The crash is non-deterministic -
TC8's subprocess-per-PDF run successfully parsed this same PDF moments
before, producing the canonical mean_composite=0.253 envelope on
disk. To prove Gate 3 ("the public import + call chain works end-to-end
on this fixture") without being at the mercy of OCR flake, TC10:

1. Spawns a child Python process that imports the public API and calls
   ``parse_file`` on the fixture. The child writes the resulting
   ``Envelope`` as JSON into a tempfile and exits.
2. Retries once on non-zero exit, mirroring TC8's retry policy.
3. The parent reads the JSON back via ``Envelope.model_validate_json``
   to verify the round-trip (and therefore the ``isinstance(env,
   Envelope)`` check) succeeds.

The top-level ``from kenya_gazette_parser import ...`` in this
parent script still exercises the Gate 3 import path; the child just
isolates the Docling work so OCR flake cannot corrupt the parent.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

from kenya_gazette_parser import (  # noqa: E402
    Envelope,
    __version__,
    parse_bytes,
    parse_file,
    write_envelope,
)

PDF = REPO / "pdfs" / "Kenya Gazette Vol CIINo 83 - pre 2010.pdf"

_CHILD_SCRIPT = """
import sys
from pathlib import Path
from kenya_gazette_parser import Envelope, parse_file
env = parse_file(Path(sys.argv[1]))
assert isinstance(env, Envelope), f"child got {type(env).__name__}"
Path(sys.argv[2]).write_text(env.model_dump_json(), encoding="utf-8")
"""


def _parse_in_child(pdf: Path, attempts: int = 2) -> Envelope:
    with tempfile.TemporaryDirectory(prefix="f21_tc10_") as td:
        tdp = Path(td)
        script = tdp / "child.py"
        script.write_text(_CHILD_SCRIPT, encoding="utf-8")
        out_json = tdp / "env.json"
        last_rc: int | None = None
        for attempt in range(1, attempts + 1):
            suffix = f" (attempt {attempt}/{attempts})" if attempts > 1 else ""
            print(f">>> TC10 child parse_file on {pdf.name}{suffix}", flush=True)
            rc = subprocess.call(
                [sys.executable, str(script), str(pdf), str(out_json)],
                cwd=str(REPO),
            )
            last_rc = rc
            if rc == 0 and out_json.exists():
                print(f"<<< TC10 child rc=0", flush=True)
                return Envelope.model_validate_json(
                    out_json.read_text(encoding="utf-8")
                )
            print(f"<<< TC10 child rc={rc} (G1 OCR crash; will retry)", flush=True)
        raise SystemExit(
            f"TC10 FAIL: parse_file child crashed {attempts}x "
            f"(last rc={last_rc}); G1 OCR non-determinism"
        )


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    assert __version__ == "0.1.0", f"library_version drift: {__version__!r}"
    assert callable(parse_file)
    assert callable(parse_bytes)
    assert callable(write_envelope)

    env = _parse_in_child(PDF)

    assert isinstance(env, Envelope), (
        f"reconstructed Envelope has wrong type: {type(env).__name__}"
    )
    assert len(env.notices) == 1, (
        f"Expected 1 notice for CIINo 83 pre-2010, got {len(env.notices)}"
    )

    print("TC10 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
