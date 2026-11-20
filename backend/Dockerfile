FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_THREAD_LIMIT=1
WORKDIR /srv
# Tesseract (Apache-2.0) reads the MRZ from uploaded photos
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr curl ca-certificates && rm -rf /var/lib/apt/lists/*
# OCR-B model for Tesseract (github.com/Shreeshrii/tessdata_ocrb, Apache-2.0, trained on OCR-B fonts: far more accurate on MRZ than the generic English model); pinned by SHA-256
RUN d="$(dirname "$(find /usr/share/tesseract-ocr -name eng.traineddata | head -1)")" \
 && curl -fsSL -o "$d/ocrb.traineddata" https://raw.githubusercontent.com/Shreeshrii/tessdata_ocrb/master/ocrb.traineddata \
 && echo "f4631039e140e674518e8adb39b41751ef62e6338686d5fff6c1c707e591b829  $d/ocrb.traineddata" | sha256sum -c -
# Face comparison models (OpenCV Zoo; YuNet MIT, SFace Apache-2.0), pinned by SHA-256. Advisory use only (see app/services/face.py)
RUN mkdir -p /opt/face-models \
 && curl -fsSL -o /opt/face-models/face_detection_yunet_2023mar.onnx https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx \
 && curl -fsSL -o /opt/face-models/face_recognition_sface_2021dec.onnx https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx \
 && echo "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4  /opt/face-models/face_detection_yunet_2023mar.onnx" | sha256sum -c - \
 && echo "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79  /opt/face-models/face_recognition_sface_2021dec.onnx" | sha256sum -c -
# Experimental presentation-attack models (Minivision MiniFASNet, ONNX conversions by yakhyo). Code is Apache-2.0; the licence/training data of the WEIGHTS is not stated by the
# publishers (CLAUDE.md, D7). Set --build-arg INSTALL_PAD=0 to leave them out: the feature then reports `unavailable`. Pinned by SHA-256.
ARG INSTALL_PAD=1
RUN if [ "$INSTALL_PAD" = "1" ]; then mkdir -p /opt/pad-models \
 && curl -fsSL -o /opt/pad-models/MiniFASNetV2.onnx https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx \
 && curl -fsSL -o /opt/pad-models/MiniFASNetV1SE.onnx https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV1SE.onnx \
 && echo "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907  /opt/pad-models/MiniFASNetV2.onnx" | sha256sum -c - \
 && echo "ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676  /opt/pad-models/MiniFASNetV1SE.onnx" | sha256sum -c -; fi
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
