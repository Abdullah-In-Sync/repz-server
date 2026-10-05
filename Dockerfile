FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY exercises.json ./
COPY scripts/start_api.sh ./scripts/start_api.sh

RUN pip install --no-cache-dir . \
    && mkdir -p /data/media/gifs \
    && chmod +x ./scripts/start_api.sh

ENV MEDIA_ROOT=/data/media
ENV PORT=8000
ENV WEB_CONCURRENCY=1
EXPOSE 8000

CMD ["./scripts/start_api.sh"]
