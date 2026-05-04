#!/usr/bin/env python3
"""Extract CSV tables from "Groundfish risk table report.pdf".

The PDF was generated from Word and has selectable text, but Table 2 spans many
pages and wraps stock names across lines. This script uses `pdftotext -layout`
and then repairs those wrapped stock-name rows into a rectangular CSV.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "Groundfish risk table report.pdf"
TEXT = ROOT / "groundfish_risk_table_report.txt"
SUMMARY_CSV = ROOT / "groundfish_risk_table_summary.csv"
SCORES_CSV = ROOT / "groundfish_risk_table_scores.csv"

TABLE1_COLUMNS = [
    "year",
    "region",
    "total_risk_tables",
    "stocks_with_elevated_scores",
    "stocks_without_elevated_scores",
    "stocks_with_author_recommended_reductions",
    "stocks_with_reductions",
]

TABLE2_COLUMNS = [
    "region",
    "stock",
    "year",
    "assessment_related_considerations",
    "ecosystem_considerations",
    "fishery_informed_stock_considerations",
    "population_dynamics_considerations",
    "max_score",
    "author_suggested_reduction",
    "ssc_recommended_reduction",
]


def write_text_from_pdf() -> None:
    subprocess.run(
        ["pdftotext", "-layout", str(PDF), str(TEXT)],
        check=True,
        cwd=ROOT,
    )


def section(lines: list[str], start_pattern: str, end_pattern: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if re.search(start_pattern, line))
    end = next(i for i, line in enumerate(lines[start + 1 :], start + 1) if re.search(end_pattern, line))
    return lines[start:end]


def extract_table1(lines: list[str]) -> list[dict[str, str]]:
    table = section(lines, r"^Table 1\.", r"^Table 2\.")
    rows: list[dict[str, str]] = []
    row_re = re.compile(
        r"^\s*(20\d{2})\s+(Alaska|BSAI|GOA)\s+"
        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?\s*$"
    )
    for line in table:
        match = row_re.match(line)
        if not match:
            continue
        values = list(match.groups())
        values[-1] = values[-1] or ""
        rows.append(dict(zip(TABLE1_COLUMNS, values)))
    return rows


def skip_table2_nondata_line(line: str) -> bool:
    stripped = line.strip().lstrip("\f").strip()
    if not stripped:
        return True
    if stripped == "Fishery":
        return True
    if "Assessment" in stripped and "Population" in stripped and "Author" in stripped:
        return True
    if "related" in stripped and "Ecosystem" in stripped and "suggested" in stripped:
        return True
    if stripped.startswith("Region") and "Stock" in stripped and "Year" in stripped:
        return True
    if "C1 Groundfish Risk Table Update" in stripped or stripped == "December 2024":
        return True
    if stripped.startswith("Table 2."):
        return True
    if stripped.startswith("the risk table was") or stripped.startswith("provided in the"):
        return True
    if stripped.startswith("the Scientific and Statistical Committee"):
        return True
    if stripped.startswith("following deliberation"):
        return True
    return False


def value_at(tokens: list[tuple[str, int]], start: int, stop: int) -> str:
    values = [token for token, pos in tokens if start <= pos < stop]
    return " ".join(values)


def parse_table2_values(rest: str, offset: int) -> list[str]:
    tokens = [(m.group(), offset + m.start()) for m in re.finditer(r"\S+", rest)]
    scores = ["", "", "", "", ""]
    author: list[str] = []
    ssc: list[str] = []

    for token, pos in tokens:
        if re.fullmatch(r"[1-4]", token):
            if 30 <= pos < 44:
                scores[0] = token
                continue
            if 44 <= pos < 59:
                scores[1] = token
                continue
            if 59 <= pos < 73:
                scores[2] = token
                continue
            if 73 <= pos < 85:
                scores[3] = token
                continue
            if 85 <= pos < 99:
                scores[4] = token
                continue
        if 95 <= pos < 111:
            author.append(token)
        elif 111 <= pos < 140:
            ssc.append(token)

    return [*scores, " ".join(author), " ".join(ssc)]


def extract_table2(lines: list[str]) -> list[dict[str, str]]:
    table = section(lines, r"^Table 2\.", r"^Notes on PT or SSC Adjustment")
    row_re = re.compile(r"^\s*(BSAI|GOA)\s+(.*?)\s+(20\d{2})\b(.*)$")
    rows: list[dict[str, str]] = []
    pending_stock_parts: list[str] = []
    pending_value_parts: dict[str, list[str]] = {}

    for line in table:
        if skip_table2_nondata_line(line):
            continue

        match = row_re.match(line)
        if match:
            region, stock_part, year, rest = match.groups()
            stock_parts = [*pending_stock_parts, stock_part.strip()]
            stock = " ".join(part for part in stock_parts if part).strip()
            stock = re.sub(r"\s+", " ", stock)
            values = parse_table2_values(rest, match.start(4))
            row = dict(zip(TABLE2_COLUMNS, [region, stock, year, *values]))
            for column, parts in pending_value_parts.items():
                suffix = row[column]
                row[column] = " ".join([*parts, suffix]).strip()
            rows.append(row)
            pending_stock_parts = []
            pending_value_parts = {}
            continue

        stripped = line.strip()
        if stripped and not stripped.startswith("\f"):
            first_text_col = len(line) - len(line.lstrip())
            if first_text_col >= 99:
                pending_value_parts.setdefault("ssc_recommended_reduction", []).append(stripped)
            else:
                pending_stock_parts.append(stripped)

    return rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    write_text_from_pdf()
    lines = TEXT.read_text().splitlines()
    table1 = extract_table1(lines)
    table2 = extract_table2(lines)
    write_csv(SUMMARY_CSV, TABLE1_COLUMNS, table1)
    write_csv(SCORES_CSV, TABLE2_COLUMNS, table2)
    print(f"Wrote {len(table1)} rows to {SUMMARY_CSV.name}")
    print(f"Wrote {len(table2)} rows to {SCORES_CSV.name}")


if __name__ == "__main__":
    main()
