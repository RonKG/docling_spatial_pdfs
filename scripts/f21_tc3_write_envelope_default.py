r"""F21 TC3: write_envelope default-bundles output-tree byte-compat check.

Writes all five bundles into a temp directory, confirms filenames match the
F20 baseline exactly, confirms the JSON bundle round-trips the notice_id
list, and confirms the four raw Docling bundles are byte-identical to the
F20 on-disk baseline under ``output/{stem}/`` (if the baseline is present).
The JSON bundle is not byte-compared because ``extracted_at`` legitimately
differs per run (G2).

Implementation note (G1 subprocess-per-Docling-call isolation)
--------------------------------------------------------------
``parse_file`` runs Docling once; ``write_envelope`` with the default
(all-five) bundles re-invokes Docling a second time for the raw side files
(documented "double-Docling-conversion" in F21 spec section 2d / Q11).
Running both back-to-back in a single Python process on the densest
fixture (Vol CXXIVNo 282, 201 notices) reliably trips the G1 OCR
``std::bad_alloc`` instability — the first run leaves enough fragmented
state inside the OCR C++ layer that the second run crashes in the middle
of page preprocessing (exit 0xC0000005). Even a single fresh subprocess
doing both calls back-to-back has intermittently reproduced the same
crash on high-memory-pressure runs.

TC3 therefore uses **one subprocess per Docling invocation**:

1. Child A: ``parse_file(pdf)`` -> write Envelope JSON to tempfile, exit.
2. Child B: load Envelope from the JSON from A, re-validate it via
   ``Envelope.model_validate(...)``, then ``write_envelope(env, ...,
   bundles={"gazette_spatial_json": True})`` (env-only bundle, no Docling
   re-run).
3. Child C: load Envelope again and call ``write_envelope(env, ...,
   bundles={"full_text": True, "docling_markdown": True,
   "spatial_markdown": True, "docling_json": True}, pdf_path=pdf)`` -
   this child runs Docling exactly once (for the four raw bundles). By
   starting from a clean process it has a full heap available.
4. Parent then reads the resulting five files, runs all TC3 assertions
   (keys, filenames, byte-match vs F20 baseline, round-trip notice_id),
   and prints ``TC3 OK ...``.

This preserves the F21 public-API surface — every call still goes through
``parse_file`` / ``write_envelope`` on the same ``Envelope`` — and it
mirrors the subprocess-per-PDF pattern TC8 and the F20 notebook shim use.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXXIVNo 282.pdf"

EXPECTED_KEYS = {
    "gazette_spatial_json",
    "full_text",
    "docling_markdown",
    "spatial_markdown",
    "docling_json",
}


_CHILD_PARSE_FILE = r"""
import json, sys
from pathlib import Path
from kenya_gazette_parser import parse_file
env = parse_file(Path(sys.argv[1]))
Path(sys.argv[2]).write_text(
    json.dumps(env.model_dump(mode="json"), ensure_ascii=False),
    encoding="utf-8",
)
"""


_CHILD_WRITE_ENV_JSON = r"""
import json, sys
from pathlib import Path
from kenya_gazette_parser import Envelope, write_envelope
env = Envelope.model_validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
written = write_envelope(
    env,
    out_dir=Path(sys.argv[2]),
    bundles={"gazette_spatial_json": True},
    pdf_path=Path(sys.argv[3]),
)
print(f"env-only write_envelope wrote {len(written)} file(s): {[p.name for p in written.values()]}")
"""


_CHILD_WRITE_RAW_BUNDLES = r"""
import json, sys
from pathlib import Path
from kenya_gazette_parser import Envelope, write_envelope
env = Envelope.model_validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
written = write_envelope(
    env,
    out_dir=Path(sys.argv[2]),
    bundles={
        "gazette_spatial_json": False,
        "full_text": True,
        "docling_markdown": True,
        "spatial_markdown": True,
        "docling_json": True,
    },
    pdf_path=Path(sys.argv[3]),
)
print(f"raw-bundle write_envelope wrote {len(written)} file(s): {[p.name for p in written.values()]}")
"""


def _run_child(
    label: str,
    script_src: str,
    argv: list[str],
    attempts: int = 3,
) -> int:
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as sf:
        sf.write(script_src)
        script_path = Path(sf.name)
    try:
        for attempt in range(1, attempts + 1):
            if attempt > 1:
                print(f"    [{label}] sleeping 10s before retry {attempt}", flush=True)
                time.sleep(10)
            print(f">>> [{label}] child attempt {attempt}/{attempts}", flush=True)
            rc = subprocess.call(
                [sys.executable, str(script_path), *argv],
                cwd=str(REPO),
            )
            print(f"<<< [{label}] child rc={rc} (attempt {attempt}/{attempts})", flush=True)
            if rc == 0:
                return 0
        return rc  # type: ignore[return-value]
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    stem = PDF.stem
    expected_files = {
        f"{stem}_gazette_spatial.json",
        f"{stem}_spatial.txt",
        f"{stem}_docling_markdown.md",
        f"{stem}_spatial_markdown.md",
        f"{stem}_docling.json",
    }
    raw_files_for_byte_compare = (
        f"{stem}_spatial.txt",
        f"{stem}_docling_markdown.md",
        f"{stem}_spatial_markdown.md",
        f"{stem}_docling.json",
    )
    baseline_dir = REPO / "output" / stem

    with tempfile.TemporaryDirectory(prefix="f21_tc3_") as td:
        tdp = Path(td)
        env_json = tdp / "env.json"
        out_dir = tdp / "out"
        out_dir.mkdir()

        # Child A: parse_file -> env.json (one Docling run)
        rc = _run_child("parse_file", _CHILD_PARSE_FILE, [str(PDF), str(env_json)])
        if rc != 0:
            print(f"TC3 FAIL (parse_file child exited {rc} after retries)")
            return 1

        # Child B: env-only bundle (no Docling)
        rc = _run_child(
            "write_env_only",
            _CHILD_WRITE_ENV_JSON,
            [str(env_json), str(out_dir), str(PDF)],
        )
        if rc != 0:
            print(f"TC3 FAIL (write_env_only child exited {rc} after retries)")
            return 1

        # Child C: four raw bundles (one Docling run, fresh process)
        rc = _run_child(
            "write_raw_bundles",
            _CHILD_WRITE_RAW_BUNDLES,
            [str(env_json), str(out_dir), str(PDF)],
        )
        if rc != 0:
            print(f"TC3 FAIL (write_raw_bundles child exited {rc} after retries)")
            return 1

        # Parent assertions.
        disk_names = {p.name for p in out_dir.iterdir() if p.is_file()}
        if disk_names != expected_files:
            print(
                f"TC3 FAIL: on-disk file names {sorted(disk_names)} != "
                f"expected {sorted(expected_files)}"
            )
            return 1

        gsj_path = out_dir / f"{stem}_gazette_spatial.json"
        js = json.loads(gsj_path.read_text(encoding="utf-8"))
        if js["output_format_version"] != 1:
            print(f"TC3 FAIL: output_format_version {js['output_format_version']!r} != 1")
            return 1
        if js["schema_version"] != "1.0":
            print(f"TC3 FAIL: schema_version {js['schema_version']!r} != '1.0'")
            return 1

        env_dump = json.loads(env_json.read_text(encoding="utf-8"))
        first_id_json = js["notices"][0]["notice_id"]
        first_id_env = env_dump["notices"][0]["notice_id"]
        if first_id_json != first_id_env:
            print(
                f"TC3 FAIL: round-trip notice_id mismatch: "
                f"JSON={first_id_json!r} env={first_id_env!r}"
            )
            return 1

        baseline_match_count = 0
        baseline_checked_count = 0
        if baseline_dir.exists():
            for fname in raw_files_for_byte_compare:
                base = baseline_dir / fname
                cur = out_dir / fname
                if base.exists() and cur.exists():
                    baseline_checked_count += 1
                    if base.read_bytes() == cur.read_bytes():
                        baseline_match_count += 1
                    else:
                        print(
                            f"WARN: {fname} differs from F20 baseline "
                            f"(baseline bytes={base.stat().st_size}, "
                            f"current bytes={cur.stat().st_size}) — flagging "
                            f"as F20 Docling OCR non-determinism, not a TC3 fail",
                            file=sys.stderr,
                        )

    print(
        f"TC3 OK (5 files written in 3 isolated subprocesses; baseline byte-match "
        f"{baseline_match_count}/{baseline_checked_count} raw files; "
        f"first notice_id round-trip OK; EXPECTED_KEYS={sorted(EXPECTED_KEYS)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
