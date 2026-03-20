from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.cv.models import RequestedOutputs
from agents.cv.pipeline import run_pipeline
from agents.cv.run import build_parser
from agents.cv.utils import split_frontmatter


FIXTURE_BASE_DIR = Path(__file__).resolve().parents[1]


def make_temp_base_dir() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="cv-pipeline-test-"))
    shutil.copytree(FIXTURE_BASE_DIR / "people", temp_dir / "people")
    shutil.copytree(FIXTURE_BASE_DIR / "template", temp_dir / "template")
    return temp_dir


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = make_temp_base_dir()
        self.job_text = (
            "Senior AI Security Engineer for a bank. Focus on security testing, automation, "
            "OWASP, threat modeling and stakeholder communication."
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_parser_supports_new_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--person", "toni", "--cover-letter", "--career-path", "--no-cv"])
        self.assertEqual(args.person, "toni")
        self.assertTrue(args.cover_letter)
        self.assertTrue(args.learning_path)
        self.assertFalse(args.cv)

    def test_job_bound_outputs_require_job_text(self) -> None:
        with self.assertRaises(ValueError):
            run_pipeline(
                self.temp_dir,
                person_id="toni",
                requested_outputs=RequestedOutputs(cover_letter=True),
                run_id="missing-job",
            )

    def test_run_pipeline_creates_scoped_outputs(self) -> None:
        result = run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="job-run",
            requested_outputs=RequestedOutputs(
                cover_letter=True,
                interview_prep=True,
                style_guide=True,
                learning_path=True,
            ),
        )
        metadata = result.payload["metadata"]
        artifacts = result.payload["artifacts"]
        self.assertEqual(metadata["person_id"], "toni")
        self.assertEqual(metadata["run_id"], "job-run")
        self.assertIn("cover_letter_markdown", artifacts)
        self.assertIn("interview_prep_markdown", artifacts)
        self.assertIn("style_guide_markdown", artifacts)
        self.assertIn("learning_path_markdown", artifacts)
        self.assertTrue((self.temp_dir / "result" / "toni" / "job-run" / "manifest.json").exists())

    def test_cover_letter_is_marked_validated(self) -> None:
        run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="cover-letter",
            requested_outputs=RequestedOutputs(cover_letter=True),
        )
        markdown_path = self.temp_dir / "result" / "toni" / "cover-letter" / "cover_letter.md"
        frontmatter, _ = split_frontmatter(markdown_path.read_text(encoding="utf-8"))
        self.assertIs(frontmatter["validated"], True)

    def test_person_and_run_isolation(self) -> None:
        shutil.copytree(self.temp_dir / "people" / "toni", self.temp_dir / "people" / "alex")
        run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="run-one",
            requested_outputs=RequestedOutputs(),
        )
        run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="alex",
            run_id="run-two",
            requested_outputs=RequestedOutputs(learning_path=True),
        )
        self.assertTrue((self.temp_dir / "result" / "toni" / "run-one" / "manifest.json").exists())
        self.assertTrue((self.temp_dir / "result" / "alex" / "run-two" / "manifest.json").exists())

    def test_project_history_regression(self) -> None:
        result = run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="project-history",
            requested_outputs=RequestedOutputs(project_history=True),
        )
        self.assertIn("project_history_markdown", result.payload["artifacts"])

    def test_run_pipeline_supports_disabling_cv(self) -> None:
        result = run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="no-cv",
            requested_outputs=RequestedOutputs(cv=False, project_history=True),
        )
        artifacts = result.payload["artifacts"]
        self.assertNotIn("cv_markdown", artifacts)
        self.assertIn("project_history_markdown", artifacts)

    def test_no_enabled_outputs_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_pipeline(
                self.temp_dir,
                job_offer_text=self.job_text,
                person_id="toni",
                run_id="no-outputs",
                requested_outputs=RequestedOutputs(cv=False),
            )

    @patch.dict("os.environ", {"CV_REQUIRE_PDF": "true"})
    @patch("agents.cv.pipeline.render_pdf", side_effect=RuntimeError("renderer unavailable"))
    def test_require_pdf_fails_pipeline_when_pdf_rendering_breaks(self, _render_pdf_mock) -> None:
        with self.assertRaises(RuntimeError):
            run_pipeline(
                self.temp_dir,
                job_offer_text=self.job_text,
                person_id="toni",
                run_id="require-pdf-failure",
                requested_outputs=RequestedOutputs(),
            )

    def test_learning_path_contains_three_routes(self) -> None:
        run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="learning-routes",
            requested_outputs=RequestedOutputs(learning_path=True),
        )
        markdown_path = self.temp_dir / "result" / "toni" / "learning-routes" / "learning_path.md"
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn("## Route 1 - Tech-Expert Track", markdown)
        self.assertIn("## Route 2 - Management Track", markdown)
        self.assertIn("## Route 3 - Specialization Track", markdown)

    def test_interview_prep_includes_company_briefing(self) -> None:
        run_pipeline(
            self.temp_dir,
            job_offer_text=self.job_text,
            person_id="toni",
            run_id="interview-briefing",
            requested_outputs=RequestedOutputs(interview_prep=True),
        )
        markdown_path = self.temp_dir / "result" / "toni" / "interview-briefing" / "interview_prep.md"
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn("## Frage 1", markdown)
        self.assertIn("## Frage 2", markdown)
        self.assertIn("## Frage 3", markdown)
        self.assertIn("## Company Briefing - Kontext", markdown)
        self.assertIn("## Company Briefing - Prioritaeten", markdown)
        self.assertIn("## Company Briefing - Stakeholder", markdown)
        self.assertIn("## Company Briefing - Interviewton", markdown)
        self.assertIn("## Company Briefing - So sollten Sie sich positionieren", markdown)
        self.assertIn("Stellenanzeige", markdown)

    def test_interview_prep_bank_job_uses_regulated_cues(self) -> None:
        run_pipeline(
            self.temp_dir,
            job_offer_text=(
                "Senior Security Engineer for a bank with compliance, audit, risk, "
                "and governance ownership."
            ),
            person_id="toni",
            run_id="interview-briefing-bank",
            requested_outputs=RequestedOutputs(interview_prep=True),
        )
        markdown_path = self.temp_dir / "result" / "toni" / "interview-briefing-bank" / "interview_prep.md"
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn("reguliertes", markdown)
        self.assertIn("Compliance", markdown)


if __name__ == "__main__":
    unittest.main()
