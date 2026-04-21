# Aegis monitor agent — production image
# Non-root, slim base, layer-cached dependency install.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: build tools for native wheels (eth-hash, coincurve transitively).
# We purge them after install to keep the final image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# Drop build-essential now that wheels are compiled.
RUN apt-get purge -y build-essential && apt-get autoremove -y

# Non-root runtime user.
RUN useradd --create-home --shell /bin/bash aegis
USER aegis

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "aegis_monitor.main:app", "--host", "0.0.0.0", "--port", "8000"]
