#!/usr/bin/env python
"""F22 TC7: Test Bundles with unknown field raises ValidationError.

StrictBase pattern continues — extra="forbid".
"""
import sys

from pydantic import ValidationError

from kenya_gazette_parser.models import Bundles

def main() -> int:
    try:
        Bundles(mystery_key=True)  # type: ignore[call-arg]
        print("TC7 FAIL: Expected ValidationError for unknown field")
        return 1
    except ValidationError as e:
        error_str = str(e)
        if "extra_forbidden" in error_str or "Extra inputs are not permitted" in error_str:
            print("TC7 PASS: Bundles(mystery_key=True) raises ValidationError with extra_forbidden")
            return 0
        else:
            print(f"TC7 FAIL: ValidationError raised but without extra_forbidden: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
