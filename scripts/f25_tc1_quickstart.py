#!/usr/bin/env python3
"""F25 TC1: Verify quickstart code from README runs correctly."""

from kenya_gazette_parser import parse_file, write_envelope

print("=== TC1: Quickstart code ===")
pdf_path = "pdfs/Kenya Gazette Vol CXXIVNo 282.pdf"
env = parse_file(pdf_path)

print(f"Issue: {env.issue.gazette_issue_id}")
print(f"Notices: {len(env.notices)}")
print(f"Document confidence: {env.document_confidence.mean_composite:.3f}")

# Access individual notices
for notice in env.notices[:3]:
    header = notice.gazette_notice_header or "(no header)"
    print(f"  - {notice.notice_id}: {header}")

# Verify expected values for CXXIVNo 282
expected_notices = 201
expected_issue = "KE-GAZ-CXXIV-282-2022-12-23"

assert len(env.notices) == expected_notices, f"Expected {expected_notices} notices, got {len(env.notices)}"
assert env.issue.gazette_issue_id == expected_issue, f"Expected {expected_issue}, got {env.issue.gazette_issue_id}"
assert 0.96 < env.document_confidence.mean_composite < 0.98, f"Mean composite {env.document_confidence.mean_composite} out of expected range"

print()
print("TC1: PASS")
