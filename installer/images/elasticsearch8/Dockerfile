# syntax=docker/dockerfile:1
# Elasticsearch 8.19.24 for the GakuNin RDM developer environment (grdm-dev/elasticsearch8, ADR-14):
# the official multi-architecture image, pinned by its index digest, with the two plugins the Japanese
# analyzer of osf.io's full-text search needs (analysis-kuromoji, analysis-icu), TLS and authentication on.
#
# Why this instead of ES 2 (ADR-13): osf.io's search runs on Elasticsearch 8 since RDM-osf.io-dev2027 PR #11, with
# the permission filter kept. The official image already runs as uid 1000, supports arm64 natively and has
# openssl, curl and unzip, so nothing here is compiled or emulated.
#
# Read-only root: the image's entrypoint writes the keystore (bootstrap password) into config/, so the running
# container mounts a tmpfs on config/ and grdm-entrypoint.sh fills it from config.dist/ (the original files plus
# our elasticsearch.yml) before handing over to the official entrypoint. The TLS key never leaves the data
# volume; only the public CA certificate is copied to /es-ca for the clients.
ARG ES_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.19.24@sha256:d6dfe6626d645cfec66e91009aca60c6c1bb6f94d34253528f24d8cea2f94ba6

FROM ${ES_IMAGE}
ARG ES_IMAGE
ARG ES_VERSION=8.19.24
LABEL org.opencontainers.image.base.name="${ES_IMAGE}" \
      org.opencontainers.image.base.digest="sha256:d6dfe6626d645cfec66e91009aca60c6c1bb6f94d34253528f24d8cea2f94ba6" \
      org.opencontainers.image.version="${ES_VERSION}" \
      org.opencontainers.image.title="grdm-dev/elasticsearch8" \
      org.opencontainers.image.description="Elasticsearch ${ES_VERSION} with analysis-kuromoji and analysis-icu, TLS and authentication, for the GakuNin RDM developer environment (ADR-14)"
RUN ["elasticsearch-plugin", "install", "--batch", "analysis-kuromoji", "analysis-icu"]
RUN ["cp", "-a", "/usr/share/elasticsearch/config", "/usr/share/elasticsearch/config.dist"]
USER root
# /es-ca is where the public CA certificate is published (a named volume takes the owner of this directory)
RUN ["sh", "-c", "mkdir -p /es-ca && chown 1000:0 /es-ca && chmod 0755 /es-ca"]
COPY --chown=1000:0 elasticsearch.yml /usr/share/elasticsearch/config.dist/elasticsearch.yml
COPY --chmod=0755 grdm-entrypoint.sh grdm-setup.sh /usr/local/bin/
USER 1000:0
ENTRYPOINT ["/usr/local/bin/grdm-entrypoint.sh"]
CMD ["eswrapper"]
