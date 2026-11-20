FROM python:3.12-slim

ENV POETRY_VERSION=1.8.4 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock* README.md ./
COPY apps ./apps

RUN /opt/poetry/bin/poetry install --no-ansi --only main

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "document_filler.main:app", "--host", "0.0.0.0", "--port", "8000"]