"""Portable deliverables; escape HTML and spreadsheet formulas."""

import csv
import html
import io
import json
from pathlib import Path


def csv_cell(value):
    text = str(value if value is not None else "")
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def deliverables(result: dict) -> dict[str, str]:
    serialized = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    rows = result.get("findings", result.get("metrics", []))
    output = io.StringIO(newline="")
    if rows:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: csv_cell(v) for k, v in row.items()} for row in rows)
    summary = ["# Evidence report", "", f"Type: {result.get('kind', 'analysis')}", ""]
    for item in result.get("limitations", []):
        summary.append("- " + str(item).replace("\n", " "))
    summary += ["", "Machine-readable evidence is in report.json. Review before acting.", ""]
    return {
        "report.json": serialized + "\n",
        "report.csv": output.getvalue(),
        "report.md": "\n".join(summary),
        "report.html": '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Evidence report</title><h1>Evidence report</h1><pre>"
        + html.escape(serialized)
        + "</pre></html>",
    }


def write_reports(result: dict, directory: str):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    for name, content in deliverables(result).items():
        path = target / name
        if path.is_symlink():
            raise ValueError("Refusing to overwrite a symlink")
        path.write_text(content, encoding="utf-8")
