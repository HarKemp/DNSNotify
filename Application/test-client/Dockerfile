# Dockerfile.testclient
FROM alpine:latest

# Install dig and other DNS tools
RUN apk update && apk add --no-cache bind-tools

# Default command opens a shell
CMD ["/bin/sh"]