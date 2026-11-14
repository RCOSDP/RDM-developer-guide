#!/usr/bin/env bash
# Smoke test of the grdm-dev/elasticsearch8 image (images.yml, ADR-14): start it the way the Compose template does
# (read-only root, no capabilities, config on a tmpfs, named volumes for data and the CA) and check that
#   1. HTTPS answers and an anonymous request is refused with 401 (authentication is on),
#   2. the server certificate verifies against the CA the container publishes in /es-ca,
#   3. the superuser sees a yellow or green cluster, the node, and the two analysis plugins.
# On any failure the container's last log lines are printed (with the password masked); the container and both
# volumes are always removed.
#
#   bash .github/scripts/smoke-elasticsearch8.sh <image>
set -euo pipefail

image=$1
name=grdm-smoke-es8
vol_data=grdm-smoke-es8-data
vol_ca=grdm-smoke-es8-ca
port=${SMOKE_PORT:-19200}
base="https://127.0.0.1:${port}"
# An ephemeral credential for this one container: it lives only in the container's configuration and keystore
# while the test runs, and is never committed, uploaded or printed.
pw=$(openssl rand -hex 16)
work=$(mktemp -d)

cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "== elasticsearch8 smoke failed (exit $rc); last container log lines:"
    docker logs --tail 100 "$name" 2>&1 | sed "s/${pw}/[redacted]/g" || true
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$vol_data" >/dev/null 2>&1 || true
  docker volume rm "$vol_ca" >/dev/null 2>&1 || true
  rm -rf "$work"
  exit "$rc"
}
trap cleanup EXIT

fail() { echo "elasticsearch8 smoke: $*" >&2; exit 1; }

docker run -d --name "$name" --read-only \
  --tmpfs /tmp --tmpfs /usr/share/elasticsearch/logs:mode=1777 --tmpfs /usr/share/elasticsearch/config:mode=1777 \
  -v "$vol_data:/usr/share/elasticsearch/data" -v "$vol_ca:/es-ca" \
  -e ES_JAVA_OPTS="-Xms512m -Xmx512m" -e ELASTIC_PASSWORD="$pw" \
  --cap-drop ALL --security-opt no-new-privileges:true -p "127.0.0.1:${port}:9200" "$image" >/dev/null

# 1. HTTPS answers; anonymous gets exactly 401 (a 200 means authentication is off, which fails the test)
status=000
for _ in $(seq 1 60); do
  sleep 5
  status=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$base/" || true)
  case "$status" in 401|200) break ;; esac
  [ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" = true ] || fail "the container stopped before answering"
done
[ "$status" = 401 ] || fail "an anonymous request got HTTP $status after the wait; expected 401"

# 2. the certificate verifies against the published CA (from here on, no -k)
docker cp "$name:/es-ca/ca.crt" "$work/ca.crt" >/dev/null || fail "no CA certificate in /es-ca"
auth() { curl -sS --fail --max-time 20 --cacert "$work/ca.crt" --user "elastic:${pw}" "$base$1"; }

# 3. the superuser: cluster health (the 401 can come before the node is fully up), node, plugins
health=""
for _ in $(seq 1 24); do
  if health=$(auth "/_cluster/health?wait_for_status=yellow&timeout=5s" 2>&1); then break; fi
  sleep 5
done
grep -Eq '"status":"(green|yellow)"' <<<"$health" || fail "cluster health not yellow or green: ${health:0:300}"
root=$(auth /) || fail "authenticated GET / failed"
grep -q '"cluster_name"' <<<"$root" || fail "GET / has no cluster_name: ${root:0:300}"
plugins=$(auth /_cat/plugins) || fail "authenticated GET /_cat/plugins failed"
for p in analysis-kuromoji analysis-icu; do
  grep -q "$p" <<<"$plugins" || fail "plugin $p is missing: ${plugins:0:300}"
done
echo "elasticsearch8 smoke: anonymous 401, certificate verified against /es-ca, cluster healthy, kuromoji and icu present"
