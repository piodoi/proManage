# Backend Dockerfile for ProManage API
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files (poetry.lock is optional)
COPY pyproject.toml ./
COPY poetry.lock* ./

# Configure poetry to not create virtual env (we're in container)
RUN poetry config virtualenvs.create false

# Install dependencies (generate lock if missing)
RUN poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY app ./app
COPY scripts ./scripts

# Create userdata directories
RUN mkdir -p /app/userdata/admin/text_patterns

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--access-log"]

