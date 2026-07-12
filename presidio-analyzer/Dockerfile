FROM python:3.12-slim@sha256:804ddf3251a60bbf9c92e73b7566c40428d54d0e79d3428194edf40da6521286

ARG NLP_CONF_FILE=presidio_analyzer/conf/default.yaml
ARG ANALYZER_CONF_FILE=presidio_analyzer/conf/default_analyzer.yaml
ARG RECOGNIZER_REGISTRY_CONF_FILE=presidio_analyzer/conf/default_recognizers.yaml
ENV PIP_NO_CACHE_DIR=1

ENV ANALYZER_CONF_FILE=${ANALYZER_CONF_FILE}
ENV RECOGNIZER_REGISTRY_CONF_FILE=${RECOGNIZER_REGISTRY_CONF_FILE}
ENV NLP_CONF_FILE=${NLP_CONF_FILE}

ENV PORT=3000
ENV WORKERS=1

COPY ${ANALYZER_CONF_FILE} /app/${ANALYZER_CONF_FILE}
COPY ${RECOGNIZER_REGISTRY_CONF_FILE} /app/${RECOGNIZER_REGISTRY_CONF_FILE}
COPY ${NLP_CONF_FILE} /app/${NLP_CONF_FILE}

WORKDIR /app

# Install essential build tools and curl for health checks
RUN apt-get update \
  && apt-get install curl --no-install-recommends -y \
  && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml /app/

RUN pip install uv==0.11.6 \
    && uv pip install --system --no-cache -r pyproject.toml --extra server
    
# install nlp models specified in NLP_CONF_FILE or via nlp_configuration in ANALYZER_CONF_FILE
COPY ./install_nlp_models.py /app/

RUN python install_nlp_models.py \
    --conf_file ${NLP_CONF_FILE} \
    --analyzer_conf_file ${ANALYZER_CONF_FILE}

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1
CMD ["./entrypoint.sh"]
