import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str = os.environ.get("FV_VISION_TOKEN", "")                          # shared secret between the Freda backend and this service
    env: str = os.environ.get("FV_VISION_ENV", "dev")
    engine: str = os.environ.get("FV_VISION_ENGINE", "openai")                  # openai (vLLM / any OpenAI-compatible server on OUR network) | fake (tests, dev)
    llm_url: str = os.environ.get("FV_VISION_LLM_URL", "http://vllm:8000")
    llm_model: str = os.environ.get("FV_VISION_MODEL", "Qwen/Qwen3-VL-4B-Instruct")
    max_upload_bytes: int = int(os.environ.get("FV_VISION_MAX_BYTES", str(6 * 1024 * 1024)))
    max_pixels: int = int(os.environ.get("FV_VISION_MAX_PIXELS", str(40_000_000)))
    max_side: int = int(os.environ.get("FV_VISION_MAX_SIDE", "1344"))             # image is downscaled before inference (latency / VRAM)
    timeout_s: float = float(os.environ.get("FV_VISION_TIMEOUT_S", "120"))
    max_concurrent: int = int(os.environ.get("FV_VISION_CONCURRENCY", "2"))      # simultaneous inferences
    max_queued: int = int(os.environ.get("FV_VISION_QUEUE", "8"))                # waiting requests before a 429
    rate_per_minute: int = int(os.environ.get("FV_VISION_RATE_PER_MIN", "60"))


def get_settings() -> Settings:
    return Settings()
