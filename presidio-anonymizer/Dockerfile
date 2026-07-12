FROM python:3.14-slim@sha256:bc389f7dfcb21413e72a28f491985326994795e34d2b86c8ae2f417b4e7818aa

ENV PIP_NO_CACHE_DIR=1

ENV PORT=3000
ENV WORKERS=1

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml /app/
RUN pip install uv==0.11.6 \
    && uv pip install --system --no-cache -r pyproject.toml --extra server

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1
CMD ["./entrypoint.sh"]
