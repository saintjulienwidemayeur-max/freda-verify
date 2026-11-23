"""Server-side legibility gate for ID-card / licence photos (front and back): refuses a photo that is too dark, too blurry or in which no printed text can be found, so the customer is
asked to retake it in a bright place instead of the system deciding on an unreadable image. Deliberately conservative (a refusal of a good photo is worse than accepting a mediocre one);
thresholds are first guesses, NOT tuned on real phone photos. Returns a reason code or None."""
from app.services import paddle

DARK_MEAN = 40          # mean luminance 0-255
BLUR_VAR = 12.0         # variance of the Laplacian on the image scaled to 1000 px
MIN_TEXT_CHARS = 8      # alphanumeric characters found by the OCR on a card photo


def check(image: bytes, need_text: bool = True) -> str | None:
    try:
        import cv2
        import numpy as np
        a = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_GRAYSCALE)
        if a is None:
            return None
        k = 1000 / max(a.shape[:2])
        if k < 1:
            a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        if float(a.mean()) < DARK_MEAN:
            return "dark"
        if float(cv2.Laplacian(a, cv2.CV_64F).var()) < BLUR_VAR:
            return "blurry"
    except Exception:  # noqa: BLE001  a failing check must never block a customer
        return None
    if need_text and paddle.available():
        n = paddle.count_text_fast(image)                           # downscaled, no angle classifier: a few times faster than a full reading
        if n is not None and n < MIN_TEXT_CHARS:
            return "no_text"
    return None
