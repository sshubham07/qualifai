"""Report rendering — a Jinja2 template, never LLM-written HTML. Same layout every time."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_report_html(report: dict[str, Any]) -> str:
    return _ENV.get_template("report.html.j2").render(r=report)
