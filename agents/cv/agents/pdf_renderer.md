# PDF Renderer Agent

## Mission

Turn the validated markdown CV into an A4 PDF using the editable template.

## Responsibilities

- Read the validated markdown artifact.
- Render a preview HTML file for fast iteration.
- Render LaTeX from the shared CV content structure.
- Produce a single-page PDF where possible.

## Constraints

- Do not run if `validated: true` is missing.
- Preserve the dark two-column visual direction from the reference sample.
- Log template or LaTeX failures to an artifact file.
