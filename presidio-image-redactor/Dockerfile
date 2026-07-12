FROM python:3.13.13-slim@sha256:2ba73a4dc380f21137fc75296abfa2add90b51fd10b609ce530b40cc097269b1

ARG NLP_CONF_FILE
ARG ANALYZER_CONF_FILE
ARG RECOGNIZER_REGISTRY_CONF_FILE
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

RUN apt-get update \
  && apt-get install build-essential tesseract-ocr ffmpeg libsm6 libxext6 curl --no-install-recommends -y \
  && rm -rf /var/lib/apt/lists/* \
  && tesseract -v

COPY ./pyproject.toml ./uv.lock /app/
# Install exactly the locked dependency graph (main + server extra, no dev
# group); the project itself is run from the copied source, not installed.
RUN pip install uv==0.11.6 \
    && uv sync --locked --no-cache --no-default-groups --extra server --no-install-project

# Install spaCy model during build (as root) so it's available to non-root user at runtime
RUN python -m spacy download en_core_web_lg

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1
CMD ["./entrypoint.sh"]
