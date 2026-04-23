r"""F21 TC4: write_envelope selective bundles - only gazette_spatial_json.

Proves the ``bundles`` dict API filters correctly and the env-only shortcut
works without ``pdf_path``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import parse_file, write_envelope  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXIINo 76.pdf"
STEM = PDF.stem


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"

    env = parse_file(PDF)
    with tempfile.TemporaryDirectory(prefix="f21_tc4_") as td:
        out_dir = Path(td)
        written = write_envelope(
            env,
            out_dir=out_dir,
            bundles={
                "gazette_spatial_json": True,
                "full_text": False,
                "docling_markdown": False,
                "spatial_markdown": False,
                "docling_json": False,
            },
            pdf_path=PDF,
        )

        assert list(written.keys()) == ["gazette_spatial_json"], (
            f"written keys {list(written.keys())!r} != ['gazette_spatial_json']"
        )
        files = sorted(p.name for p in out_dir.iterdir() if p.is_file())
        expected = [f"{STEM}_gazette_spatial.json"]
        assert files == expected, (
            f"on-disk files {files!r} != expected {expected!r}"
        )

        written2 = write_envelope(
            env,
            out_dir=out_dir,
            bundles={"gazette_spatial_json": True},
            pdf_path=None,
        )
        assert list(written2.keys()) == ["gazette_spatial_json"], (
            f"env-only (pdf_path=None) keys {list(written2.keys())!r}"
        )

    print(
        f"TC4 OK (selective default={files[0]}; env-only pdf_path=None also works)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
