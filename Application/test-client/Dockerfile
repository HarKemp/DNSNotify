FROM alpine:latest

# Install dig and other DNS tools
RUN apk update && apk add --no-cache bind-tools coreutils

WORKDIR /app

COPY domains.txt .

# Default command opens a shell
CMD ["sh", "-c", \
     "echo 'Starting automatic dig from coredns'; \
      while true; do \
        DOMAIN_RAW=$(shuf -n 1 domains.txt); \
        DOMAIN=${DOMAIN_RAW%'\r'};\
        if [ -n \"$DOMAIN\" ]; then \
          echo \"Running dig @coredns $DOMAIN\"; \
          dig @coredns $DOMAIN; \
        else \
          echo \"Warning: No domain name in domains file\"; \
          sleep 5; \
        fi; \
        echo \"Sleeping for 30 seconds...\"; \
        sleep 30; \
      done"]