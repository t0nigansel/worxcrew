from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import CVContent
from .utils import latex_escape, split_frontmatter, write_text


DEFAULT_LAYOUT = "reference"


def _html_environment(template_dir: Path) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return environment


def _latex_environment(template_dir: Path) -> Environment:
    environment = Environment(
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
    environment.filters["latex_escape"] = latex_escape
    return environment


def _layout_assets(layout_name: str | None) -> Dict[str, str]:
    layout = str(layout_name or DEFAULT_LAYOUT).strip().lower()
    layouts = {
        "reference": {
            "html_template": "cv_preview_reference.html.j2",
            "css_file": "cv_reference.css",
            "pdf_template": "cv_pdf_reference.tex.j2",
        },
        "legacy_modern": {
            "html_template": "cv_preview.html.j2",
            "css_file": "cv.css",
            "pdf_template": "cv_pdf.tex.j2",
        },
    }
    return layouts.get(layout, layouts[DEFAULT_LAYOUT])


def render_html(content: CVContent, template_dir: Path, output_path: Path) -> Path:
    environment = _html_environment(template_dir)
    assets = _layout_assets(content.frontmatter.get("layout"))
    template = environment.get_template(assets["html_template"])
    css = (template_dir / assets["css_file"]).read_text(encoding="utf-8")
    html = template.render(content=content.body, frontmatter=content.frontmatter, css=css)
    return write_text(output_path, html)


def render_pdf(content: CVContent, markdown_path: Path, template_dir: Path, output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frontmatter, _ = split_frontmatter(markdown_path.read_text(encoding="utf-8"))
    if not frontmatter.get("validated"):
        raise RuntimeError("PDF rendering requires a validated markdown file.")

    environment = _latex_environment(template_dir)
    assets = _layout_assets(content.frontmatter.get("layout"))
    template = environment.get_template(assets["pdf_template"])
    tex_path = output_dir / "cv.tex"
    pdf_path = output_dir / "cv.pdf"
    log_path = output_dir / "cv.xelatex.log"

    tex_path.write_text(
        template.render(content=content.body, frontmatter=content.frontmatter),
        encoding="utf-8",
    )

    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(output_dir),
        str(tex_path),
    ]

    process = subprocess.run(command, capture_output=True, text=True)
    log_path.write_text(process.stdout + "\n\nSTDERR\n\n" + process.stderr, encoding="utf-8")
    if process.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(f"xelatex failed. See {log_path}")

    return {
        "tex": str(tex_path),
        "pdf": str(pdf_path),
        "log": str(log_path),
    }
