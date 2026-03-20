"""CLI entry point for the CV and application documents pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agents.cv.loader import list_available_people
    from agents.cv.models import RequestedOutputs
    from agents.cv.pipeline import run_pipeline
else:
    from .loader import list_available_people
    from .models import RequestedOutputs
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
        "--person",
        default="toni",
        help="Person bundle id under people/<person_id>.",
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
    parser.add_argument(
        "--language",
        default="de",
        choices=["de", "en"],
        help="Output language: 'de' (German, default) or 'en' (English).",
    )
    parser.add_argument(
        "--cv",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate CV output (use --no-cv to disable).",
    )
    parser.add_argument(
        "--project-history",
        action="store_true",
        default=False,
        help="Include the project history attachment PDF.",
    )
    parser.add_argument(
        "--cover-letter",
        action="store_true",
        default=False,
        help="Generate a source-bound cover letter.",
    )
    parser.add_argument(
        "--interview-prep",
        action="store_true",
        default=False,
        help="Generate interview prep notes for the job posting.",
    )
    parser.add_argument(
        "--style-guide",
        action="store_true",
        default=False,
        help="Generate style guidance for the interview.",
    )
    parser.add_argument(
        "--learning-path",
        "--career-path",
        dest="learning_path",
        action="store_true",
        default=False,
        help="Generate career path guidance.",
    )
    parser.add_argument(
        "--list-people",
        action="store_true",
        default=False,
        help="List available people and exit.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    base_dir = args.base_dir.resolve()

    if args.list_people:
        for person_id in list_available_people(base_dir):
            print(person_id)
        return 0

    job_offer_text = args.job_text or ""
    if args.job_file and not job_offer_text:
        job_offer_text = args.job_file.read_text(encoding="utf-8")

    requested_outputs = RequestedOutputs(
        cv=args.cv,
        project_history=args.project_history,
        cover_letter=args.cover_letter,
        interview_prep=args.interview_prep,
        style_guide=args.style_guide,
        learning_path=args.learning_path,
    )

    result = run_pipeline(
        base_dir,
        job_offer_text=job_offer_text,
        variant_name=args.variant or "",
        layout_name=args.layout or "reference",
        language=args.language or "de",
        person_id=args.person or "toni",
        requested_outputs=requested_outputs,
    )
    print(f"Pipeline completed: {result.name}")
    print(f"person_id: {result.payload.get('metadata', {}).get('person_id')}")
    print(f"run_id: {result.payload.get('metadata', {}).get('run_id')}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for name, path in result.payload.get("artifacts", {}).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
