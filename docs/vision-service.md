# Private Vision AI service (Qwen3-VL, self-hosted)

Status (2026-11-23): **code and tests exist; the model has NEVER been run by us** (the build sandbox has no GPU and cannot reach huggingface.co). Treat everything about speed, memory
and accuracy below as an estimate until it is measured on the real GPU host.

## What it is
`vision/` is a small internal FastAPI service. It sends a document photo to a **vLLM** server (OpenAI-compatible API) that runs **Qwen3-VL-4B-Instruct on our own GPU** and returns
strictly validated JSON: extracted text, document type, fields, local image-quality measurements, missing information, visible anomalies, model self-reported confidence.
It never returns a verdict (no `verified` / `authentic` / `decision` field exists). The main backend calls it only when `FV_VISION_URL` is set and only from a reviewer action
(`POST /api/v1/organizations/{org}/verifications/{id}/checks/vision`); the automatic decision does NOT use it.

## What it is NOT
Not OCR validation (Tesseract + PaddleOCR + ICAO check digits stay), not face matching, not liveness, not an authenticity check. A language model can misread digits and can
invent plausible text; its confidence is its own opinion. Text printed on a document can try to give it instructions: the prompt treats the image as data and the output schema refuses
anything unexpected, but that is a mitigation, not a guarantee.

## Server requirements (estimates, to be confirmed)
* NVIDIA GPU with ~16 GB VRAM recommended (the 4B model's bf16 weights are ~8-9 GB, plus vision encoder and KV cache); an RTX 4060 Ti 16 GB, L4 or A10 class card. Older cards without bf16 (T4)
  need `--dtype float16`. A smaller quantised build or a smaller model is the fallback if VRAM is lower.
* CPU-only is not practical for production (minutes per document) and is not supported by this compose file.
* NVIDIA Container Toolkit, Docker Compose v2, ~20 GB disk for the model cache, 8+ GB RAM.
* **The current production host (Render free web service: 512 MB RAM, no GPU) cannot run it.** Use a separate GPU machine reachable only over a private network / VPN.
* Licence: the Qwen3-VL model card is reported to state Apache-2.0; **we could not read it from the sandbox: verify the licence of the exact model you download before real customers.**

## Install
1. `cp infra/.env.example infra/.env` and set `FV_VISION_TOKEN` (>= 32 random characters: `python -c "import secrets;print(secrets.token_urlsafe(48))"`).
2. Download the weights once (needs internet only for this step): `docker compose -f infra/docker-compose.yml -f infra/docker-compose.vision.yml --profile init run --rm vllm-init`.
3. Start: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.vision.yml --env-file infra/.env up -d --build`; then set `FV_VISION_OFFLINE=1` so the model server never contacts the internet.
4. Check: `curl -s localhost:8100/health/ready` (503 `model_unavailable` until vLLM has loaded the model).
5. Pin the vLLM image tag and the model revision after the first successful test.

## API (internal, Bearer `FV_VISION_TOKEN`)
`POST /api/v1/vision/analyze` multipart: `image` (JPEG/PNG/WebP, <= 6 MB by default), `document_type` (`passport|id_card|driver_license|proof_of_address|other`), optional `instructions` (<= 300 chars).
Errors: 401 token, 413 too large, 422 bad image / type, 429 busy or rate limited, 502 model returned unusable JSON, 503 model unavailable, 504 timeout. `GET /health`, `GET /health/ready`.

## Security
Internal network only (`visionnet` is `internal: true`: no route to the internet; the model server publishes no port); shared-token auth (constant-time compare); the image is re-encoded
(EXIF stripped) and downscaled before inference; sizes, pixels, concurrency, queue, rate and timeouts are bounded; logs contain request id, size, status and timing, never content;
nothing is cached; results are stored by the backend like the other checks (Fernet-encrypted, deleted with the verification's data policy). The fake engine is refused in prod.

## Smaller / compressed models (no GPU): `infra/docker-compose.vision-cpu.yml`
The same Vision API talks to **llama.cpp** (`llama-server`, OpenAI-compatible) serving a **quantised GGUF** build of Qwen3-VL. Nothing else changes (same token, same schema, same backend endpoint).

| Choice | `FV_VISION_GGUF` | Notes (ESTIMATES, nothing measured by us) |
|---|---|---|
| Smallest | `Qwen/Qwen3-VL-2B-Instruct-GGUF:Q4_K_M` | about 2-3 GB of RAM with the vision projector; fastest; weakest reading |
| Better | `Qwen/Qwen3-VL-4B-Instruct-GGUF:Q4_K_M` | about 4-5 GB of RAM; roughly twice the time |
| GPU | `Qwen/Qwen3-VL-4B-Instruct` via vLLM (`docker-compose.vision.yml`) | fastest and best of the three |

* Expect **tens of seconds to minutes per document** on 2-4 CPU cores. That is acceptable only as a background / on-demand reviewer action, never inside the customer's upload request.
  The compose file lowers the image size (`FV_VISION_MAX_SIDE=896`), runs one request at a time and raises the timeouts for that reason.
* The first start must download the weights (`-hf` fetches the GGUF and its `mmproj`); the `llm` container is on the `default` network only for that. After the cache volume is filled,
  remove `default` from `llm` so it has no internet route.
* **Render:** the container can run as a Render *Private Service* (Docker image of `vision/` and of llama.cpp) but needs at least the **Standard plan (2 GB, $25/month)** for the 2B model and
  probably **Pro (4 GB, $85/month)** for comfort; the 512 MB plan cannot hold it. Render lists no GPU plans (check with Render support). A separate cheap GPU rental is faster per dollar.
* Compressed models read worse than the full one. Measure them against the existing PaddleOCR layout reader on lawful Haitian documents before trusting any field.
