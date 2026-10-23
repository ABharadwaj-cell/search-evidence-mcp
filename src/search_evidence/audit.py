"""HTML checks. Findings describe evidence, never promise rankings."""

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import AuditInput, Finding, PageInput


def page_facts(page: PageInput) -> dict:
    soup = BeautifulSoup(page.html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
    canonicals = soup.find_all("link", rel=lambda v: v and "canonical" in v)
    robots = [
        str(t.get("content", ""))
        for t in soup.find_all("meta")
        if str(t.get("name", "")).lower() in {"robots", "googlebot"}
    ]
    robots.append(next((v for k, v in page.headers.items() if k.lower() == "x-robots-tag"), ""))
    headings = [
        {"level": int(t.name[1]), "text": t.get_text(" ", strip=True)}
        for t in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    ]
    links = sorted(
        {
            urldefrag(urljoin(page.url, str(a["href"])))[0]
            for a in soup.find_all("a", href=True)
            if urlsplit(urljoin(page.url, str(a["href"]))).scheme in {"http", "https"}
        }
    )
    schema_types, schema_errors = set(), []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
            pending, visited = [data], 0
            while pending:
                item = pending.pop()
                visited += 1
                if visited > 10_000:
                    raise ValueError("JSON-LD node limit exceeded")
                if isinstance(item, dict):
                    types = item.get("@type", [])
                    if isinstance(types, str):
                        types = [types]
                    if isinstance(types, list):
                        schema_types.update(t for t in types if isinstance(t, str))
                    pending.extend(item.values())
                elif isinstance(item, list):
                    pending.extend(item)
        except (ValueError, RecursionError) as exc:
            schema_errors.append(type(exc).__name__)
    missing_alt = sum(1 for img in soup.find_all("img") if not img.has_attr("alt"))
    for element in soup(["script", "style", "noscript", "template"]):
        element.decompose()
    text = soup.get_text(" ", strip=True)
    return {
        "url": page.url,
        "status": page.status,
        "title": title,
        "description": str(description.get("content", "")) if description else "",
        "canonicals": [urljoin(page.url, str(c.get("href", ""))) for c in canonicals],
        "robots": ",".join(robots).lower(),
        "headings": headings,
        "lang": str(soup.html.get("lang", "")) if soup.html else "",
        "links": links,
        "missing_alt": missing_alt,
        "word_count": len(text.split()),
        "schema_types": sorted(schema_types),
        "schema_errors": schema_errors,
        "content_sha256": hashlib.sha256(page.html.encode()).hexdigest(),
    }


def audit_pages(payload: AuditInput) -> dict:
    facts = [page_facts(page) for page in payload.pages]
    findings: list[Finding] = []

    def add(fact, code, severity, evidence, action, confidence="observed"):
        findings.append(
            Finding(
                url=fact["url"],
                code=code,
                severity=severity,
                evidence=evidence,
                action=action,
                confidence=confidence,
            )
        )

    for f in facts:
        if f["status"] >= 400:
            add(
                f,
                "http_error",
                "high",
                f"HTTP {f['status']}",
                "Restore the intended page or update links to a valid replacement.",
            )
        if {"noindex", "none"} & set(re.split(r"[,\s:]+", f["robots"])):
            add(
                f,
                "indexing_excluded",
                "high",
                f["robots"],
                "Confirm exclusion is intentional before changing robots directives.",
            )
        if not f["title"]:
            add(
                f,
                "title_missing",
                "medium",
                "No nonempty title element",
                "Write a specific title describing the page's purpose.",
            )
        if not f["description"]:
            add(
                f,
                "description_missing",
                "low",
                "No meta description",
                "Supply a helpful summary; Google may choose a different snippet.",
            )
        if len(f["canonicals"]) > 1:
            add(
                f,
                "multiple_canonicals",
                "high",
                repr(f["canonicals"]),
                "Emit one consistent canonical hint.",
            )
        elif f["canonicals"] and f["canonicals"][0] != f["url"]:
            add(
                f,
                "canonical_elsewhere",
                "info",
                f["canonicals"][0],
                "Verify this destination represents the preferred equivalent page.",
            )
        if not any(h["level"] == 1 and h["text"] for h in f["headings"]):
            add(
                f,
                "h1_missing",
                "low",
                "No nonempty H1",
                "Give the page a descriptive main heading for readers.",
            )
        previous = 0
        for h in f["headings"]:
            if previous and h["level"] > previous + 1:
                add(
                    f,
                    "heading_skip",
                    "low",
                    f"H{previous} followed by H{h['level']}",
                    "Review heading hierarchy for accessibility.",
                )
                break
            previous = h["level"]
        if f["missing_alt"]:
            add(
                f,
                "image_alt_missing",
                "low",
                f"{f['missing_alt']} images lack alt attributes",
                "Describe meaningful images; use empty alt for decorative ones.",
            )
        if not f["lang"]:
            add(
                f,
                "language_missing",
                "low",
                "html lang absent",
                "Declare the document language for assistive technology.",
            )
        if f["schema_errors"]:
            add(
                f,
                "jsonld_invalid",
                "medium",
                repr(f["schema_errors"]),
                "Fix JSON syntax; then validate supported markup and visible claims separately.",
            )
        if f["word_count"] < 80:
            add(
                f,
                "limited_extracted_text",
                "info",
                f"{f['word_count']} words in static HTML",
                "Inspect rendered content and page purpose; this is not a thin-content verdict.",
                "heuristic",
            )

    for field in ["title", "description"]:
        buckets = defaultdict(list)
        for f in facts:
            if f[field]:
                buckets[f[field].strip().casefold()].append(f)
        for group in buckets.values():
            if len(group) > 1:
                for f in group:
                    add(
                        f,
                        f"duplicate_{field}",
                        "medium",
                        f"Shared with {len(group) - 1} sampled pages: {f[field][:200]}",
                        "Differentiate genuinely distinct pages; review canonicalization for duplicates.",
                    )
    known = {f["url"]: f for f in facts}
    for f in facts:
        for link in f["links"]:
            if link in known and known[link]["status"] >= 400:
                add(
                    f,
                    "broken_sampled_link",
                    "medium",
                    f"{link} returned {known[link]['status']}",
                    "Update or remove this internal link.",
                )
    rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings.sort(key=lambda f: (rank[f.severity], f.url, f.code))
    return {
        "kind": "search_audit",
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"pages": len(facts), "method": "static_html"},
        "findings": [f.model_dump() for f in findings],
        "pages": facts,
        "limitations": [
            "Static HTML only; JavaScript rendering and Core Web Vitals are not measured.",
            "No ranking score, traffic uplift or AI citation probability is inferred.",
            "JSON-LD syntax/type detection does not certify eligibility or factual accuracy.",
            "Status and HTML supplied by the caller are not independently fetched.",
        ],
    }
