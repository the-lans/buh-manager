FROM python:3.12-slim AS base

WORKDIR /app


FROM base AS test

COPY . .
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir psycopg2-binary
CMD ["pytest"]


FROM base AS prod

COPY . .
RUN pip install --no-cache-dir -e "." && \
    pip install --no-cache-dir gunicorn psycopg2-binary
CMD ["sh", "-c", \
     "alembic upgrade head && \
      gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --access-logfile - \
        --error-logfile -"]
