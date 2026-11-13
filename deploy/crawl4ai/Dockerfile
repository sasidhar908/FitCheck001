# Official Crawl4AI Google Cloud Run Deployment Dockerfile
# Source Repository: https://github.com/unclecode/crawl4ai.git
# Documentation: https://docs.crawl4ai.com/core/docker-deployment/

FROM unclecode/crawl4ai:latest

# Cloud Run injects PORT (default 11235 for Crawl4AI REST server)
ENV PORT=11235
ENV PYTHONUNBUFFERED=1
ENV CRAWL4AI_API_TOKEN=""

# Copy production Crawl4AI server configuration
COPY config.yml /app/config.yml

EXPOSE 11235

# Healthcheck against Crawl4AI's built-in /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1
