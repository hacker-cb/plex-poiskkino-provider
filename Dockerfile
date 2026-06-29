# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POISKKINO_HOST=0.0.0.0 \
    POISKKINO_PORT=8000

WORKDIR /app

# Install the package (deps resolved from pyproject). README is required by the
# build backend; src holds the package.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Drop privileges.
RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"]

CMD ["python", "-m", "poiskkino_provider"]
