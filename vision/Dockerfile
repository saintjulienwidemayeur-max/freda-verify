# Freda Verify Vision API: small CPU image (FastAPI + OpenCV). The MODEL itself runs in the separate `vllm` container (GPU), see infra/docker-compose.vision.yml.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt && useradd --system --uid 10002 --no-create-home app
COPY app ./app
USER app
EXPOSE 8100
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8100/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
