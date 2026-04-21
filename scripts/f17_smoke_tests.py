r"""F17 smoke tests T2-T4 consolidated.

Run from repo root: `.\.venv\Scripts\python.exe scripts\f17_smoke_tests.py`
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

FAILS: list[str] = []


def t2_parse_file_stub() -> None:
    from kenya_gazette_parser import parse_file

    try:
        parse_file("anything.pdf")
    except NotImplementedError as e:
        msg = str(e)
        required = ["F17", "F20-F21", "gazette_docling_pipeline_spatial.ipynb"]
        missing = [tok for tok in required if tok not in msg]
        if missing:
            FAILS.append(f"T2 FAIL: missing tokens {missing} in message: {msg!r}")
        else:
            print("T2 OK (parse_file stub raises NotImplementedError with all tokens)")
    else:
        FAILS.append("T2 FAIL: parse_file did not raise")


def t3_parse_bytes_stub() -> None:
    from kenya_gazette_parser import parse_bytes

    try:
        parse_bytes(b"%PDF-1.4 fake", filename="x.pdf")
    except NotImplementedError as e:
        msg = str(e)
        if "F17" not in msg or "parse_bytes" not in msg:
            FAILS.append(f"T3 FAIL: missing 'F17' or 'parse_bytes' in message: {msg!r}")
        else:
            print("T3 OK (parse_bytes stub raises with 'parse_bytes' token)")
    else:
        FAILS.append("T3 FAIL: parse_bytes did not raise")

    # Also verify keyword-only shape for filename
    try:
        parse_bytes(b"x", "positional_filename_should_fail")  # noqa: F841
    except TypeError:
        print("T3 OK (filename is keyword-only as required)")
    except NotImplementedError:
        FAILS.append(
            "T3 FAIL: parse_bytes accepted positional filename (should be keyword-only)"
        )


def t4_pyproject() -> None:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        FAILS.append("T4a FAIL: pyproject.toml not found")
        return

    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)

    project = data.get("project", {})
    name = project.get("name")
    version = project.get("version")
    lic = project.get("license", {})
    deps = project.get("dependencies", [])

    assertions = [
        ("name", name, "kenya-gazette-parser"),
        ("version", version, "0.1.0"),
        ("license.text", lic.get("text") if isinstance(lic, dict) else None, "Apache-2.0"),
    ]

    for label, actual, expected in assertions:
        if actual != expected:
            FAILS.append(f"T4a FAIL: {label} is {actual!r}, expected {expected!r}")

    deps_str = " ".join(deps)
    for must_have in ("openai", "docling", "docling-core"):
        if must_have not in deps_str:
            FAILS.append(f"T4a FAIL: runtime dep {must_have!r} missing from {deps!r}")

    # Classifier must mention the Apache Software License
    classifiers = project.get("classifiers", [])
    if "License :: OSI Approved :: Apache Software License" not in classifiers:
        FAILS.append(
            "T4a FAIL: missing 'License :: OSI Approved :: Apache Software License' classifier"
        )

    if not FAILS:
        print("T4a OK (pyproject.toml valid, all metadata assertions pass)")


if __name__ == "__main__":
    t2_parse_file_stub()
    t3_parse_bytes_stub()
    t4_pyproject()

    print("")
    if FAILS:
        print("=== FAILURES ===")
        for f in FAILS:
            print(f)
        sys.exit(1)
    else:
        print("All T2-T4 assertions PASS")
        sys.exit(0)
