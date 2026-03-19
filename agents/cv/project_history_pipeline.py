"""Pipeline agents for the project history attachment."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from agents.BaseAgent import AgentContext, AgentResult, BaseAgent

from .llm import LLMError, OpenAICompatibleClient
from .llm_workflows import run_fact_checker_llm
from .models import CVContent, JobAnalysis, SourceBundle
from .project_history_renderer import render_project_history_html, render_project_history_pdf
from .project_history_validator import validate_project_history
from .project_history_writer import build_project_history_content
from .utils import write_json, write_text


class ProjectHistoryWriterAgent(BaseAgent):
    name = "project_history_writer"
    description = "Builds structured project history content from the full project list."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        analysis: JobAnalysis = context.data["job_analysis"]
        selection = context.data["selection"]

        content = build_project_history_content(
            bundle,
            analysis,
            selection,
            layout_name=context.data.get("layout_name", "reference"),
        )

        context.data["project_history_content"] = content

        content_path = context.record_artifact(
            "project_history_content",
            write_json(
                context.result_dir / "project_history_content.json",
                {"frontmatter": content.frontmatter, "body": content.body},
            ),
        )
        markdown_path = context.record_artifact(
            "project_history_markdown",
            write_text(context.result_dir / "project_history.md", content.markdown),
        )

        return AgentResult(
            name=self.name,
            payload={
                "content_path": str(content_path),
                "markdown_path": str(markdown_path),
            },
            artifacts={
                "project_history_content": str(content_path),
                "project_history_markdown": str(markdown_path),
            },
        )


class ProjectHistoryFactCheckerAgent(BaseAgent):
    name = "project_history_fact_checker"
    description = "Validates the project history against the JSON sources."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        content: CVContent = context.data["project_history_content"]
        warnings: List[str] = []

        corrected_content, report = validate_project_history(bundle, content)
        context.data["project_history_content"] = corrected_content
        context.data["project_history_validation_report"] = report

        content_path = context.record_artifact(
            "project_history_content",
            write_json(
                context.result_dir / "project_history_content.json",
                {
                    "frontmatter": corrected_content.frontmatter,
                    "body": corrected_content.body,
                },
            ),
        )
        markdown_path = context.record_artifact(
            "project_history_markdown",
            write_text(
                context.result_dir / "project_history.md",
                corrected_content.markdown,
            ),
        )
        report_path = context.record_artifact(
            "project_history_validation_report",
            write_json(
                context.result_dir / "project_history_validation_report.json",
                {"passed": report.passed, "corrections": report.corrections},
            ),
        )

        artifacts = {
            "project_history_content": str(content_path),
            "project_history_markdown": str(markdown_path),
            "project_history_validation_report": str(report_path),
        }

        return AgentResult(
            name=self.name,
            payload={"passed": report.passed, "corrections": report.corrections},
            warnings=warnings + report.corrections,
            artifacts=artifacts,
        )


class ProjectHistoryRendererAgent(BaseAgent):
    name = "project_history_renderer"
    description = "Renders the validated project history as HTML preview and A4 PDF."

    def run(self, context: AgentContext) -> AgentResult:
        content: CVContent = context.data["project_history_content"]
        validation_report = context.data.get("project_history_validation_report")

        if validation_report and not validation_report.passed:
            warning = "Project history PDF rendering skipped because validation did not pass."
            return AgentResult(
                name=self.name,
                warnings=[warning],
                payload={},
                artifacts={},
            )

        warnings: List[str] = []
        artifacts: Dict[str, str] = {}

        html_path = context.record_artifact(
            "project_history_html",
            render_project_history_html(
                content,
                context.template_dir,
                context.result_dir / "project_history.html",
            ),
        )
        artifacts["project_history_html"] = str(html_path)

        try:
            pdf_artifacts = render_project_history_pdf(
                content,
                context.template_dir,
                context.result_dir,
            )
            for name, path in pdf_artifacts.items():
                artifact_name = f"project_history_{name}"
                artifacts[artifact_name] = path
                context.record_artifact(artifact_name, Path(path))
        except Exception as error:
            warnings.append(str(error))

        return AgentResult(
            name=self.name,
            payload=artifacts,
            warnings=warnings,
            artifacts=artifacts,
        )
