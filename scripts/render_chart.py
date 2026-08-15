"""Render a standalone HTML Liuyao chart from runtime JSON."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from render_chart_text import render as render_markdown


def render_report(report: str | None) -> str:
    """Render a small, safe Markdown subset for the final standalone report."""
    if not report or not report.strip():
        return ""
    blocks: list[str] = []
    list_items: list[str] = []

    def inline(value: str) -> str:
        escaped = html.escape(value.strip())
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        bullet = re.match(r"^(?:[-*]|\d+[.、])\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(4, len(heading.group(1)) + 1)
            blocks.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif bullet:
            flush_paragraph()
            list_items.append(f"<li>{inline(bullet.group(1))}</li>")
        elif line.startswith(">"):
            flush_paragraph()
            flush_list()
            blocks.append(f"<blockquote>{inline(line[1:])}</blockquote>")
        else:
            flush_list()
            paragraph.append(inline(line))
    flush_paragraph()
    flush_list()
    return '<section class="interpretation"><div class="report-label">综合解读</div>' + "".join(blocks) + "</section>"


def render_html(data: dict[str, object], report: str | None = None) -> str:
    """Render either a chart response or the unified {result, prompt} wrapper."""
    source = data.get("result") or data
    if not isinstance(source, dict) or not isinstance(source.get("chart"), dict):
        raise ValueError("input must contain a chart response or an object at 'result'")
    template_path = Path(__file__).resolve().parents[1] / "assets" / "liuyao-viewer.html"
    template = template_path.read_text(encoding="utf-8")
    embedded = json.dumps(json.dumps(source, ensure_ascii=False), ensure_ascii=False)[1:-1]
    embedded = embedded.replace("<", "\\u003c").replace(">", "\\u003e")
    report_json = json.dumps(render_report(report), ensure_ascii=False)
    report_json = report_json.replace("<", "\\u003c").replace(">", "\\u003e")
    return template.replace("__LIUYAO_DATA__", embedded).replace('"__LIUYAO_REPORT__"', report_json)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.chart.read_text(encoding="utf-8"))
    args.output.write_text(render_html(data), encoding="utf-8")
    markdown_output = args.markdown_output or args.output.with_suffix(".md")
    markdown_output.write_text(render_markdown(data), encoding="utf-8")


if __name__ == "__main__":
    main()
