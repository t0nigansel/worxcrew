from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


@dataclass
class SourceBundle:
    person_id: str
    data_dir: Path
    profile_path: Path
    projects_path: Path
    certifications_path: Path
    profile: JsonDict
    projects: List[JsonDict]
    certifications: List[JsonDict]
    portrait_path: Path


@dataclass
class JobAnalysis:
    title: str
    summary: str
    keywords: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    raw_text: str = ""
    language: str = "de"
    tone: str = "direct"
    variant: Optional[str] = None


@dataclass
class EvidenceSelection:
    selected_project_ids: List[str]
    selected_certification_ids: List[str]
    selected_experience_ids: List[str]
    selected_clients: List[str]
    technology_groups: List[JsonDict]
    certification_groups: List[JsonDict]
    project_scores: Dict[str, float]
    certification_scores: Dict[str, float]


@dataclass
class CVContent:
    frontmatter: JsonDict
    body: JsonDict
    markdown: str


@dataclass
class ValidationReport:
    passed: bool
    corrections: List[str] = field(default_factory=list)
    markdown_path: Optional[Path] = None


@dataclass
class RequestedOutputs:
    cv: bool = True
    project_history: bool = False
    cover_letter: bool = False
    interview_prep: bool = False
    style_guide: bool = False
    learning_path: bool = False

    def as_dict(self) -> Dict[str, bool]:
        return {
            "cv": self.cv,
            "project_history": self.project_history,
            "cover_letter": self.cover_letter,
            "interview_prep": self.interview_prep,
            "style_guide": self.style_guide,
            "learning_path": self.learning_path,
        }
