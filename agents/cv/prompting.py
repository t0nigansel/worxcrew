from __future__ import annotations

from pathlib import Path


def read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def compose_stage_prompt(base_dir: Path, stage_name: str, include_design_reference: bool = False) -> str:
    parts = [
        read_prompt(base_dir / "agents" / "memo.md"),
        read_prompt(base_dir / "agents" / f"{stage_name}.md"),
    ]
    if include_design_reference:
        parts.append(read_prompt(base_dir / "template" / "design_reference.md"))
    return "\n\n".join(part for part in parts if part)
