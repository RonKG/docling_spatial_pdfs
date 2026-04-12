# Test Inputs (Legacy)

This folder contains sample Kenya Gazette PDFs used during early parser testing.

**Location:** Moved to `lab/test_inputs/` (2026-04-05) - exploratory test data belongs with lab scripts.

## Status

**Note:** This folder is deprecated. The canonical location for benchmark PDFs is `data/benchmarks/input_pdfs/`.

A copy of these files exists at:
- `data/benchmarks/input_pdfs/legacy_test_set/`

## Contents

Sample Kenya Gazette PDFs (Vol CXI, issues 100-104).

## Usage

For new testing:
- Place reference PDFs in `data/benchmarks/input_pdfs/`
- Update test scripts to read from the new location

Lab scripts reference this folder during exploratory work. This is acceptable for lab experiments, but production code should use `data/benchmarks/input_pdfs/`.
