# ─────────────────────────────────────────────────────────────
# Docker image for the CV generation pipeline
#
# Build:  docker build -t registry.gitlab.com/tonigansel/cv-pipeline:latest .
# Push:   docker push registry.gitlab.com/tonigansel/cv-pipeline:latest
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

# ── System dependencies: xelatex + fonts ─────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-latex-recommended \
    fonts-lato \
    fontconfig \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
COPY requirements-ci.txt /tmp/requirements-ci.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ci.txt \
    && rm /tmp/requirements-ci.txt

WORKDIR /builds
