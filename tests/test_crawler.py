import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit
import pytest
import search_evidence.crawl as crawler
from search_evidence.models import CrawlInput


def test_redirect_is_checked_before_connect(monkeypatch):
    requests = []

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, method, path, headers):
            requests.append(path)

        def getresponse(self):
            return self

        status = 302

        def getheaders(self):
            return [("location", "/private")]

        def close(self):
            pass

    monkeypatch.setattr(crawler, "PinnedHTTP", Connection)
    monkeypatch.setattr(
        crawler, "destination", lambda u: (urlsplit(u), "example.com", 443, "93.184.216.34")
    )
    robots = RobotFileParser()
    robots.parse(["User-agent: *", "Disallow: /private"])
    with pytest.raises(ValueError, match="robots"):
        crawler.fetch(
            "https://example.com/",
            crawler.origin_key("https://example.com"),
            time.monotonic() + 10,
            robots,
        )
    assert requests == ["/"]


def test_crawler_same_origin_and_page_bound(monkeypatch):
    seen = []

    def fake_fetch(url, origin, deadline, robots=None):
        seen.append(url)
        if url.endswith("robots.txt"):
            return url, 200, {}, "User-agent: *\nDisallow: /private"
        return (
            url,
            200,
            {"content-type": "text/html"},
            '<title>Test</title><a href="/next">Next</a><a href="https://other.example/">Other</a><a href="/private">Private</a>',
        )

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    monkeypatch.setattr(crawler, "destination", lambda u: None)
    monkeypatch.setattr(crawler.time, "sleep", lambda n: None)
    r = crawler.crawl_site(CrawlInput(url="https://example.com/", max_pages=3))
    assert len(r["pages"]) == 2
    assert not any("other.example" in u or u.endswith("private") for u in seen)
    assert r["crawl"]["skipped"][0]["reason"] == "robots_disallowed"


def test_robots_failure_is_fail_closed(monkeypatch):
    monkeypatch.setattr(crawler, "destination", lambda u: None)
    monkeypatch.setattr(crawler, "fetch", lambda *args: (args[0], 503, {}, ""))
    with pytest.raises(ValueError, match="robots"):
        crawler.crawl_site(CrawlInput(url="https://example.com/"))

@pytest.mark.parametrize(
    "url, error",
    [
        ("https://@example.com/", "Credentials"),
        ("http://example.com:0/", "Nonstandard ports"),
        ("https://example.com:0/", "Nonstandard ports"),
    ],
)
def test_crawler_rejects_empty_userinfo_and_zero_port_before_dns(monkeypatch, url, error):
    monkeypatch.setenv("ALLOWED_CRAWL_HOSTS", "example.com")

    def unexpected_dns(*args, **kwargs):
        pytest.fail("Invalid authority must be rejected before DNS resolution")

    monkeypatch.setattr(crawler.socket, "getaddrinfo", unexpected_dns)
    with pytest.raises(ValueError, match=error):
        crawler.destination(url)
