# Agent-Driven CV Generator

This workspace generates a tailored CV from structured JSON data in `agents/cv/data`.

`job_analyzer`, `cv_writer`, and `fact_checker` support two modes:

- deterministic fallback mode
- LLM-assisted mode through an OpenAI-compatible chat completions API

## Pipeline

1. `job_analyzer` extracts keywords and target emphasis from the job offering.
2. `evidence_selector` scores projects, skills, and certifications against that target.
3. `cv_writer` creates structured content plus `result/cv.md`.
4. `fact_checker` validates the markdown against the JSON sources and rewrites it if needed.
5. `pdf_renderer` creates `result/cv.html`, `result/cv.tex`, and `result/cv.pdf` when the local LaTeX toolchain is available.

## Run

Generic CV:

```bash
python3 -m agents.cv.run --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv
```

Tailored CV from a job ad file:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --job-file /path/to/job-offer.md
```

Render the reference layout explicitly:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --layout reference
```

Render the previous showcase layout:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --layout legacy_modern
```

## Optional LLM Mode

Set these environment variables before running:

```bash
export OPENAI_API_KEY=...
export CV_LLM_MODEL=...
export CV_LLM_BASE_URL=https://api.openai.com/v1
```

If `OPENAI_API_KEY` and `CV_LLM_MODEL` are missing, the pipeline falls back to the deterministic analyzer, writer, and validator.

## Outputs

- `result/source_bundle.json`
- `result/job_analysis.json`
- `result/job_analyzer_llm.json` when the analyzer used the LLM
- `result/selection.json`
- `result/cv_content.json`
- `result/cv.md`
- `result/validation_report.json`
- `result/cv_writer_llm.json` when the writer used the LLM
- `result/fact_checker_llm.json` when the fact checker used the LLM
- `result/cv.html`
- `result/cv.tex`
- `result/cv.pdf`

## Design

The editable design lives in `template/`:

- `cv_reference.css`, `cv_preview_reference.html.j2`, and `cv_pdf_reference.tex.j2` for the default reference layout
- `cv.css`, `cv_preview.html.j2`, and `cv_pdf.tex.j2` for the legacy modern layout
- `design_reference.md` with the extracted section/layout intent from the original sample PDF
