# Protocol: collecting and measuring a presentation-attack (PAD) test set

Goal: replace the unknowns in `CLAUDE.md` ("Liveness") with numbers. Everything here is for **measuring** the experimental MiniFASNet check, not for certifying it. This is not legal advice: have the consent text reviewed (D9).

## 1. Consent and privacy (before the first photo)

Every volunteer signs (or records a clear yes to) a short consent that says, in their language (Kreyòl / Français / English):

- who collects the photos (Freda Verify), why (testing whether the system can tell a live face from a photo, screen or mask), and that the result may be used to improve it;
- which images are taken (their face, live and "attack" versions of it), how long they are kept (state a date), who can see them, and that they can ask for deletion at any time;
- that nothing is shared with third parties and no image is sent to an outside AI service (decision D11);
- optional labels they agree to give for group results: skin tone (self-described, or Fitzpatrick I-VI), lighting, phone model. These are optional and can be refused.

Rules: no minors; keep a list `consent.csv` (code, date, language, labels) **separate** from the photos; give each person a code (`p001`…), never a name in a file name; store the set encrypted, never in git; delete when the retention date arrives.

## 2. Who and how many

| Set | Minimum for a first picture | To state a reasonably tight bound |
|---|---|---|
| Genuine people | 30 | ≥ 100, covering skin tones (include many darker-skinned volunteers: the target population is Haiti / diaspora), ages, glasses, beards, head coverings |
| Attacks per type | 50 captures | ≥ 100, made with ≥ 10 different volunteers |

With fewer than ~100 genuine / 50 per attack, `pad_eval` prints "INDICATIVE only": do not quote the numbers as a claim.

## 3. What to capture (folder layout `pad_set/`)

Capture exactly as a customer would: through the real hosted page `/verify` (so the same camera, resolution and JPEG compression), then export the selfie frames from the dashboard review panel (owner/admin) or take a screenshot of the review image. Capturing with a different app gives numbers that do not apply.

```
pad_set/
  genuine/<group>/…            live captures. Groups, e.g. dark_skin, light_skin, low_light, backlight, outdoor_sun, glasses, phone_android_low_end, phone_iphone
  attack_print/<group>/…       a PRINTED photo of the volunteer: laser and inkjet, matte and glossy, A5 and A4, held flat and slightly bent
  attack_replay/<group>/…      the volunteer's photo or video shown on a phone screen, a tablet and a laptop (vary brightness; with and without a screen protector)
  attack_cutout/<group>/…      printed photo with the eyes cut out and a real person behind it
  attack_mask/<group>/…        paper/3D-printed/silicone/latex mask of the volunteer (only if available; separate folder per material)
```

Rules: one capture = one file; for each attack type use the volunteer's real face, not a stock photo; record the lighting and phone in the group folder name; never mix a group's files from different people into the genuine set.

## 4. Measuring

```bash
cd backend
FV_PAD_MODEL_DIR=/opt/pad-models python -m tools.pad_eval /path/to/pad_set --thresholds 0.3,0.5,0.7,0.9 --stress
```

It prints BPCER (live people refused), APCER per attack type with 95 % Wilson intervals, per-group results (skin tone, lighting, phone) and, with `--stress`, a synthetic sensitivity probe (darkening, noise, blur, compression). **Read the per-group lines first**: an average can hide a group that fails (typical failure: dark skin in low light is refused or accepted at a different rate).

Decision rules before the check is ever shown to customers or used to route cases:

1. Pick the threshold from the data (not from the 0.7 / 0.3 defaults) for an acceptable BPCER per group.
2. Report the worst attack type's APCER, not the average. If any type is above your risk limit, the check must not be described as protection against that attack.
3. If a skin-tone or lighting group has a clearly worse BPCER, fix or document it before launch.

## 5. What photos cannot test (do these separately)

- **Virtual camera / injection** (OBS virtual camera, emulator, a video file as the camera) and **deepfakes** (face-swap or reenactment video): they are attacks on the video *pipeline*, not on a still. Test them by running the hosted page against a virtual camera feeding (a) a pre-recorded video of the person and (b) a deepfake, with the head-turn challenge on. Record whether the page, the selfie frames and the PAD check accept it. Expected today: the browser challenge can be defeated by a good replay or deepfake and the single-image PAD does not look at video at all.
- **Masks and 3D attacks**: need the physical materials; add them to `attack_mask/` as they become available.
- **Independent evaluation**: only an accredited lab (ISO/IEC 30107-3, e.g. iBeta) gives a certified result. Our own numbers are an engineering signal, not a certificate.

## 6. After the run

Record only aggregates in `CLAUDE.md` (no images, no codes), then delete the set. Keep the threshold decision, the per-group table and the date.
