FROM ghcr.io/astral-sh/uv:0.11.15@sha256:e590846f4776907b254ac0f44b5b380347af5d90d668138ca7938d1b0c2f98d3 AS uv

FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

ARG NLP_CONF_FILE=presidio_analyzer/conf/default.yaml
ARG ANALYZER_CONF_FILE=presidio_analyzer/conf/default_analyzer.yaml
ARG RECOGNIZER_REGISTRY_CONF_FILE=presidio_analyzer/conf/default_recognizers.yaml
ENV PIP_NO_CACHE_DIR=1
# Install the locked dependencies into the system environment (no venv).
ENV UV_PROJECT_ENVIRONMENT=/usr/local

ENV ANALYZER_CONF_FILE=${ANALYZER_CONF_FILE}
ENV RECOGNIZER_REGISTRY_CONF_FILE=${RECOGNIZER_REGISTRY_CONF_FILE}
ENV NLP_CONF_FILE=${NLP_CONF_FILE}

ENV PORT=3000
ENV WORKERS=1

COPY ${ANALYZER_CONF_FILE} /app/${ANALYZER_CONF_FILE}
COPY ${RECOGNIZER_REGISTRY_CONF_FILE} /app/${RECOGNIZER_REGISTRY_CONF_FILE}
COPY ${NLP_CONF_FILE} /app/${NLP_CONF_FILE}

WORKDIR /app

# Apply OS security updates.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./uv.lock /app/

# Install exactly the locked dependency graph (main + server extra, no dev
# group, project itself not installed — it is run from the copied source).
# Splitting this from the source COPY keeps the dependency layer cached until
# pyproject.toml/uv.lock change.
# uv is mounted from a pinned image for this step only, so it never lands in a layer.
RUN --mount=type=bind,from=uv,source=/uv,target=/usr/local/bin/uv \
    uv sync --locked --no-cache --no-default-groups --extra server --no-install-project

# install nlp models specified in NLP_CONF_FILE or via nlp_configuration in ANALYZER_CONF_FILE
COPY ./install_nlp_models.py /app/

# setuptools and wheel are only needed by the model download; pip stays for runtime spaCy downloads.
RUN python install_nlp_models.py \
    --conf_file ${NLP_CONF_FILE} \
    --analyzer_conf_file ${ANALYZER_CONF_FILE} \
    && pip uninstall -y setuptools wheel

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request as u; u.build_opener(u.ProxyHandler({})).open('http://localhost:${PORT}/health', timeout=2)"
CMD ["./entrypoint.sh"]
