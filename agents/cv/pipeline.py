from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from agents.BaseAgent import AgentContext, AgentResult, BaseAgent

from .job_offer import analyze_job_offer
from .llm import LLMError, LLMSettings, OpenAICompatibleClient
from .llm_workflows import run_fact_checker_llm, run_job_analyzer_llm, run_writer_llm
from .loader import load_source_bundle
from .models import CVContent, JobAnalysis, SourceBundle
from .renderer import render_html, render_pdf
from .selector import select_evidence
from .utils import write_json, write_text
from .validator import validate_cv_content
from .variants import available_cv_variants, resolve_cv_variant
from .writer import build_cv_content


def _serializable_source_bundle(bundle: SourceBundle) -> Dict[str, object]:
    return {
        "data_dir": str(bundle.data_dir),
        "portrait_path": str(bundle.portrait_path),
        "profile": bundle.profile,
        "projects": bundle.projects,
        "certifications": bundle.certifications,
    }


class JobAnalyzerAgent(BaseAgent):
    name = "job_analyzer"
    description = "Reads the job offer and extracts tailoring signals."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        variant_name = context.data.get("variant_name", "")
        variant = resolve_cv_variant(bundle.profile, variant_name)
        analysis = analyze_job_offer(context.data.get("job_offer_text", ""), bundle, variant_name=variant_name)
        warnings: List[str] = []
        llm_artifact = None

        if variant_name and not variant:
            warnings.append(
                f"Unbekannte CV-Variante '{variant_name}'. Verfuegbar: {', '.join(available_cv_variants(bundle.profile)) or 'keine'}."
            )

        llm_client: OpenAICompatibleClient | None = context.data.get("llm_client")
        if llm_client and analysis.raw_text:
            try:
                analysis, llm_payload, llm_warnings = run_job_analyzer_llm(
                    llm_client,
                    context.root_dir,
                    bundle,
                    analysis,
                )
                warnings.extend(llm_warnings)
                llm_artifact = context.record_artifact(
                    "job_analyzer_llm",
                    write_json(context.result_dir / "job_analyzer_llm.json", llm_payload),
                )
            except LLMError as error:
                warnings.append(f"Job analyzer LLM fallback used: {error}")

        context.data["job_analysis"] = analysis

        path = context.record_artifact(
            "job_analysis",
            write_json(context.result_dir / "job_analysis.json", asdict(analysis)),
        )
        artifacts = {"job_analysis": str(path)}
        if llm_artifact:
            artifacts["job_analyzer_llm"] = str(llm_artifact)
        return AgentResult(name=self.name, payload=asdict(analysis), warnings=warnings, artifacts=artifacts)


class EvidenceSelectorAgent(BaseAgent):
    name = "evidence_selector"
    description = "Chooses the most relevant projects, skills, and certifications."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        analysis: JobAnalysis = context.data["job_analysis"]
        selection = select_evidence(bundle, analysis)
        context.data["selection"] = selection

        path = context.record_artifact(
            "selection",
            write_json(context.result_dir / "selection.json", asdict(selection)),
        )
        return AgentResult(name=self.name, payload=asdict(selection), artifacts={"selection": str(path)})


class CVWriterAgent(BaseAgent):
    name = "cv_writer"
    description = "Builds structured CV content and renders the markdown document."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        analysis: JobAnalysis = context.data["job_analysis"]
        selection = context.data["selection"]
        content = build_cv_content(bundle, analysis, selection, layout_name=context.data.get("layout_name", "reference"))
        warnings: List[str] = []
        llm_artifact = None

        llm_client: OpenAICompatibleClient | None = context.data.get("llm_client")
        if llm_client:
            try:
                content, llm_payload, llm_warnings = run_writer_llm(
                    llm_client,
                    context.root_dir,
                    bundle,
                    analysis,
                    selection,
                    content,
                )
                warnings.extend(llm_warnings)
                llm_artifact = context.record_artifact(
                    "cv_writer_llm",
                    write_json(context.result_dir / "cv_writer_llm.json", llm_payload),
                )
            except LLMError as error:
                warnings.append(f"Writer LLM fallback used: {error}")

        context.data["cv_content"] = content

        content_path = context.record_artifact(
            "cv_content",
            write_json(
                context.result_dir / "cv_content.json",
                {
                    "frontmatter": content.frontmatter,
                    "body": content.body,
                },
            ),
        )
        markdown_path = context.record_artifact("cv_markdown", write_text(context.result_dir / "cv.md", content.markdown))
        artifacts = {"cv_content": str(content_path), "cv_markdown": str(markdown_path)}
        if llm_artifact:
            artifacts["cv_writer_llm"] = str(llm_artifact)
        return AgentResult(
            name=self.name,
            payload={"content_path": str(content_path), "markdown_path": str(markdown_path)},
            warnings=warnings,
            artifacts=artifacts,
        )


class FactCheckerAgent(BaseAgent):
    name = "fact_checker"
    description = "Verifies the markdown against the source bundle and rewrites it if needed."

    def run(self, context: AgentContext) -> AgentResult:
        bundle: SourceBundle = context.data["source_bundle"]
        analysis: JobAnalysis = context.data["job_analysis"]
        selection = context.data["selection"]
        content: CVContent = context.data["cv_content"]
        warnings: List[str] = []
        llm_artifact = None
        llm_corrections: List[str] = []

        llm_client: OpenAICompatibleClient | None = context.data.get("llm_client")
        if llm_client:
            try:
                content, llm_payload, llm_warnings = run_fact_checker_llm(
                    llm_client,
                    context.root_dir,
                    bundle,
                    analysis,
                    selection,
                    content,
                )
                warnings.extend(llm_warnings)
                llm_corrections = [str(item) for item in (llm_payload.get("corrections") or []) if str(item).strip()]
                llm_artifact = context.record_artifact(
                    "fact_checker_llm",
                    write_json(context.result_dir / "fact_checker_llm.json", llm_payload),
                )
            except LLMError as error:
                warnings.append(f"Fact-checker LLM fallback used: {error}")

        corrected_content, report = validate_cv_content(bundle, content)
        report.corrections = llm_corrections + report.corrections
        context.data["cv_content"] = corrected_content
        context.data["validation_report"] = report

        content_path = context.record_artifact(
            "cv_content",
            write_json(
                context.result_dir / "cv_content.json",
                {
                    "frontmatter": corrected_content.frontmatter,
                    "body": corrected_content.body,
                },
            ),
        )
        markdown_path = context.record_artifact("cv_markdown", write_text(context.result_dir / "cv.md", corrected_content.markdown))
        report_path = context.record_artifact(
            "validation_report",
            write_json(
                context.result_dir / "validation_report.json",
                {
                    "passed": report.passed,
                    "corrections": report.corrections,
                },
            ),
        )
        artifacts = {
            "cv_content": str(content_path),
            "cv_markdown": str(markdown_path),
            "validation_report": str(report_path),
        }
        if llm_artifact:
            artifacts["fact_checker_llm"] = str(llm_artifact)
        return AgentResult(
            name=self.name,
            payload={"passed": report.passed, "corrections": report.corrections},
            warnings=warnings + report.corrections,
            artifacts=artifacts,
        )


class PdfRendererAgent(BaseAgent):
    name = "pdf_renderer"
    description = "Renders preview HTML and an A4 PDF from the verified document."

    def run(self, context: AgentContext) -> AgentResult:
        content: CVContent = context.data["cv_content"]
        markdown_path = context.artifacts["cv_markdown"]
        validation_report = context.data.get("validation_report")

        if validation_report and not validation_report.passed:
            warning = "PDF rendering skipped because validation did not pass."
            return AgentResult(name=self.name, warnings=[warning], payload={}, artifacts={})

        html_path = context.record_artifact(
            "cv_html",
            render_html(content, context.template_dir, context.result_dir / "cv.html"),
        )

        warnings: List[str] = []
        artifacts = {"cv_html": str(html_path)}
        try:
            pdf_artifacts = render_pdf(content, markdown_path, context.template_dir, context.result_dir)
            for name, path in pdf_artifacts.items():
                artifacts[f"cv_{name}"] = path
                context.record_artifact(f"cv_{name}", Path(path))
        except Exception as error:
            warnings.append(str(error))

        return AgentResult(name=self.name, payload=artifacts, warnings=warnings, artifacts=artifacts)


class CVOrchestrator(BaseAgent):
    name = "orchestrator"
    description = "Runs the complete CV generation flow."

    def __init__(self) -> None:
        self.agents = [
            JobAnalyzerAgent(),
            EvidenceSelectorAgent(),
            CVWriterAgent(),
            FactCheckerAgent(),
            PdfRendererAgent(),
        ]

    def run(self, context: AgentContext) -> AgentResult:
        source_bundle = load_source_bundle(context.root_dir / "data")
        context.data["source_bundle"] = source_bundle
        source_bundle_path = context.record_artifact(
            "source_bundle",
            write_json(context.result_dir / "source_bundle.json", _serializable_source_bundle(source_bundle)),
        )

        stage_results = []
        warnings: List[str] = []
        for agent in self.agents:
            result = agent.run(context)
            stage_results.append(
                {
                    "agent": result.name,
                    "warnings": result.warnings,
                    "artifacts": result.artifacts,
                }
            )
            warnings.extend(result.warnings)

        manifest = {
            "source_bundle": str(source_bundle_path),
            "metadata": context.metadata,
            "artifacts": {name: str(path) for name, path in context.artifacts.items()},
            "stages": stage_results,
        }
        manifest_path = context.record_artifact("manifest", write_json(context.result_dir / "manifest.json", manifest))

        return AgentResult(
            name=self.name,
            payload=manifest,
            warnings=warnings,
            artifacts={"manifest": str(manifest_path)},
        )


def run_pipeline(
    base_dir: Path,
    job_offer_text: str = "",
    variant_name: str = "",
    layout_name: str = "reference",
) -> AgentResult:
    result_dir = base_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    llm_settings = LLMSettings.from_env()
    context = AgentContext(
        root_dir=base_dir,
        result_dir=result_dir,
        template_dir=base_dir / "template",
        data={
            "job_offer_text": job_offer_text,
            "variant_name": variant_name,
            "layout_name": layout_name,
            "llm_client": OpenAICompatibleClient(llm_settings) if llm_settings else None,
        },
        metadata={
            "llm": llm_settings.public_dict() if llm_settings else {"enabled": False},
            "variant": variant_name,
            "layout": layout_name,
        },
    )
    orchestrator = CVOrchestrator()
    return orchestrator.run(context)
