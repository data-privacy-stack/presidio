FROM ghcr.io/astral-sh/uv:0.11.15@sha256:e590846f4776907b254ac0f44b5b380347af5d90d668138ca7938d1b0c2f98d3 AS uv

FROM python:3.14-slim@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8

ENV PIP_NO_CACHE_DIR=1
# Install the locked dependencies into the system environment (no venv).
ENV UV_PROJECT_ENVIRONMENT=/usr/local

ENV PORT=3000
ENV WORKERS=1

WORKDIR /app

# Apply OS security updates.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./uv.lock /app/
# Install exactly the locked dependency graph (main + server extra, no dev
# group); the project itself is run from the copied source, not installed.
# uv is mounted from a pinned image for this step only (it never lands in a
# layer) and pip is removed afterwards: neither is needed at runtime.
RUN --mount=type=bind,from=uv,source=/uv,target=/usr/local/bin/uv \
    uv sync --locked --no-cache --no-default-groups --extra server --no-install-project \
    && pip uninstall -y pip setuptools wheel

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request as u; u.build_opener(u.ProxyHandler({})).open('http://localhost:${PORT}/health', timeout=2)"
CMD ["./entrypoint.sh"]
