# CV Pipeline Memo

## Shared Rules

- Never invent employers, projects, dates, certifications, tools, or claims.
- Prefer omission over speculation when evidence is weak.
- Tailor emphasis, ordering, and wording to the job offer without changing facts.
- Keep the CV optimized for a single A4 page.
- Every selected project and certification must be traceable to a source ID.
- The markdown file is the human-readable contract artifact.
- The PDF stage may run only after validation marks the markdown as `validated: true`.

## Required Inputs

- `data/profile.json`
- `data/projekte.json`
- `data/cert.json`
- `data/portrait.jpeg`
- Job offering text or file path

## Required Outputs

- `result/cv.md`
- `result/cv_content.json`
- `result/validation_report.json`
- `result/cv.html`
- `result/cv.pdf`
