# syntax=docker/dockerfile:1
# Elasticsearch 6.8.23 (the last 6.8 release; Log4j 2.17.1) built natively for linux/arm64 and
# linux/amd64 from the official OSS release tarball on a digest-pinned Temurin 11 JRE (ADR-07).
#
# Why: docker.elastic.co/elasticsearch/elasticsearch:6.3.1 is linux/amd64 only and carries a
# Log4Shell-vulnerable Log4j. osf.io uses this instance only for django-elasticsearch-metrics
# (index templates, yearly indices, aggregations), none of which needs X-Pack, so the OSS tarball is used: smaller, and no x86-only machine-learning binaries.
#
# Stages: `fetch` and `keystore` run on the *build* platform, so nothing runs under emulation; the
# final stage only copies files. The keystore is created at build time because Elasticsearch would
# otherwise write it into config/ at start, which a read-only root forbids.
ARG JRE_IMAGE=eclipse-temurin:11-jre@sha256:5dd0f12260b837ce636299e4fc0a10c7c70ed879d1f162470da6badd6f8f733d

FROM --platform=$BUILDPLATFORM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS fetch
ARG ES_VERSION=6.8.23
ARG ES_SHA512=14dbb2809b06499373c3ec5035d829d62255c2c93103618fbfe3d7d03cecf8847f654e83c78f765f23224126ff18ed713b959857e8ecf435c475b11bcd143d3f
ARG ES_URL=https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-oss-${ES_VERSION}.tar.gz
RUN set -eux; \
    apt-get update; apt-get install -y --no-install-recommends curl ca-certificates; \
    curl -fsSL -o /tmp/es.tar.gz "${ES_URL}"; \
    echo "${ES_SHA512}  /tmp/es.tar.gz" | sha512sum -c -; \
    mkdir -p /out/elasticsearch; \
    tar -xzf /tmp/es.tar.gz -C /out/elasticsearch --strip-components=1; \
    # -XX:UseAVX is an x86-only flag: on the aarch64 JVM it is a fatal "Unrecognized VM option"
    sed -i '/UseAVX/d' /out/elasticsearch/config/jvm.options; \
    mkdir -p /out/elasticsearch/data /out/elasticsearch/logs /out/elasticsearch/plugins; \
    chown -R 1000:1000 /out/elasticsearch
COPY --chown=1000:1000 elasticsearch.yml /out/elasticsearch/config/elasticsearch.yml

FROM --platform=$BUILDPLATFORM ${JRE_IMAGE} AS keystore
COPY --from=fetch /out/elasticsearch /usr/share/elasticsearch
RUN ["/usr/share/elasticsearch/bin/elasticsearch-keystore", "create"]
RUN ["chown", "-R", "1000:1000", "/usr/share/elasticsearch/config"]

FROM ${JRE_IMAGE}
ARG JRE_IMAGE
ARG ES_VERSION=6.8.23
# Provenance labels (SPEC-03 §3.4): the pinned base reference/digest and the upstream release packaged.
LABEL org.opencontainers.image.base.name="${JRE_IMAGE}" \
      org.opencontainers.image.base.digest="sha256:5dd0f12260b837ce636299e4fc0a10c7c70ed879d1f162470da6badd6f8f733d" \
      org.opencontainers.image.version="${ES_VERSION}" \
      org.opencontainers.image.title="grdm-dev/elasticsearch6" \
      org.opencontainers.image.description="Elasticsearch ${ES_VERSION} OSS (EOL, retired at M5) built natively from the official tarball for the GakuNin RDM developer environment (ADR-07)"
COPY --from=keystore --chown=1000:1000 /usr/share/elasticsearch /usr/share/elasticsearch
ENV PATH=/usr/share/elasticsearch/bin:$PATH
USER 1000:1000
WORKDIR /usr/share/elasticsearch
VOLUME /usr/share/elasticsearch/data
EXPOSE 9200 9300
CMD ["elasticsearch"]
