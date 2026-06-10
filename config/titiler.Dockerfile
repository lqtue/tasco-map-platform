FROM ghcr.io/developmentseed/titiler:0.18.5

ENV PORT=8080
ENV WORKERS_PER_CORE=1
ENV TITILER_API_CORS_ORIGINS="*"

# R2/S3 access — set via docker-compose environment
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL

EXPOSE 8080
