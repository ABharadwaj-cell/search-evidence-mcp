# Concept research and scope — 2026-10-23

## References reviewed

README-level conceptual review, not source-code reuse or cloning:

- https://github.com/MutantAngelo/claude-seo — broad SEO workflows and specialized agent instructions; upstream AgriciDaniel/claude-seo.
- https://github.com/MutantAngelo/seomachine — research, writing and editorial workflows; upstream TheCraigHewitt/seomachine.
- https://github.com/MutantAngelo/marketingskills — a broad marketing skill catalog; upstream coreyhaines31/marketingskills. Its README already advertises Codex support. Renaming agent branding would not be meaningful differentiation.
- https://github.com/topics/marketing — sampled the visible topic listing, not every repository. Substantial existing products include Matomo, Plausible and Twenty; resource lists and prompt collections also appear. It would be false to describe the whole category as lacking substance.

This project is an original, narrower implementation. It does not include those projects' code, prompts, private business data, branding or copied skill files. No claim is made that concepts themselves are exclusive. MIT applies to this repository's original work, not third-party sources linked here.

## Opportunity assessment

| Workflow | Public signal | Build decision | Remaining validation |
|---|---|---|---|
| Actionable SEO evidence | Broad audit catalogs show demand for audits; users still need traceable findings and scoped actions | Static evidence, explicit heuristics and exportable remediation | Interview operators; test real sites and rendered-page gaps |
| Source-grounded editorial operations | Research/write/refresh workflows recur in the references | Source ledger, citation inventory, revision and refresh tools | Evaluate claim-support accuracy with human reviewers |
| Attribution discrepancy reconciliation | Multiple vendors explain why tools disagree, showing an existing competitive category | Transparent scope gates and exact-ID reconciliation | Test anonymized exports from real stacks; do not claim causal attribution |
| Experiment decision discipline | Common optimization workflow with numerical and stopping-rule pitfalls | Explicit assumptions, sample-ratio checks and fixed-horizon gates | Statistical review and exact/simulation methods for sparse data |

Additional public reading:
- https://www.usermaven.com/blog/marketing-attribution-discrepancies-between-tools — vendor-authored discussion; commercial bias applies.
- https://www.getseoheatmap.com/knowledge/content-audit-keep-update-merge-or-remove-using-search-console-data/ — practical content-audit workflow; not a search-demand estimate.

No access to aggregate private ChatGPT query logs was available. No keyword-volume dataset was purchased or measured. These are qualitative opportunity hypotheses, not a ranked list of the most queried needs, proof of market size, or claims that competitors have no substance.

## Deliberate release boundary

The first release ships working Python tools, MCP, a bounded OpenAI runner, reports and tests. It does not reproduce every reference subskill or line count. Future candidates include authenticated connectors, rendered audits, source entailment evaluation, reusable campaign playbooks and hosted OAuth deployments. Each needs its own acceptance tests and real-user evidence before being claimed as complete.
