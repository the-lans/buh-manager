FROM python:3.12-slim AS base

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv


FROM base AS test

COPY pyproject.toml uv.lock ./
RUN uv sync --all-extras
ENV PATH="/app/.venv/bin:$PATH"
COPY . .
CMD ["pytest"]


FROM base AS prod

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --extra prod
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

RUN useradd --no-create-home --uid 1001 app && chown -R app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", \
     "alembic upgrade head && \
      exec gunicorn app.main:app \
        --workers ${WEB_CONCURRENCY:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --forwarded-allow-ips='*' \
        --access-logfile - \
        --error-logfile -"]
