from .audit import audit_pages
from .crawl import crawl_site
from .models import AuditInput, CrawlInput, SearchInput
from .search_console import analyze_search

REGISTRY = {
    "audit_html": (
        AuditInput,
        audit_pages,
        "Inspect supplied HTML for observable technical SEO issues; no network.",
    ),
    "analyze_search_console": (
        SearchInput,
        analyze_search,
        "Aggregate supplied Search Console rows and identify review candidates.",
    ),
    "crawl_site": (
        CrawlInput,
        crawl_site,
        "Fetch a bounded same-origin public website; requires operator ALLOWED_CRAWL_HOSTS allowlist; respects robots.",
    ),
}
