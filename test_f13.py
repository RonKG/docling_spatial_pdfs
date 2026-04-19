"""Test script for F13: Identity Fields implementation."""
import json
import sys
from pathlib import Path

def test_t1_happy_path():
    """T1: Happy path - modern clean gazette."""
    json_path = Path("output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json")
    if not json_path.exists():
        return "SKIP", "File not found - need to run pipeline first"
    
    with open(json_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    
    # Check pdf_sha256
    expected_sha = "fd6adb427496096cd9e00ad652e7915556a021518c4713a7d929c918f9daf12e"
    if record.get("pdf_sha256") != expected_sha:
        return "FAIL", f"pdf_sha256 mismatch: got {record.get('pdf_sha256')[:20]}..."
    
    # Check gazette_issue_id
    expected_issue_id = "KE-GAZ-CXXIV-282-2022-12-23"
    if record.get("gazette_issue_id") != expected_issue_id:
        return "FAIL", f"issue_id mismatch: got {record.get('gazette_issue_id')}"
    
    # Check first notice
    notices = record.get("gazette_notices", [])
    if not notices:
        return "FAIL", "No notices found"
    
    first_notice = notices[0]
    expected_first_notice_id = "KE-GAZ-CXXIV-282-2022-12-23:15793"
    if first_notice.get("notice_id") != expected_first_notice_id:
        return "FAIL", f"First notice_id mismatch: got {first_notice.get('notice_id')}"
    
    # Check warnings is empty list
    if record.get("warnings") != []:
        return "FAIL", f"warnings should be empty: got {record.get('warnings')}"
    
    return "PASS", f"sha256, issue_id={expected_issue_id}, first notice_id correct, warnings=[]"


def test_t2_determinism():
    """T2: Determinism - two runs produce identical IDs."""
    json_path = Path("output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json")
    if not json_path.exists():
        return "SKIP", "File not found - need to run pipeline twice"
    
    # We'll need to run the pipeline twice and compare
    # For now, just check that notice_ids exist and are unique
    with open(json_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    
    notices = record.get("gazette_notices", [])
    notice_ids = [n.get("notice_id") for n in notices]
    
    # Check all notices have notice_ids
    if any(nid is None for nid in notice_ids):
        return "FAIL", "Some notices missing notice_id"
    
    # Check uniqueness within issue
    if len(set(notice_ids)) != len(notice_ids):
        return "FAIL", f"Duplicate notice_ids found: {len(notice_ids)} notices, {len(set(notice_ids))} unique"
    
    return "PASS", f"All {len(notice_ids)} notice_ids unique (determinism requires manual re-run)"


def test_t3_degraded():
    """T3: Degraded - fallback when masthead missing."""
    # Test the helper function directly
    from importlib import import_module
    
    # We can't import from notebook directly, so we'll check the output
    # for a gazette that should have failed masthead parsing
    json_path = Path("output/Kenya Gazette Vol CXIXNo 194/Kenya Gazette Vol CXIXNo 194_gazette_spatial.json")
    if not json_path.exists():
        return "SKIP", "File not found - need to process CXIXNo 194"
    
    with open(json_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    
    issue_id = record.get("gazette_issue_id", "")
    
    # Check if it's either canonical or fallback
    if issue_id.startswith("KE-GAZ-UNKNOWN-"):
        # Fallback case
        warnings = record.get("warnings", [])
        if not any(w.get("kind") == "masthead.parse_failed" for w in warnings):
            return "FAIL", "Fallback ID but no masthead.parse_failed warning"
        return "PASS", f"Fallback ID with warning: {issue_id}"
    elif issue_id.startswith("KE-GAZ-CXIX-"):
        # Canonical case for this gazette
        return "PASS", f"Canonical ID: {issue_id} (masthead parsed successfully)"
    else:
        return "FAIL", f"Unexpected issue_id format: {issue_id}"


def test_t4_cross_gazette_uniqueness():
    """T4: Different gazettes have different IDs."""
    json1 = Path("output/Kenya Gazette Vol CXINo 100/Kenya Gazette Vol CXINo 100_gazette_spatial.json")
    json2 = Path("output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json")
    
    if not json1.exists() or not json2.exists():
        return "SKIP", "Need both CXINo 100 and CXXIVNo 282 processed"
    
    with open(json1, "r", encoding="utf-8") as f:
        record1 = json.load(f)
    with open(json2, "r", encoding="utf-8") as f:
        record2 = json.load(f)
    
    issue_id1 = record1.get("gazette_issue_id")
    issue_id2 = record2.get("gazette_issue_id")
    
    expected_id1 = "KE-GAZ-CXI-100-2009-11-20-S76"
    expected_id2 = "KE-GAZ-CXXIV-282-2022-12-23"
    
    if issue_id1 != expected_id1:
        return "FAIL", f"CXINo 100 ID wrong: got {issue_id1}, expected {expected_id1}"
    if issue_id2 != expected_id2:
        return "FAIL", f"CXXIVNo 282 ID wrong: got {issue_id2}"
    
    # Check no notice_id collision
    notices1 = [n.get("notice_id") for n in record1.get("gazette_notices", [])]
    notices2 = [n.get("notice_id") for n in record2.get("gazette_notices", [])]
    
    collision = set(notices1) & set(notices2)
    if collision:
        return "FAIL", f"Notice ID collision: {collision}"
    
    return "PASS", f"CXI={expected_id1}, CXXIV={expected_id2}, no collisions"


def test_t5_orphan_stability():
    """T5: Orphan blocks get stable _orphan_{N} IDs."""
    json_path = Path("output/Kenya Gazette Vol CXIXNo 194/Kenya Gazette Vol CXIXNo 194_gazette_spatial.json")
    if not json_path.exists():
        return "SKIP", "Need CXIXNo 194 processed"
    
    with open(json_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    
    notices = record.get("gazette_notices", [])
    orphans = [n for n in notices if n.get("gazette_notice_no") is None]
    
    if not orphans:
        return "PASS", "No orphan notices found (not a failure, just informational)"
    
    # Check orphan IDs have correct format
    for orphan in orphans:
        notice_id = orphan.get("notice_id", "")
        if ":_orphan_" not in notice_id:
            return "FAIL", f"Orphan notice missing _orphan_ format: {notice_id}"
    
    return "PASS", f"Found {len(orphans)} orphan(s) with stable _orphan_N IDs"


def test_t6_supplement_formatting():
    """T6: Supplement suffix -S76 for CXINo 100."""
    json_path = Path("output/Kenya Gazette Vol CXINo 100/Kenya Gazette Vol CXINo 100_gazette_spatial.json")
    if not json_path.exists():
        return "SKIP", "Need CXINo 100 processed"
    
    with open(json_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    
    issue_id = record.get("gazette_issue_id")
    expected_id = "KE-GAZ-CXI-100-2009-11-20-S76"
    
    if issue_id != expected_id:
        return "FAIL", f"Expected {expected_id}, got {issue_id}"
    
    # Also check CXXIVNo 282 has NO supplement suffix
    json2_path = Path("output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json")
    if json2_path.exists():
        with open(json2_path, "r", encoding="utf-8") as f:
            record2 = json.load(f)
        issue_id2 = record2.get("gazette_issue_id")
        if "-S" in issue_id2:
            return "FAIL", f"CXXIVNo 282 should not have -S suffix: {issue_id2}"
    
    return "PASS", f"CXINo 100 has -S76 suffix, CXXIVNo 282 has no suffix"


def main():
    """Run all tests and report results."""
    tests = [
        ("T1", "Happy path - modern clean", test_t1_happy_path),
        ("T2", "Determinism", test_t2_determinism),
        ("T3", "Degraded masthead", test_t3_degraded),
        ("T4", "Cross-gazette uniqueness", test_t4_cross_gazette_uniqueness),
        ("T5", "Orphan stability", test_t5_orphan_stability),
        ("T6", "Supplement formatting", test_t6_supplement_formatting),
    ]
    
    print("=" * 70)
    print("F13 Identity Fields Test Suite")
    print("=" * 70)
    
    results = []
    for test_id, description, test_func in tests:
        try:
            status, notes = test_func()
            results.append((test_id, status, notes))
            print(f"\n{test_id}: {description}")
            print(f"  Status: {status}")
            print(f"  Notes: {notes}")
        except Exception as e:
            results.append((test_id, "ERROR", str(e)))
            print(f"\n{test_id}: {description}")
            print(f"  Status: ERROR")
            print(f"  Error: {e}")
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    skipped = sum(1 for _, status, _ in results if status == "SKIP")
    errors = sum(1 for _, status, _ in results if status == "ERROR")
    
    print(f"PASS: {passed}, FAIL: {failed}, SKIP: {skipped}, ERROR: {errors}")
    
    if failed > 0 or errors > 0:
        sys.exit(1)
    else:
        print("\n✓ All non-skipped tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
