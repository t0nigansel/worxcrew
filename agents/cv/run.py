from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agents.cv.pipeline import run_pipeline
else:
    from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a tailored CV from JSON data.")
    parser.add_argument(
        "--job-file",
        type=Path,
        help="Path to a text or markdown job offering.",
    )
    parser.add_argument(
        "--job-text",
        help="Inline job offering text. Overrides --job-file when both are set.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Base directory of the CV workspace.",
    )
    parser.add_argument(
        "--variant",
        help="Optional CV variant, for example: security_appsec.",
    )
    parser.add_argument(
        "--layout",
        default="reference",
        help="Optional layout, for example: reference or legacy_modern.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_offer_text = args.job_text or ""
    if args.job_file and not job_offer_text:
        job_offer_text = args.job_file.read_text(encoding="utf-8")

    result = run_pipeline(
        args.base_dir.resolve(),
        job_offer_text=job_offer_text,
        variant_name=args.variant or "",
        layout_name=args.layout or "reference",
    )
    print(f"Pipeline completed: {result.name}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for name, path in result.payload.get("artifacts", {}).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
