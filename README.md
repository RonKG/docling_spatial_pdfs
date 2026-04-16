# Kenya Gazette PDF Extraction Project

## Project Overview
This project focuses on extracting and structuring data from the Kenya Gazette PDFs, making it easier to access important legal and administrative notices in a user-friendly format. We utilize OCR technologies along with a robust parsing pipeline to convert scanned PDFs into structured JSON data that can be easily interpreted and processed.

## Motivation
The Kenya Gazette serves as an essential record of government decisions, public notices, and legal information in Kenya. Improving the accessibility of this information helps enhance transparency and accountability in governance. This initiative aims to streamline how these documents are processed, ensuring critical information is readily available to the public and other stakeholders.

## Current Status
As of now, the pipeline consists of the following features:
- **Docling Extraction**: Converts PDF files to structured JSON format along with metadata.
- **Spatial Reading Order Correction**: Fixes the two-column layout reading order to ensure logical text flow.
- **Notice Splitting**: Accurately divides contents into individual gazette notices based on defined patterns, including improvements to mitigate false positives.
- **Corrigenda Extraction**: Newly added feature that captures correction notices as distinct entries, providing a clearer understanding of amendments made to existing notices.

## Usage
1. **Input**: Drop Kenya Gazette PDFs into the `pdfs/` folder.
2. **Run the Pipeline**: Execute the notebook `gazette_docling_pipeline_spatial.ipynb` to process the PDFs.
3. **Output**: The structured data and markdown files will be generated in the `output/` directory for further review and analysis.

## Library Functionality
The project will evolve into a fully contained library that allows users to programmatically access and retrieve documents from the Kenya Gazette. This library will expose functions to search and fetch specific gazette notices by parameters such as notice number, date, or keywords.

## Integration
To integrate this library into another application, you will need to include the library as a dependency. Detailed instructions will be provided on how to instantiate the library and call its fetch functions.

## Setup Instructions
Once the library is installed, you can use it as follows:
1. Import the library into your project.
2. Initialize the library with necessary configuration (e.g., API keys, base URLs).
3. Call the relevant function to pull the required gazette documents.

For more details on known issues or future improvements, see `docs/known-issues.md` and `spatial_reorder_changelog.md`.  
