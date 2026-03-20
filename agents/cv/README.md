# Agent-Driven CV Generator

This workspace generates a tailored CV and companion application documents from structured JSON data in `agents/cv/people/<person_id>`.

`job_analyzer`, `cv_writer`, and `fact_checker` support two modes:

- deterministic fallback mode
- LLM-assisted mode through an OpenAI-compatible chat completions API

## Pipeline

1. `job_analyzer` extracts keywords and target emphasis from the job offering.
2. `evidence_selector` scores projects, skills, and certifications against that target.
3. `cv_writer` creates structured content plus `result/cv.md`.
4. `fact_checker` validates the markdown against the JSON sources and rewrites it if needed.
5. `pdf_renderer` creates `result/cv.html`, `result/cv.tex`, and `result/cv.pdf` when the local LaTeX toolchain is available.
6. Optional companion documents can add:
   - `cover_letter`
   - `project_history`
   - `interview_prep` (3 likely questions + answer guidance + company briefing inferred from the job text)
   - `style_guide`
   - `learning_path`

## People

Person data live in:

- `agents/cv/people/<person_id>/profile.json`
- `agents/cv/people/<person_id>/projekte.json`
- `agents/cv/people/<person_id>/cert.json`
- `agents/cv/people/<person_id>/portrait.(jpeg|jpg|png|webp)`

List available people:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --list-people
```

## Run

Generic CV:

```bash
python3 -m agents.cv.run --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv
```

Tailored CV from a job ad file:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --person toni \
  --job-file /path/to/job-offer.md
```

Generate companion documents for a job run:

```bash
python3 -m agents.cv.run \
  --base-dir /Users/tonigansel/workspace/worxcrew/agents/cv \
  --person toni \
  --job-file /path/to/job-offer.md \
  --cover-letter \
  --interview-prep \
  --style-guide \
  --learning-path \
  --project-history
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

Outputs are stored per person and per run in two layers:

- User-facing files in `result/<person_id>/<run_id>/`
  - `cv.md`, `cv.html`, `cv.pdf` when CV is requested
  - `cover_letter.md` when requested
  - `interview_prep.md` when requested
  - `style_guide.md` when requested
  - `learning_path.md` when requested
  - `project_history.md`, `project_history.html`, `project_history.pdf` when requested
- Technical/internal files in `result/<person_id>/<run_id>/_internal/`
  - `manifest.json`, `source_bundle.json`, `job_analysis.json`, `selection.json`
  - content JSON sidecars, validation reports, LLM payloads, and renderer logs

## Design

The editable design lives in `template/`:

- `cv_reference.css`, `cv_preview_reference.html.j2`, and `cv_pdf_reference.tex.j2` for the default reference layout
- `cv.css`, `cv_preview.html.j2`, and `cv_pdf.tex.j2` for the legacy modern layout
- `design_reference.md` with the extracted section/layout intent from the original sample PDF
