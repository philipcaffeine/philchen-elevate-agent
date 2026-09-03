# Containerized Deployment for Altostrat HR Agent on Cloud Run
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project definition and install dependencies
COPY pyproject.toml .
RUN uv venv /opt/venv && uv pip install --no-cache -r <(uv pip compile pyproject.toml)

ENV PATH="/opt/venv/bin:$PATH"

# Copy application and knowledge base
COPY app/ ./app/
COPY SDD.md .
COPY agents-cli-manifest.yaml .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
