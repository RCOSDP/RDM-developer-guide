# syntax=docker/dockerfile:1
# ShareJS 0.7 on current Node, without npm or yarn in the running image (ADR-07).
#
# Why: quay.io/centerforopenscience/sharejs:develop is Debian 8 with Node 0.12. mongodb 1.4 (under
# livedb-mongo and mongoskin) never calls back on the TLS stack of Node 22/24, so vendor/mongoskin
# puts the part of the mongoskin API that livedb-mongo uses on top of mongodb 3.7. ws 8 replaces ws
# 0.4; index.js.patch is the only change to the upstream server. Scripts are off (--ignore-scripts),
# so nothing is compiled and no install step runs code from the dependency tree.
ARG NODE_IMAGE=node:24-alpine@sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8
ARG SHAREJS_COMMIT=7d4731ce03f62e76e61483e00fa32b4dc563e6d0
ARG SHAREJS_SHA256=e9a1219d8a99c2a4eda8bacd318deb0fc500a166883adcb3dac34ca83818d2b5

FROM ${NODE_IMAGE} AS deps
ARG SHAREJS_COMMIT
ARG SHAREJS_SHA256
WORKDIR /home/node/app
COPY package.json index.js.patch ./
COPY vendor ./vendor
RUN set -eux; \
    apk add --no-cache patch; \
    wget -q -O /tmp/sharejs.tgz "https://codeload.github.com/CenterForOpenScience/sharejs/tar.gz/${SHAREJS_COMMIT}"; \
    echo "${SHAREJS_SHA256}  /tmp/sharejs.tgz" | sha256sum -c -; \
    tar -xzf /tmp/sharejs.tgz --strip-components=1 "sharejs-${SHAREJS_COMMIT}/index.js"; \
    patch -p1 < index.js.patch; \
    npm install --omit=dev --omit=optional --ignore-scripts --install-links --no-audit --no-fund; \
    rm -rf vendor index.js.patch package-lock.json

FROM ${NODE_IMAGE}
LABEL org.opencontainers.image.base.name="node:24-alpine" \
      org.opencontainers.image.base.digest="sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8"
RUN ["rm", "-rf", "/usr/local/lib/node_modules", "/usr/local/bin/npm", "/usr/local/bin/npx", "/usr/local/bin/corepack", "/usr/local/bin/yarn", "/usr/local/bin/yarnpkg", "/opt"]
WORKDIR /home/node/app
COPY --from=deps --chown=node:node /home/node/app ./
USER node
EXPOSE 7007
CMD ["node", "./index.js"]
