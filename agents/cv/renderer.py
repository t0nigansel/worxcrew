from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import CVContent
from .utils import split_frontmatter, write_text


DEFAULT_LAYOUT = "reference"


def _html_environment(template_dir: Path) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
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


def _render_pdf_with_playwright(html_path: Path, pdf_path: Path, log_path: Path) -> Dict[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is not installed. Install it with: "
            "'pip install playwright' and 'python -m playwright install chromium'."
        ) from error

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1240, "height": 1754})
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.emulate_media(media="screen")
            page.pdf(
                path=str(pdf_path),
                width="210mm",
                height="297mm",
                print_background=True,
                display_header_footer=False,
                margin={
                    "top": "0mm",
                    "right": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                },
                prefer_css_page_size=True,
            )
            browser.close()
    except Exception as error:
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        raise RuntimeError(f"Playwright PDF rendering failed. See {log_path}") from error

    log_path.write_text(
        "PDF engine: playwright/chromium\n"
        "Source: HTML\n"
        "Headers/footers: disabled\n"
        "Backgrounds: enabled\n",
        encoding="utf-8",
    )
    return {
        "pdf": str(pdf_path),
        "log": str(log_path),
    }


def render_pdf(
    content: CVContent,
    markdown_path: Path,
    template_dir: Path,
    output_dir: Path,
    aux_output_dir: Path | None = None,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_aux_output_dir = aux_output_dir or output_dir
    resolved_aux_output_dir.mkdir(parents=True, exist_ok=True)
    frontmatter, _ = split_frontmatter(markdown_path.read_text(encoding="utf-8"))
    if not frontmatter.get("validated"):
        raise RuntimeError("PDF rendering requires a validated markdown file.")

    pdf_path = output_dir / "cv.pdf"
    log_path = resolved_aux_output_dir / "cv.playwright.log"
    html_path = output_dir / "cv.html"
    if not html_path.exists():
        render_html(content, template_dir, html_path)

    return _render_pdf_with_playwright(html_path, pdf_path, log_path)
