"""Search Console export analysis preserving grain and weighted metrics."""

from collections import defaultdict

from .models import SearchInput


def analyze_search(payload: SearchInput) -> dict:
    grouped = defaultdict(lambda: {"clicks": 0, "impressions": 0, "position_sum": 0.0})
    by_query = defaultdict(dict)
    for row in payload.rows:
        g = grouped[(row.query, row.page)]
        g["clicks"] += row.clicks
        g["impressions"] += row.impressions
        g["position_sum"] += row.position * row.impressions
    metrics = []
    for (query, page), g in sorted(grouped.items()):
        impressions = g["impressions"]
        metric = {
            "query": query,
            "page": page,
            "clicks": g["clicks"],
            "impressions": impressions,
            "ctr": g["clicks"] / impressions if impressions else None,
            "position": g["position_sum"] / impressions if impressions else None,
        }
        metrics.append(metric)
        if impressions >= payload.min_impressions:
            by_query[query][page] = metric
    overlaps = []
    for query, pages in sorted(by_query.items()):
        if len(pages) > 1:
            overlaps.append(
                {
                    "query": query,
                    "pages": list(pages.values()),
                    "classification": "overlap_to_review",
                    "action": "Compare intent, date trends, device and country before considering consolidation.",
                }
            )
    opportunities = sorted(
        [
            r
            for r in metrics
            if r["impressions"] >= payload.min_impressions
            and r["position"] is not None
            and 4 <= r["position"] <= 20
        ],
        key=lambda r: (-r["impressions"], r["page"]),
    )
    return {
        "kind": "search_performance",
        "schema_version": "1.0",
        "period": {
            "start": min(r.date for r in payload.rows).isoformat(),
            "end": max(r.date for r in payload.rows).isoformat(),
        },
        "metrics": metrics,
        "overlap_candidates": overlaps,
        "review_queue": opportunities,
        "limitations": [
            "One row per date/query/page is required; omitted dimensions must be aggregated first.",
            "Anonymized queries and export/API row limits can omit data.",
            "Multiple ranking pages do not prove harmful cannibalization.",
            "Position is impression-weighted; CTR is clicks divided by impressions, never average row CTR.",
            "Review queue is a heuristic, not predicted incremental traffic.",
        ],
    }
