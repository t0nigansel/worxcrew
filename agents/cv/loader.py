from __future__ import annotations

from pathlib import Path

from .models import SourceBundle
from .utils import read_json


def load_source_bundle(data_dir: Path) -> SourceBundle:
    profile_path = data_dir / "profile.json"
    projects_path = data_dir / "projekte.json"
    certs_path = data_dir / "cert.json"
    portrait_path = data_dir / "portrait.jpeg"

    return SourceBundle(
        data_dir=data_dir,
        profile=read_json(profile_path),
        projects=read_json(projects_path),
        certifications=read_json(certs_path),
        portrait_path=portrait_path,
    )
