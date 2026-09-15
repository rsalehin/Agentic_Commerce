# Shared image for the three Python backends (gateway, wallet, core).
# The service is selected by the compose `command`.
FROM python:3.12-slim

# uv for dependency resolution from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

# Project metadata + lockfile first (better layer caching).
COPY pyproject.toml uv.lock README.md ./
COPY gateway ./gateway
COPY agent ./agent
COPY wallet ./wallet
COPY core ./core
COPY fixtures ./fixtures

# Install runtime deps only (no ruff/mypy/pytest) into /app/.venv.
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0

EXPOSE 8080 8081 8082

# Default command; overridden per service in docker-compose.yml.
CMD ["python", "-m", "gateway.app"]
