FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
# Tesseract (Apache-2.0) reads the MRZ from uploaded photos
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd --system --uid 10001 --no-create-home app
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .
USER app
EXPOSE 8000
# the entrypoint applies the migrations (tables are created automatically) and then starts the API
CMD ["./docker-entrypoint.sh"]
