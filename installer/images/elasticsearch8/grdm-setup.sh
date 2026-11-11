#!/bin/sh
# One-shot of grdm-dev/elasticsearch8: wait for the cluster, then create the role and the user osf.io searches
# with (idempotent PUTs, run at every `up`). osf.io never gets the elastic superuser: the role may monitor the
# cluster and do anything on the website* and private__website* indices, nothing else (ADR-14).
# Needs ELASTIC_PASSWORD (bootstrap superuser) and OSF_ES_PASSWORD (the password to give grdm_osf).
set -eu

URL="${ES_URL:-https://elasticsearch8:9200}"
CA="${ES_CA:-/es-ca/ca.crt}"
: "${ELASTIC_PASSWORD:?}" "${OSF_ES_PASSWORD:?}"

# The credentials go through curl's config on stdin, not the command line.
es() {
  method=$1; path=$2; body=${3:-}
  if [ -n "$body" ]; then
    printf 'user = "elastic:%s"\n' "$ELASTIC_PASSWORD" | curl -fsS -K - --cacert "$CA" -X "$method" "$URL$path" -H 'Content-Type: application/json' -d "$body"
  else
    printf 'user = "elastic:%s"\n' "$ELASTIC_PASSWORD" | curl -fsS -K - --cacert "$CA" -X "$method" "$URL$path"
  fi
}

n=0
until es GET '/_cluster/health?wait_for_status=yellow&timeout=30s' >/dev/null 2>&1; do
  n=$((n + 1))
  if [ "$n" -ge 120 ]; then echo "elasticsearch8_setup: the cluster did not become ready in 10 minutes" >&2; exit 1; fi
  sleep 5
done

es PUT /_security/role/grdm_osf '{"cluster":["monitor"],"indices":[{"names":["website*","private__website*"],"privileges":["all"]}]}' >/dev/null
# The password is JSON-escaped by printf %s of a value that secrets init limits to URL-safe characters.
es PUT /_security/user/grdm_osf "{\"password\":\"$OSF_ES_PASSWORD\",\"roles\":[\"grdm_osf\"],\"full_name\":\"osf.io search (grdm-dev)\"}" >/dev/null
echo "elasticsearch8_setup: done"
