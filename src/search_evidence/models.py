"""Validated inputs and explicit, inspectable audit findings."""

from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


def public_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("An absolute HTTP(S) URL is required")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in URLs are forbidden")
    if len(value) > 2048:
        raise ValueError("URL exceeds 2048 characters")
    return value


class Finding(StrictModel):
    code: str
    severity: Literal["high", "medium", "low", "info"]
    url: str
    evidence: str
    action: str
    confidence: Literal["observed", "heuristic"] = "observed"


class PageInput(StrictModel):
    url: str
    html: str = Field(max_length=1_000_000)
    status: int = Field(default=200, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict, max_length=100)

    _url = field_validator("url")(public_url)


class AuditInput(StrictModel):
    pages: list[PageInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def bounded(self):
        if sum(len(p.html) for p in self.pages) > 5_000_000:
            raise ValueError("Combined HTML exceeds 5 MB")
        if len({p.url for p in self.pages}) != len(self.pages):
            raise ValueError("Duplicate page URLs are not allowed")
        return self


class SearchRow(StrictModel):
    query: str = Field(min_length=1, max_length=500)
    page: str
    date: date
    clicks: int = Field(ge=0, strict=True)
    impressions: int = Field(ge=0, strict=True)
    position: float = Field(ge=0)

    _page = field_validator("page")(public_url)

    @model_validator(mode="after")
    def consistent(self):
        if self.clicks > self.impressions:
            raise ValueError("Clicks cannot exceed impressions")
        if self.impressions > 0 and self.position < 1:
            raise ValueError("Observed positions must be at least 1")
        return self


class SearchInput(StrictModel):
    rows: list[SearchRow] = Field(min_length=1, max_length=20_000)
    min_impressions: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def unique_grain(self):
        keys = [(r.date, r.query, r.page) for r in self.rows]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate date/query/page rows; aggregate omitted dimensions first")
        return self


class CrawlInput(StrictModel):
    url: str
    max_pages: int = Field(default=5, ge=1, le=25)
    max_depth: int = Field(default=1, ge=0, le=3)

    _url = field_validator("url")(public_url)
