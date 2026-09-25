FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-bookworm-slim
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
  && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
COPY apps/api/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /srv
COPY apps/api/app /srv/api/app
COPY --from=web /app/.next/standalone /srv/web
COPY --from=web /app/.next/static /srv/web/.next/static
COPY --from=web /app/public /srv/web/public
COPY start.sh /srv/start.sh
RUN chmod +x /srv/start.sh
ENV API_PROXY_URL=http://127.0.0.1:8000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV PYTHONPATH=/srv/api
EXPOSE 3000
CMD ["/srv/start.sh"]
