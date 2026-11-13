# Retired (ADR-13, ADR-14): Elasticsearch 2.4.6 is replaced by installer/images/elasticsearch8/Dockerfile and no
# manifest component builds this directory any more. The file stays as a pointer because review records of the
# original native build (PR #34) link to this path and review records stay verbatim (SPEC-06 section 8).
# It is deliberately not a build recipe: `docker build` of this file fails.
FROM scratch
RUN ["retired", "see installer/images/elasticsearch8"]
