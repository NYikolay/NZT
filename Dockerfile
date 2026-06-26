# Builder image / dev mode
FROM python:3.12-slim AS local

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

CMD ["fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]
# ---------------------------------------------------------------------------