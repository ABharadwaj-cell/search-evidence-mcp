# Contributing

Use Python 3.11 or later and a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
ruff check .
pip-audit
```

Submit a focused pull request with a failing example, intended behavior, evidence,
and relevant tests. Use only synthetic fixtures. Do not copy third-party implementations
without explicit license review and attribution. New calculations must document their
denominator, units, assumptions, null behavior and limitations. New network tools must
include SSRF and redirect tests. Keep credentials, generated outputs and customer data
out of commits. Contributions are under the repository's MIT license.
