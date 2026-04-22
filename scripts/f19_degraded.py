r"""F19 T3: process a PDF with content_sha256 intentionally stripped.

The monkey-patch removes ``content_sha256`` from the first notice of the flat
record just before ``build_envelope_dict`` runs, so the adapter produces a
notice dict that is missing a contract-required field. ``Envelope.model_validate``
at the tail of ``process_pdf`` must then raise ``pydantic.ValidationError``
(message referencing ``content_sha256`` and ``missing``), and no
``_gazette_spatial.json`` must be written on the failed run.

We assert correctness by stat-ing the file mtime before and after (a
successful write would update the mtime; a ValidationError before the write
would leave the old file untouched).

Run from repo root:
    ``.\.venv\Scripts\python.exe scripts\f19_degraded.py``
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO / "scripts"))

from f19_run_pipeline import _load_notebook_code, NOTEBOOK  # noqa: E402

from pydantic import ValidationError  # noqa: E402

STEM = "Kenya Gazette Vol CXXIVNo 282"
PDF_PATH = REPO / "pdfs" / f"{STEM}.pdf"
OUT_PATH = REPO / "output" / STEM / f"{STEM}_gazette_spatial.json"


def main() -> int:
    if not PDF_PATH.exists():
        print(f"FAIL: missing PDF {PDF_PATH}")
        return 1
    if not OUT_PATH.exists():
        print(
            f"FAIL: expected existing output {OUT_PATH} to compare mtime; "
            "run the pipeline once before T3."
        )
        return 1

    before_mtime = OUT_PATH.stat().st_mtime_ns

    code = _load_notebook_code(NOTEBOOK)
    mod_name = "_notebook_runtime_degraded"
    module = types.ModuleType(mod_name)
    module.__file__ = str(NOTEBOOK)
    sys.modules[mod_name] = module
    exec(compile(code, str(NOTEBOOK), "exec"), module.__dict__)

    original_builder = module.__dict__["build_envelope_dict"]

    def _patched(record_flat: dict) -> dict:
        notices = record_flat.get("gazette_notices") or []
        if notices and "content_sha256" in notices[0]:
            del notices[0]["content_sha256"]
        return original_builder(record_flat)

    module.__dict__["build_envelope_dict"] = _patched

    Pipeline = module.__dict__["GazettePipeline"]
    pipeline = Pipeline()

    try:
        pipeline.process_pdf(PDF_PATH)
    except ValidationError as exc:
        msg = str(exc)
        after_mtime = OUT_PATH.stat().st_mtime_ns
        if after_mtime != before_mtime:
            print(
                "FAIL: output file mtime changed despite ValidationError "
                f"({before_mtime} -> {after_mtime}); a partial write leaked."
            )
            return 1
        if "content_sha256" not in msg or "missing" not in msg.lower():
            print("FAIL: ValidationError did not mention content_sha256 / missing:")
            print(msg[:800])
            return 1
        print("T3 OK (ValidationError raised; no file written)")
        print(f"  excerpt: {msg.splitlines()[0][:200]}")
        return 0

    print("FAIL: process_pdf did not raise ValidationError")
    return 1


if __name__ == "__main__":
    sys.exit(main())
