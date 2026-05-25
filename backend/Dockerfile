FROM python:3.12-slim AS base

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1


FROM base AS test

COPY pyproject.toml ./
RUN uv sync --all-extras
COPY . .
CMD ["pytest"]


FROM base AS prod

COPY pyproject.toml ./
RUN uv sync --no-dev && \
    uv pip install --system gunicorn psycopg2-binary
COPY . .
CMD ["sh", "-c", \
     "alembic upgrade head && \
      gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --access-logfile - \
        --error-logfile -"]
