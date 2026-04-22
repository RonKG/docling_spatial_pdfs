"""Shared strict Pydantic base for kenya_gazette_parser models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=False,
    )
