r"""F21 TC1: parse_file happy path on Vol CXXIVNo 282 (modern two-column).

Proves the wired ``parse_file`` reproduces F20 behaviour on the densest
fixture. Same assertions F19/F20 TC1 used, plus the F21-specific
``isinstance(env, Envelope)`` check.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import Envelope, parse_file  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXXIVNo 282.pdf"
BASELINE_MEAN = 0.968
TOLERANCE = 0.05


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    env = parse_file(PDF)

    assert isinstance(env, Envelope), (
        f"parse_file must return Envelope, got {type(env).__name__}"
    )
    assert env.output_format_version == 1, (
        f"output_format_version must be 1, got {env.output_format_version}"
    )
    assert env.schema_version == "1.0", (
        f"schema_version must be '1.0', got {env.schema_version!r}"
    )
    assert env.library_version == "0.1.0", (
        f"library_version must be '0.1.0', got {env.library_version!r}"
    )
    assert env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23", (
        f"gazette_issue_id mismatch: got {env.issue.gazette_issue_id!r}"
    )
    n_notices = len(env.notices)
    assert n_notices == 201, f"Expected 201 notices, got {n_notices}"

    mean = env.document_confidence.mean_composite
    delta = abs(mean - BASELINE_MEAN)
    assert delta <= TOLERANCE, (
        f"mean_composite {mean} drifted from baseline {BASELINE_MEAN} by {delta:.4f} "
        f"(>{TOLERANCE})"
    )

    print(f"TC1 OK (notices={n_notices}, mean_composite={mean:.3f}, "
          f"baseline={BASELINE_MEAN}, delta={delta:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
