# Kenya Gazette PDF Extraction Project

## Project Overview
This project focuses on extracting and structuring data from the Kenya Gazette PDFs, making it easier to access important legal and administrative notices in a user-friendly format. We utilize OCR technologies along with a robust parsing pipeline to convert scanned PDFs into structured JSON data that can be easily interpreted and processed.

## Motivation
The Kenya Gazette serves as an essential record of government decisions, public notices, and legal information in Kenya. Improving the accessibility of this information helps enhance transparency and accountability in governance. This initiative aims to streamline how these documents are processed, ensuring critical information is readily available to the public and other stakeholders.

## Current Status
As of now, the pipeline consists of the following features:
- **Docling Extraction**: Converts PDF files to structured JSON format along with metadata.
- **Spatial Reading Order Correction**: Band-level column detection that handles two-column, full-width, and mixed layouts on the same page, emitting a `layout_confidence` per page.
- **Notice Splitting**: Strict + recovered header pass that also stitches multi-page continuations; every notice carries `provenance` (header match type, line span, stitched sources) for traceability.
- **Corrigenda Extraction**: Captures correction notices as distinct entries, providing a clearer understanding of amendments made to existing notices.
- **Confidence Scoring**: Every notice gets rule-based sub-scores (`notice_number`, `structure`, `spatial`, `boundary`, `table`) and a weighted `composite`; each document gets an aggregated `document_confidence` plus `ocr_quality`. See `docs/data-quality-confidence-scoring.md` for fields and thresholds.
- **Optional LLM Semantic Validation**: For notices with `composite < 0.70`, an OpenAI pass checks coherence, completeness, single-notice integrity, and legal structure; results are cached under `.llm_cache/` and blended into `composite_enhanced`.
- **Reporting, Calibration, Regression**: `confidence_report()` surfaces low-confidence notices across all outputs; `sample_for_calibration()` + `score_calibration()` measure per-band precision against hand-labelled samples; `check_regression()` compares mean composite to the snapshot at `tests/expected_confidence.json` and flags drops. See the *Validation and Tuning* section of `docs/data-quality-confidence-scoring.md` for the full workflow.

## Usage
1. **Input**: Drop Kenya Gazette PDFs into the `pdfs/` folder.
2. **Run the Pipeline**: Execute the notebook `gazette_docling_pipeline_spatial.ipynb` to process the PDFs.
3. **Output**: The structured data and markdown files will be generated in the `output/` directory for further review and analysis.

### Environment
Put secrets in a `.env` file at the project root (not committed). The LLM validation cell auto-loads it via `python-dotenv`.

- `OPENAI_API_KEY` -- required only if you set `ENABLE_LLM_VALIDATION = True` in the notebook.
- `DATABASE_URL`, `R2_*` -- required only for downstream storage steps.

After scoring a document, call `enhance_with_llm(record["gazette_notices"])` to run the semantic pass on notices below the confidence threshold. Responses are cached by body hash under `.llm_cache/` so reruns cost nothing.

## Library Functionality
The project will evolve into a fully contained library that allows users to programmatically access and retrieve documents from the Kenya Gazette. This library will expose functions to search and fetch specific gazette notices by parameters such as notice number, date, or keywords.

## Integration
To integrate this library into another application, you will need to include the library as a dependency. Detailed instructions will be provided on how to instantiate the library and call its fetch functions.

## Setup Instructions
Once the library is installed, you can use it as follows:
1. Import the library into your project.
2. Initialize the library with necessary configuration (e.g., API keys, base URLs).
3. Call the relevant function to pull the required gazette documents.

For more details on known issues, confidence-scoring design, or future improvements, see `docs/known-issues.md`, `docs/data-quality-confidence-scoring.md`, and `spatial_reorder_changelog.md`.

