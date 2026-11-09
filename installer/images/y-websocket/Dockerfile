# syntax=docker/dockerfile:1
# y-websocket server without npm or yarn in the running image (manifest build_dockerfile, SPEC-01).
# The build context is the RDM-y-websocket-dev2027 checkout at the pinned commit; this recipe replaces
# the Dockerfile of that repository so the image can change without a new integration commit.
#
# Why: almost all of the image's findings were in the npm that node images bundle under
# /usr/local/lib/node_modules, which the server never uses at run time, and `npm install` also pulled
# the development dependencies. Node 24 is the current LTS line (node:25 was not).
ARG NODE_IMAGE=node:24-alpine@sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8

FROM ${NODE_IMAGE} AS deps
WORKDIR /home/node/app
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

FROM ${NODE_IMAGE}
RUN ["rm", "-rf", "/usr/local/lib/node_modules", "/usr/local/bin/npm", "/usr/local/bin/npx", "/usr/local/bin/corepack", "/usr/local/bin/yarn", "/usr/local/bin/yarnpkg", "/opt"]
WORKDIR /home/node/app
COPY --from=deps --chown=node:node /home/node/app/node_modules ./node_modules
COPY --chown=node:node . .
USER node
EXPOSE 1234
CMD ["node", "./bin/server.cjs"]
