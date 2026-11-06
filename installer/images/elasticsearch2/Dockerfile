# syntax=docker/dockerfile:1
# Elasticsearch 2.4.6 (end of life; retired at M5, SPEC-00 §5) built natively for linux/arm64 and
# linux/amd64 from the official release tarball on a digest-pinned Temurin 8 JRE (ADR-07).
#
# Why: the only official image, elasticsearch:2 (Docker Hub), ships linux/amd64 only. Under Rosetta
# on Apple Silicon it needed 38 minutes to open port 9200 on a fresh data directory (real install
# run 19, DEMO-20), while the same program on a native arm64 JRE starts in 5 seconds.
#
# Two stages: the fetch stage runs on the *build* platform (natively, so curl/sha256sum/tar never
# run under emulation — tar fails with "Function not implemented" under Rosetta), the final stage is
# the *target* platform and only copies files. Properties: non-root (uid 1000, the hardening
# baseline, so no owner-init container), checksum-verified tarball, no plugins, configuration from
# the Compose environment (ES_HEAP_SIZE) and the mounted data volume. The bundled JNA 4.1 has no
# aarch64 native library, so Elasticsearch logs that native support (mlockall, seccomp filter) is
# disabled; acceptable for a development instance that never leaves the Compose network.
ARG JRE_IMAGE=eclipse-temurin:8-jre@sha256:377fe8e36a4b1530d9d52020069367ef44313fa891a82ae102b1016a6a3a72f5

FROM --platform=$BUILDPLATFORM debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc AS fetch
ARG ES_VERSION=2.4.6
ARG ES_SHA256=5f7e4bb792917bb7ffc2a5f612dfec87416d54563f795d6a70637befef4cfc6f
ARG ES_URL=https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/${ES_VERSION}/elasticsearch-${ES_VERSION}.tar.gz
RUN set -eux; \
    apt-get update; apt-get install -y --no-install-recommends curl ca-certificates; \
    curl -fsSL -o /tmp/es.tar.gz "${ES_URL}"; \
    echo "${ES_SHA256}  /tmp/es.tar.gz" | sha256sum -c -; \
    mkdir -p /out/elasticsearch; \
    tar -xzf /tmp/es.tar.gz -C /out/elasticsearch --strip-components=1; \
    mkdir -p /out/elasticsearch/data /out/elasticsearch/logs /out/elasticsearch/plugins /out/elasticsearch/config/scripts; \
    chown -R 1000:1000 /out/elasticsearch
COPY elasticsearch.yml /out/elasticsearch/config/elasticsearch.yml

FROM ${JRE_IMAGE}
COPY --from=fetch --chown=1000:1000 /out/elasticsearch /usr/share/elasticsearch
ENV PATH=/usr/share/elasticsearch/bin:$PATH \
    ES_HEAP_SIZE=512m
USER 1000:1000
WORKDIR /usr/share/elasticsearch
VOLUME /usr/share/elasticsearch/data
EXPOSE 9200 9300
CMD ["elasticsearch"]
