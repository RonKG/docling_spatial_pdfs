r"""F19 T7: assert one ``corrigendum_scope_defaulted`` warning per corrigendum.

Loads the freshly-written nested-shape ``_gazette_spatial.json`` for a PDF
known to contain corrigenda (default: Vol CXXIVNo 282), validates through
``Envelope.model_validate``, and asserts:

- ``len([w for w in env.warnings if w.kind == "corrigendum_scope_defaulted"])``
  equals ``len(env.corrigenda)``
- each warning's ``where["notice_no"]`` matches the corresponding
  corrigendum's ``target_notice_no`` (both can be ``None``).

If the chosen PDF has zero corrigenda, T7 trivially passes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kenya_gazette_parser.models import Envelope

REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"

DEFAULT_STEM = "Kenya Gazette Vol CXXIVNo 282"


def main(argv: list[str]) -> int:
    stem = argv[0] if argv else DEFAULT_STEM
    path = OUTPUT_DIR / stem / f"{stem}_gazette_spatial.json"
    if not path.exists():
        print(f"FAIL: missing output file {path}")
        return 1

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    env = Envelope.model_validate(data)

    scope_warnings = [w for w in env.warnings if w.kind == "corrigendum_scope_defaulted"]
    n_warn = len(scope_warnings)
    n_cor = len(env.corrigenda)

    if n_warn != n_cor:
        print(
            f"FAIL: {stem}: {n_warn} corrigendum_scope_defaulted warnings "
            f"vs {n_cor} corrigenda"
        )
        return 1

    for idx, (w, c) in enumerate(zip(scope_warnings, env.corrigenda)):
        where = w.where or {}
        w_notice_no = where.get("notice_no")
        if w_notice_no != c.target_notice_no:
            print(
                f"FAIL: {stem}: warning[{idx}].where.notice_no="
                f"{w_notice_no!r} vs corrigendum[{idx}].target_notice_no="
                f"{c.target_notice_no!r}"
            )
            return 1

    print(f"T7 OK ({n_warn} warnings for {n_cor} corrigenda) on {stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
