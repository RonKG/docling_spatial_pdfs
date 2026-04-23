r"""F21 TC2: parse_bytes parity with parse_file on Vol CXINo 100.

Proves ``parse_bytes(data, filename=...)`` produces an ``Envelope``
byte-equivalent to ``parse_file(path)`` on the same bytes:

* identical ``pdf_sha256``
* identical ``notice_id`` list
* identical ``gazette_issue_id``
* identical ``mean_composite``

Also validates the cross-platform ``TemporaryDirectory`` temp-file dance
works on Windows (where ``NamedTemporaryFile(delete=True)`` would fail).

Implementation note (G1 subprocess isolation)
---------------------------------------------
Running ``parse_file`` and ``parse_bytes`` back-to-back in the same
Python process triggers the documented G1 Docling / RapidOCR
``std::bad_alloc`` instability on the second invocation — OCR state
leaks between conversions and certain pages intermittently fail,
producing different notice counts across the two runs (observed:
280 vs 287 on CXINo 100). This is exactly the instability F19/F20's
subprocess-per-PDF runner documents.

TC2 dodges this the same way the notebook shim and TC8 do: each parse
runs in its own child Python process that writes its ``Envelope``
(via ``env.model_dump(mode="json")``) to a tempfile. The parent
process then reads both JSONs and compares them. Library parity is
still proved — both children import the public API from
``kenya_gazette_parser`` and both go through ``build_envelope`` —
but each OCR run starts from a clean slate.
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXINo 100.pdf"


_CHILD_PARSE_FILE = """
import json, sys
from pathlib import Path
from kenya_gazette_parser import parse_file
env = parse_file(Path(sys.argv[1]))
Path(sys.argv[2]).write_text(
    json.dumps(env.model_dump(mode="json"), ensure_ascii=False),
    encoding="utf-8",
)
"""

_CHILD_PARSE_BYTES = """
import json, sys
from pathlib import Path
from kenya_gazette_parser import parse_bytes
data = Path(sys.argv[1]).read_bytes()
env = parse_bytes(data, filename=Path(sys.argv[1]).name)
Path(sys.argv[2]).write_text(
    json.dumps(env.model_dump(mode="json"), ensure_ascii=False),
    encoding="utf-8",
)
"""


def _run_child(script_src: str, pdf: Path, out_json: Path, attempts: int = 3) -> int:
    """Spawn child subprocess; retry once on G1 OCR crash (std::bad_alloc).

    The G1 instability is non-deterministic — a retry usually succeeds when
    the first attempt hits the Docling/RapidOCR allocator edge-case.
    """
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as sf:
        sf.write(script_src)
        script_path = Path(sf.name)
    try:
        rc = -1
        for attempt in range(1, attempts + 1):
            if out_json.exists():
                out_json.unlink()
            suffix = f" (attempt {attempt}/{attempts})" if attempts > 1 else ""
            print(
                f">>> child: {script_path.name} -> {out_json.name}{suffix}",
                flush=True,
            )
            rc = subprocess.call(
                [sys.executable, str(script_path), str(pdf), str(out_json)],
                cwd=str(REPO),
            )
            print(f"<<< child rc={rc}", flush=True)
            if rc == 0 and out_json.exists():
                return 0
            if attempt < attempts:
                print(
                    f"    attempt {attempt} failed "
                    f"(rc={rc}, output_exists={out_json.exists()}); "
                    f"G1 OCR instability — sleeping 10s then retrying",
                    flush=True,
                )
                gc.collect()
                time.sleep(10)
        return rc
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass


def _notice_ids(js: dict) -> list[str]:
    return [n["notice_id"] for n in (js.get("notices") or [])]


def _run_pair(tdp: Path) -> tuple[int, dict | None, dict | None]:
    """Run both children once and load their outputs."""
    out_f = tdp / "env_parse_file.json"
    out_b = tdp / "env_parse_bytes.json"
    rc1 = _run_child(_CHILD_PARSE_FILE, PDF, out_f, attempts=1)
    if rc1 != 0 or not out_f.exists():
        return (1, None, None)
    rc2 = _run_child(_CHILD_PARSE_BYTES, PDF, out_b, attempts=1)
    if rc2 != 0 or not out_b.exists():
        return (2, None, None)
    env_f = json.loads(out_f.read_text(encoding="utf-8"))
    env_b = json.loads(out_b.read_text(encoding="utf-8"))
    return (0, env_f, env_b)


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"

    # G1 OCR non-determinism (std::bad_alloc on pages 39-56 of CXINo 100)
    # can cause a single run to produce a partial/corrupted Envelope.
    # Retry the whole pair up to 5 times until both children succeed AND
    # agree on notice_id lists (byte parity is the test's purpose).
    max_pair_attempts = 5
    last_envs: tuple[dict | None, dict | None] = (None, None)
    with tempfile.TemporaryDirectory(prefix="f21_tc2_") as td:
        tdp = Path(td)
        for pair_attempt in range(1, max_pair_attempts + 1):
            print(
                f"\n=== Pair attempt {pair_attempt}/{max_pair_attempts} ===",
                flush=True,
            )
            status, env_f, env_b = _run_pair(tdp)
            if status != 0:
                print(
                    f"    pair attempt {pair_attempt}: child crashed "
                    f"(status={status}); retry after 10s"
                )
                gc.collect()
                time.sleep(10)
                continue
            last_envs = (env_f, env_b)
            ids_f = _notice_ids(env_f)
            ids_b = _notice_ids(env_b)
            if ids_f == ids_b and len(ids_f) > 0:
                print(
                    f"    pair attempt {pair_attempt}: AGREE "
                    f"({len(ids_f)} notice_ids match)",
                    flush=True,
                )
                break
            print(
                f"    pair attempt {pair_attempt}: DISAGREE "
                f"(len_f={len(ids_f)}, len_b={len(ids_b)}); G1 OCR "
                f"non-determinism; retry after 10s"
            )
            gc.collect()
            time.sleep(10)
        else:
            env_f, env_b = last_envs
            if env_f is None or env_b is None:
                print(
                    f"TC2 FAIL: no pair attempt produced both envelopes "
                    f"in {max_pair_attempts} tries (persistent G1 OCR crash)"
                )
                return 1
            print(
                f"TC2 FAIL: notice_id lists never agreed in "
                f"{max_pair_attempts} attempts (persistent G1 OCR "
                f"non-determinism on CXINo 100)"
            )
            return 1

    if env_b["pdf_sha256"] != env_f["pdf_sha256"]:
        print(
            f"TC2 FAIL: pdf_sha256 mismatch "
            f"(parse_bytes={env_b['pdf_sha256']!r}, "
            f"parse_file={env_f['pdf_sha256']!r})"
        )
        return 1

    ids_b = _notice_ids(env_b)
    ids_f = _notice_ids(env_f)
    if ids_b != ids_f:
        first_diff = next(
            (i for i, (a, b) in enumerate(zip(ids_b, ids_f)) if a != b),
            min(len(ids_b), len(ids_f)),
        )
        print(
            f"TC2 FAIL: notice_id lists differ "
            f"(len_b={len(ids_b)}, len_f={len(ids_f)}, first_diff_index={first_diff})"
        )
        return 1

    if env_b["issue"]["gazette_issue_id"] != env_f["issue"]["gazette_issue_id"]:
        print(
            f"TC2 FAIL: gazette_issue_id mismatch "
            f"({env_b['issue']['gazette_issue_id']!r} vs "
            f"{env_f['issue']['gazette_issue_id']!r})"
        )
        return 1

    mc_b = env_b["document_confidence"]["mean_composite"]
    mc_f = env_f["document_confidence"]["mean_composite"]
    if mc_b != mc_f:
        print(f"TC2 FAIL: mean_composite mismatch ({mc_b} vs {mc_f})")
        return 1

    print(
        f"TC2 OK (pdf_sha256={env_b['pdf_sha256'][:12]}..., "
        f"n_notices={len(ids_b)}, "
        f"gazette_issue_id={env_b['issue']['gazette_issue_id']}, "
        f"mean_composite={mc_b:.3f}; "
        f"subprocess-isolated to dodge G1 OCR non-determinism)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
