# syntax=docker/dockerfile:1
# Document converter for MFR: LibreOffice on current Debian behind a small HTTP service (ADR-07).
#
# Why: centerforopenscience/unoconv is Debian 10 with LibreOffice 6.1, linux/amd64 only, and runs as
# root. MFR's LibreOffice 6.1 UNO client cannot talk to a newer listener ("Binary URP bridge disposed
# during call"), so MFR now posts the document here over HTTP (RDM-modular-file-renderer-dev2027,
# fix/unoconv-client-compat, UNOCONV_CONVERT_URL) and no UNO bridge crosses a version boundary.
# The service only runs `soffice --convert-to` with a fresh profile per request after a bearer check,
# so the wb_tmp volume is no longer shared with this container: runs as uid 1000 with a read-only root
# and a tmpfs /tmp. CONVERT_SECRET is required; the service refuses to start without it.
# libreoffice-nogui without recommends leaves out X11, Java and the desktop integration.
FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2
LABEL org.opencontainers.image.base.name="debian:trixie-slim" \
      org.opencontainers.image.base.digest="sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2" \
      org.opencontainers.image.title="grdm-dev/unoconv" \
      org.opencontainers.image.description="LibreOffice convert-to service for the GakuNin RDM developer environment (ADR-07)"
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libreoffice-nogui \
        python3-minimal \
        tini \
        libpython3-stdlib \
        fonts-ipafont-gothic fonts-ipafont-mincho \
        fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea fonts-dejavu-core; \
    apt-get dist-upgrade -y; \
    rm -rf /var/lib/apt/lists/*; \
    useradd --uid 1000 --home-dir /tmp --no-create-home --shell /usr/sbin/nologin converter
COPY convert_service.py registrymodifications.xcu /opt/convert/
ENV HOME=/tmp
USER 1000:1000
EXPOSE 2002
# tini is PID 1 because LibreOffice leaves gpgconf and gpg children behind; the service must not
# accumulate zombies up to the pids limit (measured: 15 zombies after 9 conversions without it).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-I", "/opt/convert/convert_service.py"]
