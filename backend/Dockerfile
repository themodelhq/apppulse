FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form so $PORT expands - Render injects PORT at runtime and expects
# the service to bind to it. Defaults to 8000 for local `docker run`.
# No --reload here (that's a dev-only convenience, enabled instead via the
# docker-compose.yml override for local development).
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
