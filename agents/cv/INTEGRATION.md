# Integration Guide — Project History + GitLab CI Pipeline

## Overview

Two features:

1. **Project History Attachment** — multi-page PDF listing all projects in detail
2. **GitLab CI Pipeline** — manual trigger with input parameters

---

## File Placement

### New files

```
.gitlab-ci.yml                                          ← GitLab CI config
Dockerfile                                              ← CI runner image
requirements-ci.txt                                     ← Python deps for image

agents/cv/project_history_writer.py                     ← Compose project data
agents/cv/project_history_validator.py                  ← Fact-check against JSON
agents/cv/project_history_renderer.py                   ← Render HTML + PDF
agents/cv/project_history_pipeline.py                   ← 3 BaseAgent subclasses

agents/cv/template/project_history_reference.html.j2
agents/cv/template/project_history_reference.css
agents/cv/template/project_history_reference.tex.j2
```

### Modified files

```
agents/cv/run.py        ← replace with run_updated.py
agents/cv/pipeline.py   ← replace with pipeline_final.py
```

---

## GitLab CI — Input Variables

Shown in the "Run pipeline" UI when triggered manually:

| Variable | Default | Description |
|---|---|---|
| `JOB_DESCRIPTION` | *(empty)* | Full job description text. Empty = generic CV. |
| `LANGUAGE` | `de` | Output language: `de` or `en` |
| `INCLUDE_PROJECT_HISTORY` | `false` | Generate project history: `true` / `false` |
| `VARIANT` | *(empty)* | `security_appsec`, `ai_security_automation`, or empty |
| `LAYOUT` | `reference` | `reference` or `legacy_modern` |

### LLM Variables (set in GitLab → Settings → CI/CD → Variables)

| Variable | Type | Notes |
|---|---|---|
| `CV_LLM_API_KEY` | Masked | API key |
| `CV_LLM_MODEL` | Variable | e.g. `claude-sonnet-4-20250514` |
| `CV_LLM_BASE_URL` | Variable | e.g. `https://api.anthropic.com/v1` |

### Artifacts (downloadable after run, expire in 30 days)

**Always:** `cv.md`, `cv.html`, `cv.pdf`

**When project history enabled:** `project_history.md`, `project_history.html`, `project_history.pdf`

### Docker Image

Build once, push to your GitLab registry:

```bash
docker build -t registry.gitlab.com/tonigansel/cv-pipeline:latest -f Dockerfile .
docker push registry.gitlab.com/tonigansel/cv-pipeline:latest
```

Update the `image:` line in `.gitlab-ci.yml` if your registry path differs.

---

## How It Works

**Language:** `--language` overrides the auto-detected language from the job description. The `JobAnalyzerAgent` sets `analysis.language` to the forced value, which all downstream agents use.

**Project History Toggle:** `--project-history` flag controls whether `CVOrchestrator` includes the 3 project history agents. When `false`, no project history files are generated.
