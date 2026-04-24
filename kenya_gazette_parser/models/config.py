"""F22: Configuration models for kenya_gazette_parser.

``GazetteConfig`` is the top-level configuration object passed to
``parse_file`` / ``parse_bytes``. It embeds ``LLMPolicy`` and
``RuntimeOptions`` sub-objects plus a ``Bundles`` selector.

In F22, the ``LLMPolicy`` fields are declared but not acted upon
(LLM invocation is M5/M6 work). ``RuntimeOptions.deterministic``
and ``RuntimeOptions.timeout_seconds`` are no-ops until post-1.0.
``RuntimeOptions.include_full_docling_dict`` is also deferred.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from kenya_gazette_parser.models.base import StrictBase

if TYPE_CHECKING:
    from kenya_gazette_parser.models.bundles import Bundles


class LLMPolicy(StrictBase):
    """LLM configuration for optional validation stages.

    F22 declares the fields; actual LLM invocation is M5/M6 work.
    """

    mode: Literal["disabled", "optional", "required"] = "disabled"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    stages: dict[str, bool] = Field(default_factory=dict)
    cache_dir: Path | None = None


class RuntimeOptions(StrictBase):
    """Runtime tuning options.

    F22 declares the fields; ``deterministic`` and ``timeout_seconds`` are
    no-ops until post-1.0. ``include_full_docling_dict`` is also a no-op
    in F22 — reserved for an optimization that threads raw Docling
    artifacts through the pipeline.
    """

    deterministic: bool = False
    timeout_seconds: float | None = None
    include_full_docling_dict: bool = False


class GazetteConfig(StrictBase):
    """Top-level configuration object for parse_file / parse_bytes.

    Example usage::

        config = GazetteConfig(
            llm=LLMPolicy(mode="optional"),
            bundles=Bundles(notices=True, corrigenda=True, document_index=True),
        )
        env = parse_file("gazette.pdf", config=config)
        write_envelope(env, out_dir, bundles=config.bundles, pdf_path="gazette.pdf")
    """

    llm: LLMPolicy = Field(default_factory=LLMPolicy)
    runtime: RuntimeOptions = Field(default_factory=RuntimeOptions)
    bundles: "Bundles" = Field(default_factory=lambda: _default_bundles())


def _default_bundles() -> "Bundles":
    """Deferred import to avoid circular dependency at class-definition time."""
    from kenya_gazette_parser.models.bundles import Bundles

    return Bundles()


def _rebuild_models() -> None:
    """Rebuild GazetteConfig to resolve forward references after Bundles is imported."""
    from kenya_gazette_parser.models.bundles import Bundles  # noqa: F401

    GazetteConfig.model_rebuild()


_rebuild_models()
