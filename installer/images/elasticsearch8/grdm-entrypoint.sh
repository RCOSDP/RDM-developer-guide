#!/bin/sh
# Entrypoint of grdm-dev/elasticsearch8: prepare the writable config tmpfs and the TLS material, then run the
# official entrypoint. Runs as uid 1000 on a read-only root; writes only config/ (tmpfs), data/ and /es-ca.
set -eu

# Any other command (the one-shot setup script) runs as it is: it needs neither the config nor the TLS key.
case "${1:-}" in
  eswrapper|elasticsearch) ;;
  *) exec "$@" ;;
esac

ES_HOME=/usr/share/elasticsearch
TLS="$ES_HOME/data/tls"
CA_OUT=/es-ca

# config/ is an empty tmpfs: the keystore that holds the bootstrap password is created there at start.
cp -R "$ES_HOME/config.dist/." "$ES_HOME/config/"  # no -a: the tmpfs root belongs to root, so its times cannot be set

mkdir -p "$TLS"
if [ ! -s "$TLS/server.crt" ] || [ ! -s "$TLS/server.key" ] || [ ! -s "$TLS/ca.crt" ]; then
  work=$(mktemp -d)
  # A CA of its own and a server certificate for the names clients use inside the network; the CA key is
  # thrown away, so nothing can mint another certificate for it. Valid about 27 years like the mongo one was.
  openssl req -x509 -newkey rsa:3072 -nodes -days 9999 -subj "/C=JP/O=GRDM dev/CN=grdm-dev elasticsearch8 CA" \
    -keyout "$work/ca.key" -out "$work/ca.crt" -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
  openssl req -newkey rsa:3072 -nodes -subj "/C=JP/O=GRDM dev/CN=elasticsearch8" \
    -keyout "$work/server.pkcs1.key" -out "$work/server.csr" 2>/dev/null
  printf 'subjectAltName=DNS:elasticsearch8,DNS:localhost,IP:127.0.0.1\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' > "$work/ext.cnf"
  openssl x509 -req -in "$work/server.csr" -CA "$work/ca.crt" -CAkey "$work/ca.key" -CAcreateserial \
    -days 9999 -extfile "$work/ext.cnf" -out "$work/server.crt" 2>/dev/null
  openssl pkcs8 -topk8 -nocrypt -in "$work/server.pkcs1.key" -out "$work/server.key"
  # Replace one file at a time, key last: a start interrupted here is repaired by the next one.
  cp "$work/ca.crt" "$TLS/ca.crt"
  cp "$work/server.crt" "$TLS/server.crt"
  cp "$work/server.key" "$TLS/server.key"
  chmod 0600 "$TLS/server.key"
  rm -rf "$work"
fi

# Elasticsearch 8.19 refuses SSL files outside config/ (entitlements), and config/ is a tmpfs: copy them in.
mkdir -p "$ES_HOME/config/tls"
cp "$TLS/ca.crt" "$TLS/server.crt" "$TLS/server.key" "$ES_HOME/config/tls/"
chmod 0600 "$ES_HOME/config/tls/server.key"

# The public CA certificate is what osf.io (and the setup step) trust.
if [ -d "$CA_OUT" ]; then
  cp "$TLS/ca.crt" "$CA_OUT/ca.crt"
  chmod 0644 "$CA_OUT/ca.crt"
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
