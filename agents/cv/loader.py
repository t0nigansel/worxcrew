from __future__ import annotations

from pathlib import Path
from typing import List

from .models import SourceBundle
from .utils import read_json


PORTRAIT_CANDIDATES = ("portrait.jpeg", "portrait.jpg", "portrait.png", "portrait.webp")


def _resolve_legacy_bundle(base_dir: Path) -> Path | None:
    legacy_dir = base_dir / "data"
    if (legacy_dir / "profile.json").exists():
        return legacy_dir
    return None


def resolve_person_bundle_dir(base_dir: Path, person_id: str) -> Path:
    bundle_dir = base_dir / "people" / person_id
    if bundle_dir.exists():
        return bundle_dir

    legacy_dir = _resolve_legacy_bundle(base_dir)
    if legacy_dir and person_id in {"default", "toni"}:
        return legacy_dir

    raise FileNotFoundError(f"Unknown person '{person_id}'. Expected bundle under {base_dir / 'people'}")


def list_available_people(base_dir: Path) -> List[str]:
    people_dir = base_dir / "people"
    people = []
    if people_dir.exists():
        people.extend(
            path.name
            for path in sorted(people_dir.iterdir())
            if path.is_dir() and (path / "profile.json").exists()
        )

    legacy_dir = _resolve_legacy_bundle(base_dir)
    if legacy_dir and "toni" not in people:
        people.append("toni")
    return people


def _resolve_portrait_path(bundle_dir: Path) -> Path:
    # Accept portrait filenames case-insensitively so assets like
    # `portrait.JPG` work on case-sensitive filesystems (for example in CI).
    files_by_lower_name = {
        path.name.lower(): path
        for path in bundle_dir.iterdir()
        if path.is_file()
    }
    for name in PORTRAIT_CANDIDATES:
        candidate = files_by_lower_name.get(name)
        if candidate:
            return candidate
    raise FileNotFoundError(f"Missing portrait asset in {bundle_dir}")


def load_source_bundle(base_dir: Path, person_id: str = "toni") -> SourceBundle:
    data_dir = resolve_person_bundle_dir(base_dir, person_id)
    profile_path = data_dir / "profile.json"
    projects_path = data_dir / "projekte.json"
    certs_path = data_dir / "cert.json"
    portrait_path = _resolve_portrait_path(data_dir)

    return SourceBundle(
        person_id=person_id,
        data_dir=data_dir,
        profile_path=profile_path,
        projects_path=projects_path,
        certifications_path=certs_path,
        profile=read_json(profile_path),
        projects=read_json(projects_path),
        certifications=read_json(certs_path),
        portrait_path=portrait_path,
    )
