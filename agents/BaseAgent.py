from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AgentContext:
    root_dir: Path
    result_dir: Path
    template_dir: Path
    data: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_artifact(self, name: str, path: Path) -> Path:
        self.artifacts[name] = path
        return path


@dataclass
class AgentResult:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)


class BaseAgent(ABC):
    name = "base"
    description = ""

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError

    def __call__(self, context: AgentContext) -> AgentResult:
        return self.run(context)
