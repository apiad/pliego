"""DocConfig — typed frontmatter → renderer config."""
from __future__ import annotations

import datetime as _dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Margin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: str = "2cm"
    y: str = "2cm"


class PliegoOptions(BaseModel):
    """The `pliego:` block of frontmatter. Unknown keys are rejected."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    papersize: str = "a4"
    margin: Margin = Field(default_factory=Margin)
    fontsize: str = "10pt"
    toc: bool = False
    toc_depth: int = Field(default=2, alias="toc-depth")
    section_numbering: str = Field(default="1.1.a", alias="section-numbering")


class DocConfig(BaseModel):
    """Top-level document config from frontmatter."""
    model_config = ConfigDict(extra="ignore")  # extras captured into metadata

    title: str
    subtitle: str | None = None
    date: str
    lang: str = "en"
    pliego: PliegoOptions = Field(default_factory=PliegoOptions)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> str:
        """Accept str, date, or datetime; normalize to ISO 8601 string."""
        if isinstance(v, (_dt.date, _dt.datetime)):
            return v.isoformat()[:10]
        return v

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any]) -> "DocConfig":
        known = {"title", "subtitle", "date", "lang", "pliego"}
        metadata = {k: v for k, v in data.items() if k not in known}
        config_data = {k: v for k, v in data.items() if k in known}
        config_data["metadata"] = metadata
        return cls.model_validate(config_data)
