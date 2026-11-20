FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_THREAD_LIMIT=1
WORKDIR /srv
# Tesseract (Apache-2.0) reads the MRZ from uploaded photos
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr curl ca-certificates && rm -rf /var/lib/apt/lists/*
# OCR-B model for Tesseract (github.com/Shreeshrii/tessdata_ocrb, Apache-2.0, trained on OCR-B fonts: far more accurate on MRZ than the generic English model); pinned by SHA-256
RUN d="$(dirname "$(find /usr/share/tesseract-ocr -name eng.traineddata | head -1)")" \
 && curl -fsSL -o "$d/ocrb.traineddata" https://raw.githubusercontent.com/Shreeshrii/tessdata_ocrb/master/ocrb.traineddata \
 && echo "f4631039e140e674518e8adb39b41751ef62e6338686d5fff6c1c707e591b829  $d/ocrb.traineddata" | sha256sum -c -
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
