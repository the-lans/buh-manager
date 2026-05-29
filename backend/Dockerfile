FROM python:3.12-slim AS base

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv


FROM base AS test

COPY . .
RUN uv sync --all-extras
ENV PATH="/app/.venv/bin:$PATH"
CMD ["pytest"]


FROM base AS prod

COPY . .
RUN uv sync --no-dev && \
    uv pip install gunicorn psycopg2-binary
ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", \
     "alembic upgrade head && \
      gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --forwarded-allow-ips='*' \
        --access-logfile - \
        --error-logfile -"]
