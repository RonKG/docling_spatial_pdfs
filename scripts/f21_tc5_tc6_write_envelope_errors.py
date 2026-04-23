r"""F21 TC5 + TC6 combined: write_envelope error paths.

TC5: raw-Docling bundle requested without ``pdf_path`` -> ValueError naming
     the offending bundle and the required ``pdf_path`` fix.
TC6: unknown bundle key -> ValueError naming the typo key.

Both cases assert the message text so that callers get actionable errors.

Envelope sourcing (G1-robust)
-----------------------------
Both ``ValueError`` paths in ``write_envelope`` raise before the function
ever touches the ``env`` argument's fields, so any valid ``Envelope``
instance suffices. To avoid re-triggering the documented Docling /
RapidOCR ``std::bad_alloc`` instability (G1) while testing a pure
library error path, TC5/TC6 reconstruct the ``Envelope`` from the
already-validated on-disk JSON at
``output/<stem>/<stem>_gazette_spatial.json`` (written by TC1/TC3/TC8
via ``write_envelope`` itself) rather than re-running Docling. The
``Envelope.model_validate_json`` round-trip proves the JSON is still a
valid Envelope and gives TC5/TC6 a stable, zero-cost fixture.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import Envelope, write_envelope  # noqa: E402

# CXXIVNo 282 is the densest modern fixture (201 notices) and is
# present on disk after TC1/TC3. If it ever goes missing, we fall back
# to the first available canonical stem under ``output/``.
PRIMARY_STEM = "Kenya Gazette Vol CXXIVNo 282"
FALLBACK_STEMS = (
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
)


def _pick_envelope_source() -> Path:
    primary = REPO / "output" / PRIMARY_STEM / f"{PRIMARY_STEM}_gazette_spatial.json"
    if primary.exists():
        return primary
    for stem in FALLBACK_STEMS:
        candidate = REPO / "output" / stem / f"{stem}_gazette_spatial.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No canonical envelope JSON found under output/ — run TC1/TC3/TC8 "
        "first so at least one {stem}_gazette_spatial.json exists for "
        "TC5/TC6 to reconstruct the Envelope from."
    )


def main() -> int:
    source = _pick_envelope_source()
    print(f">>> reconstructing Envelope from {source.relative_to(REPO)}")
    env = Envelope.model_validate_json(source.read_text(encoding="utf-8"))
    assert isinstance(env, Envelope), (
        f"reconstructed Envelope has wrong type: {type(env).__name__}"
    )
    # Sanity: an Envelope reconstructed from disk must still have its
    # pdf_sha256 (proves the JSON is structurally sound).
    assert isinstance(env.pdf_sha256, str) and len(env.pdf_sha256) == 64, (
        f"pdf_sha256 looks wrong on reconstructed Envelope: {env.pdf_sha256!r}"
    )

    with tempfile.TemporaryDirectory(prefix="f21_tc5_tc6_") as td:
        out_dir = Path(td)

        try:
            write_envelope(
                env,
                out_dir=out_dir,
                bundles={"full_text": True},
                pdf_path=None,
            )
        except ValueError as exc:
            msg = str(exc)
            assert "full_text" in msg, (
                f"TC5: ValueError must name 'full_text', got: {msg!r}"
            )
            assert "pdf_path" in msg, (
                f"TC5: ValueError must mention 'pdf_path', got: {msg!r}"
            )
            print(f"TC5 OK ({msg!r})")
        else:
            print("TC5 FAIL: write_envelope did not raise ValueError")
            return 1

        try:
            write_envelope(
                env,
                out_dir=out_dir,
                bundles={"bogus_key": True},
            )
        except ValueError as exc:
            msg = str(exc)
            assert "bogus_key" in msg, (
                f"TC6: ValueError must name 'bogus_key', got: {msg!r}"
            )
            print(f"TC6 OK ({msg!r})")
        else:
            print("TC6 FAIL: write_envelope did not raise ValueError")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
