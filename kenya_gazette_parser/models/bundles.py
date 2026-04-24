"""F22: Bundles model for write_envelope output selection.

``Bundles`` specifies which artifact files to write via ``write_envelope``.
Contract section 5 defines eight bundle names. F22 implements seven
(images is post-1.0). F21's five legacy keys remain valid via a mapping
in io.py.

Bundle -> filename mapping:
    gazette_spatial_json -> {stem}_gazette_spatial.json (F21 legacy, full Envelope)
    notices              -> {stem}_notices.json
    corrigenda           -> {stem}_corrigenda.json
    document_index       -> {stem}_index.json
    full_text            -> {stem}_spatial.txt
    spatial_markdown     -> {stem}_spatial_markdown.md
    tables               -> {stem}_tables.json
    debug_trace          -> {stem}_trace.json
    images               -> NOT IMPLEMENTED (raises NotImplementedError in F22)
    docling_markdown     -> {stem}_docling_markdown.md (F21 legacy)
    docling_json         -> {stem}_docling.json (F21 legacy)
"""

from __future__ import annotations

from kenya_gazette_parser.models.base import StrictBase


class Bundles(StrictBase):
    """Which artifact files to write via write_envelope.

    Contract section 5 defines eight bundle names. F22 implements seven
    (images is post-1.0). F21's five legacy keys remain valid via a
    mapping in io.py.
    """

    # Contract section 5 defaults: notices=True, corrigenda=True, others False
    notices: bool = True
    corrigenda: bool = True
    document_index: bool = False
    spatial_markdown: bool = False
    full_text: bool = False
    tables: bool = False
    debug_trace: bool = False
    images: bool = False

    # F21 legacy keys (not in contract section 5 but still supported)
    gazette_spatial_json: bool = True
    docling_markdown: bool = False
    docling_json: bool = False
