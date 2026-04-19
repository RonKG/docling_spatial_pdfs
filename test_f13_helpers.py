"""Direct test of F13 helper functions."""
import hashlib
from pathlib import Path
from typing import Any

# Copy helper functions from notebook cell 12
def compute_pdf_sha256(pdf_path: Path) -> str:
    """Compute SHA-256 hex digest of PDF file bytes.
    
    Returns lowercase hex string (length 64). On read failure, returns
    fallback string for stability.
    """
    try:
        pdf_bytes = pdf_path.read_bytes()
        return hashlib.sha256(pdf_bytes).hexdigest()
    except Exception:
        return f"unknown_{pdf_path.name}"


def make_gazette_issue_id(masthead: dict, pdf_sha256: str) -> tuple[str, bool]:
    """Build canonical gazette issue ID from masthead fields.
    
    Returns (issue_id, is_fallback). Canonical form:
        KE-GAZ-{volume}-{issue_no}-{publication_date}[-S{n}]
    Fallback (when required fields missing):
        KE-GAZ-UNKNOWN-{pdf_sha256[:12]}
    
    Required fields: volume, issue_no, publication_date
    Optional field: supplement_no (appended as -S{n} when present and non-zero)
    """
    volume = masthead.get("volume")
    issue_no = masthead.get("issue_no")
    pub_date = masthead.get("publication_date")
    supplement_no = masthead.get("supplement_no")
    
    # Check if required fields are present
    if volume is None or issue_no is None or pub_date is None:
        fallback_id = f"KE-GAZ-UNKNOWN-{pdf_sha256[:12]}"
        return (fallback_id, True)
    
    # Build canonical ID
    issue_id = f"KE-GAZ-{volume}-{issue_no}-{pub_date}"
    
    # Append supplement suffix if present and non-zero
    if supplement_no is not None and supplement_no != 0:
        issue_id = f"{issue_id}-S{supplement_no}"
    
    return (issue_id, False)


def make_notice_id(gazette_issue_id: str, gazette_notice_no: Any, line_span_start: int) -> str:
    """Build notice ID from gazette issue ID and notice number.
    
    For keyed notices (gazette_notice_no is not None):
        {gazette_issue_id}:{gazette_notice_no}
    For orphan blocks (gazette_notice_no is None):
        {gazette_issue_id}:_orphan_{line_span_start}
    
    line_span_start defaults to 0 if None.
    """
    if line_span_start is None:
        line_span_start = 0
    
    if gazette_notice_no is None:
        return f"{gazette_issue_id}:_orphan_{line_span_start}"
    else:
        return f"{gazette_issue_id}:{gazette_notice_no}"


def test_helper_functions():
    """Test the helper functions directly."""
    print("Testing F13 Helper Functions")
    print("=" * 70)
    
    # Test 1: compute_pdf_sha256
    print("\n1. Testing compute_pdf_sha256...")
    pdf_path = Path("pdfs/Kenya Gazette Vol CXXIVNo 282.pdf")
    if pdf_path.exists():
        sha256 = compute_pdf_sha256(pdf_path)
        expected = "fd6adb427496096cd9e00ad652e7915556a021518c4713a7d929c918f9daf12e"
        if sha256 == expected:
            print(f"   PASS: SHA-256 matches expected value")
        else:
            print(f"   FAIL: SHA-256 mismatch")
            print(f"     Expected: {expected}")
            print(f"     Got:      {sha256}")
    else:
        print(f"   SKIP: PDF not found at {pdf_path}")
    
    # Test 2: make_gazette_issue_id - happy path
    print("\n2. Testing make_gazette_issue_id (happy path)...")
    masthead = {
        "volume": "CXXIV",
        "issue_no": "282",
        "publication_date": "2022-12-23",
        "supplement_no": None
    }
    issue_id, is_fallback = make_gazette_issue_id(masthead, "dummy_sha256")
    expected_id = "KE-GAZ-CXXIV-282-2022-12-23"
    if issue_id == expected_id and not is_fallback:
        print(f"   PASS: {issue_id}")
    else:
        print(f"   FAIL: Expected {expected_id}, got {issue_id} (fallback={is_fallback})")
    
    # Test 3: make_gazette_issue_id - with supplement
    print("\n3. Testing make_gazette_issue_id (with supplement)...")
    masthead = {
        "volume": "CXI",
        "issue_no": "100",
        "publication_date": "2009-11-20",
        "supplement_no": 76
    }
    issue_id, is_fallback = make_gazette_issue_id(masthead, "dummy_sha256")
    expected_id = "KE-GAZ-CXI-100-2009-11-20-S76"
    if issue_id == expected_id and not is_fallback:
        print(f"   PASS: {issue_id}")
    else:
        print(f"   FAIL: Expected {expected_id}, got {issue_id} (fallback={is_fallback})")
    
    # Test 4: make_gazette_issue_id - fallback
    print("\n4. Testing make_gazette_issue_id (fallback)...")
    masthead = {
        "volume": None,
        "issue_no": None,
        "publication_date": None,
        "supplement_no": None
    }
    test_sha = "abc123def456789"
    issue_id, is_fallback = make_gazette_issue_id(masthead, test_sha)
    expected_id = "KE-GAZ-UNKNOWN-abc123def456"
    if issue_id == expected_id and is_fallback:
        print(f"   PASS: {issue_id} (fallback=True)")
    else:
        print(f"   FAIL: Expected {expected_id}, got {issue_id} (fallback={is_fallback})")
    
    # Test 5: make_notice_id - keyed notice
    print("\n5. Testing make_notice_id (keyed notice)...")
    notice_id = make_notice_id("KE-GAZ-CXXIV-282-2022-12-23", 15793, 100)
    expected = "KE-GAZ-CXXIV-282-2022-12-23:15793"
    if notice_id == expected:
        print(f"   PASS: {notice_id}")
    else:
        print(f"   FAIL: Expected {expected}, got {notice_id}")
    
    # Test 6: make_notice_id - orphan block
    print("\n6. Testing make_notice_id (orphan block)...")
    notice_id = make_notice_id("KE-GAZ-CXXIV-282-2022-12-23", None, 1234)
    expected = "KE-GAZ-CXXIV-282-2022-12-23:_orphan_1234"
    if notice_id == expected:
        print(f"   PASS: {notice_id}")
    else:
        print(f"   FAIL: Expected {expected}, got {notice_id}")
    
    # Test 7: make_notice_id - orphan with None line_span
    print("\n7. Testing make_notice_id (orphan with None line_span)...")
    notice_id = make_notice_id("KE-GAZ-TEST", None, None)
    expected = "KE-GAZ-TEST:_orphan_0"
    if notice_id == expected:
        print(f"   PASS: {notice_id}")
    else:
        print(f"   FAIL: Expected {expected}, got {notice_id}")
    
    print("\n" + "=" * 70)
    print("Helper function tests complete!")


if __name__ == "__main__":
    test_helper_functions()
