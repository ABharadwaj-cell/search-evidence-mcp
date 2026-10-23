import socket
import pytest
from pydantic import ValidationError
from search_evidence.audit import audit_pages
from search_evidence.models import AuditInput, SearchInput
from search_evidence.search_console import analyze_search
from search_evidence.crawl import destination


def test_observed_findings_and_broken_link():
    report = audit_pages(
        AuditInput(
            pages=[
                {
                    "url": "https://example.com/",
                    "html": '<html><title>Same</title><meta name="robots" content=" none "><a href="/gone">x</a><img src="x"><script type="application/ld+json">{bad}</script></html>',
                },
                {"url": "https://example.com/gone", "html": "<title>Same</title>", "status": 404},
            ]
        )
    )
    codes = {f["code"] for f in report["findings"]}
    assert {
        "indexing_excluded",
        "broken_sampled_link",
        "duplicate_title",
        "image_alt_missing",
        "jsonld_invalid",
        "http_error",
    } <= codes


def test_decorative_alt_and_schema_are_not_errors():
    p = AuditInput(
        pages=[
            {
                "url": "https://example.com",
                "html": '<html lang="en"><title>A</title><h1>A</h1><img alt=""><script type="application/ld+json">{"@graph":[{"@type":"Article"}]}</script></html>',
            }
        ]
    )
    r = audit_pages(p)
    assert r["pages"][0]["schema_types"] == ["Article"]
    assert "image_alt_missing" not in {f["code"] for f in r["findings"]}


def row(day, clicks, impressions, position):
    return {
        "query": "test",
        "page": "https://example.com",
        "date": day,
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def test_weighted_metrics_not_average_ctr():
    p = SearchInput(rows=[row("2026-01-01", 1, 10, 1), row("2026-01-02", 90, 1000, 10)])
    r = analyze_search(p)["metrics"][0]
    assert r["ctr"] == pytest.approx(91 / 1010)
    assert r["position"] == pytest.approx(10010 / 1010)


def test_duplicate_grain_and_invalid_clicks_rejected():
    r = row("2026-01-01", 1, 10, 1)
    with pytest.raises(ValidationError):
        SearchInput(rows=[r, r])
    with pytest.raises(ValidationError):
        SearchInput(rows=[row("2026-01-01", 11, 10, 1)])


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "192.168.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "ff02::1",
    ],
)
def test_ssrf_private_dns_blocked(monkeypatch, address):
    monkeypatch.setenv("ALLOWED_CRAWL_HOSTS", "example.com")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(0, 0, 0, "", (address, 80))])
    with pytest.raises(ValueError, match="globally"):
        destination("https://example.com")


def test_allowlist_and_credentials(monkeypatch):
    monkeypatch.delenv("ALLOWED_CRAWL_HOSTS", raising=False)
    with pytest.raises(ValueError, match="allowed"):
        destination("https://example.com")
    with pytest.raises(ValueError, match="Credentials"):
        destination("https://user:pass@example.com")
