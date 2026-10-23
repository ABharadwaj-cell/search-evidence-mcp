"""Opt-in, same-origin crawler with pinned public DNS and robots enforcement."""

import http.client
import ipaddress
import os
import socket
import ssl
import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from .audit import audit_pages, page_facts
from .models import AuditInput, CrawlInput, PageInput

AGENT = "SearchEvidenceBot/0.1"
MAX_BYTES = 1_000_000


def destination(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("HTTP(S) required")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Credentials and fragments forbidden")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port != (443 if parsed.scheme == "https" else 80):
        raise ValueError("Nonstandard ports forbidden")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    allowed = {
        h.strip().lower() for h in os.environ.get("ALLOWED_CRAWL_HOSTS", "").split(",") if h.strip()
    }
    if host not in allowed:
        raise ValueError("Host is not explicitly allowed by ALLOWED_CRAWL_HOSTS")
    addresses = sorted({r[4][0] for r in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError("Destination must resolve exclusively to globally routable IP addresses")
    return parsed, host, port, addresses[0]


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, address, secure):
        super().__init__(host, port, timeout=8)
        self.address = address
        self.secure = secure

    def connect(self):
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        if self.secure:
            self.sock = ssl.create_default_context().wrap_socket(
                self.sock, server_hostname=self.host
            )


def fetch(url, origin, deadline, robots=None):
    """Resolve/check every redirect; connect to that exact address, retaining TLS SNI."""
    for _ in range(4):
        if time.monotonic() >= deadline:
            raise TimeoutError("Crawl time budget exhausted")
        if origin_key(url) != origin:
            raise ValueError("Cross-origin redirect blocked")
        if robots is not None and not robots.can_fetch(AGENT, url):
            raise ValueError("Redirect destination disallowed by robots")
        parsed, host, port, address = destination(url)
        connection = PinnedHTTP(host, port, address, parsed.scheme == "https")
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request(
                "GET", path, headers={"User-Agent": AGENT, "Accept-Encoding": "identity"}
            )
            response = connection.getresponse()
            headers = {k.lower(): v for k, v in response.getheaders()}
            if response.status in {301, 302, 303, 307, 308}:
                if "location" not in headers:
                    raise ValueError("Redirect missing Location")
                url = urldefrag(urljoin(url, headers["location"]))[0]
                continue
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("Compressed response refused")
            body = bytearray()
            while len(body) <= MAX_BYTES:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Crawl time budget exhausted")
                chunk = response.read(min(16384, MAX_BYTES + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError("Response exceeds 1 MB")
            return url, response.status, headers, bytes(body).decode("utf-8", errors="replace")
        finally:
            connection.close()
    raise ValueError("Redirect limit exceeded")


def origin_key(url):
    p = urlsplit(url)
    return p.scheme, p.hostname, p.port or (443 if p.scheme == "https" else 80)


def crawl_site(payload: CrawlInput) -> dict:
    start = urldefrag(payload.url)[0]
    origin = origin_key(start)
    destination(start)  # Fail before attempting even robots when not authorized.
    deadline = time.monotonic() + 120
    base = urlsplit(start)
    robots_url = f"{base.scheme}://{base.netloc}/robots.txt"
    _, status, _, body = fetch(robots_url, origin, deadline)
    if status not in {200, 404, 410}:
        raise ValueError("robots.txt could not be safely checked; crawl refused")
    robots = RobotFileParser()
    robots.parse(body.splitlines() if status == 200 else [])
    delay = max(0.5, robots.crawl_delay(AGENT) or 0)
    if delay > 10:
        raise ValueError("Requested crawl delay exceeds this interactive crawler's budget")
    queue, seen, pages, skipped = deque([(start, 0)]), set(), [], []
    while queue and len(seen) < payload.max_pages:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if not robots.can_fetch(AGENT, url):
            skipped.append({"url": url, "reason": "robots_disallowed"})
            continue
        time.sleep(delay)
        final, code, headers, html = fetch(url, origin, deadline, robots)
        if status == 200 and not robots.can_fetch(AGENT, final):
            raise ValueError("Redirect destination disallowed by robots")
        if "text/html" not in headers.get("content-type", "").lower():
            skipped.append({"url": final, "reason": "not_html"})
            continue
        page = PageInput(url=final, status=code, headers=headers, html=html)
        if final not in {p.url for p in pages}:
            pages.append(page)
        if sum(len(p.html) for p in pages) > 5_000_000:
            raise ValueError("Combined page budget exceeded")
        if depth < payload.max_depth:
            for link in page_facts(page)["links"]:
                if origin_key(link) == origin and link not in seen and len(queue) < 100:
                    queue.append((link, depth + 1))
    result = (
        audit_pages(AuditInput(pages=pages))
        if pages
        else {"kind": "search_audit", "findings": [], "pages": [], "limitations": []}
    )
    result["crawl"] = {
        "attempted": len(seen),
        "skipped": skipped,
        "max_pages": payload.max_pages,
        "robots_checked": True,
        "user_agent": AGENT,
    }
    result["limitations"] = [x for x in result["limitations"] if "caller" not in x]
    result["limitations"].append(
        "Bounded same-origin sample; UTF-8 decoding only, no cookies or JavaScript. Not a full site crawl."
    )
    return result
