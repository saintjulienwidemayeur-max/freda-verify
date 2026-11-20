# Plan: our own presentation-attack (PAD) model, with weights we own

Why: no free PAD model has a stated licence for its **weights** or a named training set (checked 2026-11-20, see CLAUDE.md "Liveness"). The MiniFASNet code is Apache-2.0, so we can train our own weights with it, on data we collected with consent. Then the licence question disappears and the model fits our population (Haiti / diaspora, dark skin, phone selfies, low light). This is a plan, not something already built or trained.

## What the open code gives us (read from the repos, 2026-11-20; not run)

- `facenox/face-antispoof-onnx` (same content as `johnraivenolazo/face-antispoof-onnx`): Apache-2.0, copyright "John Raiven Olazo", MiniFASNetV2-SE (~1.8 M parameters, 128x128 RGB input, 2 outputs Real/Spoof, Fourier-transform auxiliary branch used only in training), with `scripts/prepare_data.py`, `train.py`, `export_onnx.py`, `quantize_onnx.py`. Its README names **no training data**; the "70k+" is the size of the **CelebA-Spoof test set** it is evaluated on, so its published weights were very probably trained on CelebA-Spoof (non-commercial reputation, terms unverified). Its metrics are accuracy / ROC-AUC on that set, **not** APCER/BPCER, and not on any other dataset. Use the code, **never its weights, and never the Minivision weights as an initialisation** (same weights-licence problem).
- Original Minivision code (Apache-2.0) is the other source of the architecture and training scripts.
- Before copying any code into this repo: keep the Apache-2.0 licence text and the copyright notice, state what we changed (Apache-2.0 section 4), and have a lawyer glance at it.

## 1. Data (the real bottleneck)

Follow `docs/pad-collection-protocol.md` (consent, groups, capture through the real `/verify` page), scaled up:

| Set | Minimum to train something useful | Notes |
|---|---|---|
| Live (bona fide) captures | ~3,000 images from >= 150 people | 2 to 3 phones per person, >= 3 lighting conditions, dark and light skin, glasses, head coverings, several frames per capture (video frames are fine: 5 s clip = many frames) |
| Print attacks | ~3,000 | >= 2 printers, matte and glossy, several sizes, held flat and bent |
| Screen-replay attacks | ~3,000 | >= 2 phones and 1 laptop/tablet, varied brightness |
| Cut-outs, masks | as many as available | separate folders; evaluate separately |

Split **by person** (never by image): ~60 % train, 20 % development (choose the threshold), 20 % test (report once). Add the OULU-NPU idea: also hold out one phone and one lighting condition for a generalisation test. Synthetic AI faces can add identities to the attack side but are no substitute for real captures.

Do NOT mix in CelebA-Spoof, CASIA-SURF, OULU-NPU or any other dataset into training unless its licence explicitly allows commercial model training; evaluation-only use also needs the terms read first.

## 2. Training (when the data exists)

1. Prepare crops with the face detector we already use (YuNet) and a fixed crop scale; keep the same scale at inference (record it in `app/services/pad.py`).
2. Train MiniFASNetV2-SE from scratch (small model: CPU or one modest GPU is enough), with heavy augmentation (brightness, noise, blur, JPEG, small rotations, colour jitter) because the data set is small.
3. Pick the threshold on the DEVELOPMENT set at EER; report on the TEST set: BPCER, APCER per attack type (worst type is the headline), ACER, with 95 % intervals; per group (skin tone, lighting, phone) with `tools/pad_eval.py`.
4. Export ONNX; load it in `pad.py` through the existing plug-in path (`FV_PAD_MODEL_DIR`), keeping the model files out of git (download pinned by SHA-256, as for the other models).

## 3. Acceptance criteria before the score is shown to customers or used to route cases

Decide them BEFORE training, from the risk the business accepts. Suggested starting point: worst-attack APCER <= 5 % and BPCER <= 3 % on the test set, no skin-tone / lighting group with BPCER more than 2x the average, and a documented list of attacks NOT covered (masks, deepfakes, virtual camera). Until then it stays advisory and unlabelled as 'liveness'.

## 4. Risks and honest limits

- A small, self-collected set overfits: expect good numbers on people seen in similar conditions and worse elsewhere; the held-out person / phone / lighting tests exist to show this.
- A single-frame 2D model does not stop a deepfake injected through a virtual camera or a good 3D mask. That needs a different layer (device integrity, video-level checks, certified SDK).
- Collecting biometric data needs consent, retention and deletion rules (D9) and the storage must be encrypted.
- Certification (ISO/IEC 30107-3, e.g. iBeta) is a separate step with a lab; our own numbers are an engineering signal.

## 5. Order of work

1. Collect a first pilot (10 people, 2 phones, 3 lights, print + screen) and run `pad_eval` on the CURRENT model: the baseline we must beat.
2. Collect the full set (>= 150 people).
3. Train, evaluate on dev/test with the protocol above, write the aggregate results in CLAUDE.md.
4. Only if criteria are met, show the score to reviewers as a calibrated advisory; keep the human decision.
