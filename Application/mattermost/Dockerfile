# Dockerfile.arm64
FROM debian:12-slim

ARG MM_VER=10.5.2

ENV MM_PLUGINSETTINGS_ENABLE=false

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates gosu; \
    curl -L -o /tmp/mm.tar.gz \
      "https://releases.mattermost.com/${MM_VER}/mattermost-${MM_VER}-linux-arm64.tar.gz"; \
    mkdir -p /mattermost; \
    tar -xzf /tmp/mm.tar.gz --strip-components=1 -C /mattermost; \
    rm -rf /tmp/mm.tar.gz /var/lib/apt/lists/*

RUN useradd --system --uid 2000 mattermost && \
    chown -R mattermost:mattermost /mattermost

COPY mattermost-setup.sh /opt/mattermost/mattermost-setup.sh
RUN chmod +x /opt/mattermost/mattermost-setup.sh

COPY docker-entry.sh /docker-entry.sh
RUN chmod +x /docker-entry.sh

WORKDIR /mattermost

EXPOSE 8065
ENTRYPOINT ["/docker-entry.sh"]
