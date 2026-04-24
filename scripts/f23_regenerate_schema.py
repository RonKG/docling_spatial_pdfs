"""Regenerate the checked-in envelope.schema.json file.

Run this after any model changes:
    python scripts/f23_regenerate_schema.py
Then commit the updated schema file.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import write_schema_file

if __name__ == "__main__":
    path = write_schema_file()
    print(f"Wrote: {path}")
