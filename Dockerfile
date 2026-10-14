FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    SHELFMITRA_DB=/var/data/shop.db TEMPORAL_ADDRESS=localhost:7233

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Temporal CLI: runs the Temporal dev server inside the container, backed by SQLite on the persistent disk.
RUN curl -sSfL "https://temporal.download/cli/archive/latest?platform=linux&arch=amd64" -o /tmp/t.tgz \
    && tar -xzf /tmp/t.tgz -C /usr/local/bin temporal && rm /tmp/t.tgz

WORKDIR /app
COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt

COPY shelfmitra ./shelfmitra
COPY web ./web
COPY data/raw ./data/raw
COPY scripts/start_render.sh ./start.sh
RUN chmod +x start.sh

EXPOSE 10000
CMD ["./start.sh"]
