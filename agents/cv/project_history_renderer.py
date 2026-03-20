"""Render the project history attachment as HTML preview and PDF."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import CVContent
from .utils import latex_escape, split_frontmatter, write_text


def _html_environment(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _latex_environment(template_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
    )
    env.filters["latex_escape"] = latex_escape
    return env


def render_project_history_html(
    content: CVContent,
    template_dir: Path,
    output_path: Path,
) -> Path:
    """Render the project history as an HTML preview file."""
    environment = _html_environment(template_dir)
    template = environment.get_template("project_history_reference.html.j2")
    css = (template_dir / "project_history_reference.css").read_text(encoding="utf-8")
    html = template.render(content=content.body, frontmatter=content.frontmatter, css=css)
    return write_text(output_path, html)


def render_project_history_pdf(
    content: CVContent,
    template_dir: Path,
    output_dir: Path,
    aux_output_dir: Path | None = None,
) -> Dict[str, str]:
    """Render the project history as a multi-page A4 PDF via xelatex."""
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_aux_output_dir = aux_output_dir or output_dir
    resolved_aux_output_dir.mkdir(parents=True, exist_ok=True)

    if not content.frontmatter.get("validated"):
        raise RuntimeError("Project history PDF rendering requires validated content.")

    environment = _latex_environment(template_dir)
    template = environment.get_template("project_history_reference.tex.j2")
    tex_path = resolved_aux_output_dir / "project_history.tex"
    pdf_path = output_dir / "project_history.pdf"
    aux_pdf_path = resolved_aux_output_dir / "project_history.pdf"
    log_path = resolved_aux_output_dir / "project_history.xelatex.log"

    tex_path.write_text(
        template.render(content=content.body, frontmatter=content.frontmatter),
        encoding="utf-8",
    )

    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(resolved_aux_output_dir),
        str(tex_path),
    ]

    process = subprocess.run(command, capture_output=True, text=True)
    log_path.write_text(
        process.stdout + "\n\nSTDERR\n\n" + process.stderr, encoding="utf-8"
    )
    if process.returncode != 0 or not aux_pdf_path.exists():
        raise RuntimeError(f"xelatex failed for project history. See {log_path}")
    shutil.copy2(aux_pdf_path, pdf_path)

    return {
        "tex": str(tex_path),
        "pdf": str(pdf_path),
        "log": str(log_path),
    }
