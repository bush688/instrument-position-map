FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .

ENV DATA_DIR=/data
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# 2 workers; increase for heavier load
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "api:app"]
