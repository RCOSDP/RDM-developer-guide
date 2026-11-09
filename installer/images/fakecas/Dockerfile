# syntax=docker/dockerfile:1
# FakeCAS (development login stub) rebuilt from a pinned upstream commit with a current Go (ADR-07).
#
# Why: quay.io/centerforopenscience/fakecas:master is linux/amd64 only and was compiled with an old
# Go, so its standard library carries most of the image's findings. Cross-compiled on the build
# platform, so nothing runs under emulation. The golang.org/x modules are raised to current versions;
# the application source is unchanged. The final image keeps Alpine because the Compose command
# needs `sh` to expand the database password.
FROM --platform=$BUILDPLATFORM golang:1-alpine@sha256:fa3d596898d9f126af7c01d14ee7597bab3f39cccf392ef36b69fe77cd681f18 AS build
ARG FAKECAS_COMMIT=9a9ddd73b22510b1d8a52519fd5014f50802d03f
ARG FAKECAS_SHA256=c67f8c57964763965477a692a0e00be2f159d1d0ce1c31972c7c2242dd392907
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
RUN set -eux; \
    wget -q -O /tmp/fakecas.tgz "https://codeload.github.com/CenterForOpenScience/fakecas/tar.gz/${FAKECAS_COMMIT}"; \
    echo "${FAKECAS_SHA256}  /tmp/fakecas.tgz" | sha256sum -c -; \
    tar -xzf /tmp/fakecas.tgz --strip-components=1; \
    go get golang.org/x/crypto@latest golang.org/x/net@latest golang.org/x/sys@latest golang.org/x/text@latest; \
    go mod tidy; \
    CGO_ENABLED=0 GOOS="$TARGETOS" GOARCH="$TARGETARCH" go build -trimpath -ldflags "-s -w -X main.Version=${FAKECAS_COMMIT}" -o /out/fakecas

FROM alpine:3@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf
LABEL org.opencontainers.image.base.name="alpine:3" \
      org.opencontainers.image.base.digest="sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf" \
      org.opencontainers.image.title="grdm-dev/fakecas" \
      org.opencontainers.image.description="FakeCAS built from a pinned upstream commit for the GakuNin RDM developer environment (ADR-07)"
COPY --from=build /out/fakecas /usr/local/bin/fakecas
USER 65534:65534
EXPOSE 8080
CMD ["fakecas"]
