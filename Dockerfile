# syntax=docker/dockerfile:1

# ---------- Stage 1: build wheel ----------
FROM python:3.14-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip build \
    && python -m build --wheel --outdir /dist

# ---------- Stage 2: runtime ----------
FROM python:3.14-slim AS runtime

# Create an unprivileged user to run the control helper.
RUN groupadd --system --gid 1001 gitops \
    && useradd --system --uid 1001 --gid gitops --create-home gitops

WORKDIR /app

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GITOPS_LOG_LEVEL=INFO

USER gitops

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD gitops-platform --version || exit 1

ENTRYPOINT ["gitops-platform"]
CMD ["--help"]
