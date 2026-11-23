"""Image validation and local quality measurement. Nothing here is sent anywhere."""
import io

import cv2
import numpy as np
from PIL import Image

from .schema import ImageQuality

Image.MAX_IMAGE_PIXELS = None            # checked by hand against settings.max_pixels (decompression-bomb guard)


class ImageError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sniff(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def load(data: bytes, max_pixels: int) -> Image.Image:
    kind = sniff(data)
    if kind is None:
        raise ImageError("unsupported_image", "Use a JPEG, PNG or WebP image")
    try:
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w * h > max_pixels or w < 64 or h < 64:
            raise ImageError("bad_image_size", "Image size is not acceptable")
        img.load()
        return img.convert("RGB")
    except ImageError:
        raise
    except Exception as e:  # noqa: BLE001  corrupt / truncated / bomb
        raise ImageError("invalid_image", "The image cannot be read") from e


def prepare(img: Image.Image, max_side: int) -> bytes:
    """Downscale (never upscale) and re-encode as JPEG: strips metadata (EXIF) and bounds the work of the model."""
    k = max_side / max(img.size)
    if k < 1:
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def quality(img: Image.Image) -> ImageQuality:
    a = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY)
    k = 1000 / max(a.shape[:2])
    if k < 1:
        a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    sharp = float(cv2.Laplacian(a, cv2.CV_64F).var())
    mean = float(a.mean())
    glare = float((a > 250).mean())
    issues = []
    if mean < 40:
        issues.append("too_dark")
    if mean > 235 or glare > 0.12:
        issues.append("overexposed_or_glare")
    if sharp < 12:
        issues.append("blurry")
    if min(img.size) < 400:
        issues.append("low_resolution")
    return ImageQuality(width=img.width, height=img.height, sharpness=round(sharp, 1), mean_brightness=round(mean, 1), glare_ratio=round(glare, 4),
                        usable=not {"too_dark", "blurry"} & set(issues), issues=issues)
