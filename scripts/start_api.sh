#!/bin/sh
set -eu
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT:-8000}" \
  -w "${WEB_CONCURRENCY:-1}" \
  --timeout 120
