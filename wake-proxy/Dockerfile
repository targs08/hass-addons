ARG BUILD_FROM
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

SHELL ["/bin/sh", "-o", "pipefail", "-c"]

# hadolint ignore=DL3018
RUN apk add --no-cache python3

COPY rootfs /

# Fail the build rather than the add-on if the proxy does not even parse.
RUN python3 -m compileall -q /usr/bin/wake_proxy.py /usr/bin/wake-proxy-health

# The add-on has no watchdog option: Supervisor reads this instead.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD ["/usr/bin/wake-proxy-health"]

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/wake-proxy/DOCS.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}
