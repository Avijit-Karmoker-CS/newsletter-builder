#!/bin/sh
set -e
mkdir -p /data/uploads
export DATABASE_URL="${DATABASE_URL:-sqlite:////data/newsletter_builder.db}"
export UPLOAD_DIR="${UPLOAD_DIR:-/data/uploads}"
export PYTHONPATH=/srv/api
/opt/venv/bin/uvicorn app.main:app --app-dir /srv/api --host 127.0.0.1 --port 8000 &
cd /srv/web
export API_PROXY_URL=http://127.0.0.1:8000
export PORT=3000
export HOSTNAME=0.0.0.0
exec node server.js
