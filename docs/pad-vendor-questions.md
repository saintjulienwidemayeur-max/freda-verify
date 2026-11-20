# Certified PAD vendors: shortlist and questions (to send by e-mail)

Status 2026-11-20: from web-search summaries only. NOTHING was verified on the vendors' own pages or on iBeta's site. Before any contract, open https://www.ibeta.com/iso-30107-3-presentation-attack-detection-confirmation-letters/ and read the actual letter for the exact product and version.

## Why a certified SDK

Our own experimental model refuses about 1 in 5 live people and has no measured attack-detection rate. A certified product has an independent test (iBeta, ISO/IEC 30107-3): Level 1 = simple attacks, Level 2 = harder attacks (e.g. masks). A letter covers one product VERSION on tested devices, not "all liveness from the vendor".

## Names that appeared (verify each)

Seen in iBeta confirmation letters (per search results): Paravision (Level 2, Liveness v1.2, Dec 2023), Veriff (Level 2, 2024; a service, not self-hosted), Jumio (Level 2, iOS SDK), idwall, GoTo Financial, Unissey (Level 2, 2022), Regula (Level 1 and 2, reported in 2026), Iris ID and Alibaba Cloud (Level 2, reported 2026), Zoloz and others at Level 1. Vendors that appear in comparisons as on-premise / SDK options: Paravision, FaceTec (on-prem capable, no public price), Regula, Shufti (on-prem offers for some African markets; its own pages disagree on the level, so confirm).

Faceplugin and KBY-AI market a 'Level 2 compliant' commercial SDK: we found no iBeta letter for them in the results, and the open-source Faceplugin model we tested refused ~50 % of live people. Treat their claim as unverified until they send the letter.

Prefer, in this order: (1) a product that runs ON OUR SERVERS (SDK / container), because identity photos must not leave our infrastructure without a DPA (decision D11); (2) a cloud API only with a DPA, a clear data-residency answer and no retention of our images.

## Questions to send (copy / paste)

1. Which iBeta PAD letter covers the exact product and version we would integrate? Please send the letter and the test report (Level 1 / Level 2, date, devices, attack types tested).
2. Which attacks are covered: printed photo, screen replay, 2D/3D mask, silicone mask, deepfake or virtual-camera injection? Is injection protection part of the certified scope or a separate module?
3. Passive (single image or short video) or active challenge? What does the user do? Typical capture time?
4. Where does it run: on our servers (SDK / container), on the device, or only in your cloud? Which operating systems and runtimes (Python / Node / Java / mobile / web)?
5. Where is data stored and processed (country)? Do you keep our images or templates? Retention, deletion, sub-processors. Do you sign a DPA? Do you transfer data outside Haiti / the US / EU?
6. Measured error rates (APCER / BPCER) on dark skin tones, on low-end Android phones and in low light. Can you share the demographic breakdown of the test set? Can we run our own pilot on our consented photos first?
7. Pricing: per verification, monthly minimum, annual licence for on-premise, volume tiers, test / sandbox, cost of the certified level vs the non-certified one.
8. Integration: web (browser) SDK, mobile SDKs, REST API, response format (score, decision, reasons), threshold control.
9. Support, SLA, update policy (is a new SDK version re-certified?), roadmap for deepfake / injection.
10. Can the licence be used by Freda Verify as a white-label feature for its own customers (resale), or only for our internal use?

## Our test offer (to run on every shortlisted product)

Same consented set for everyone (>= 100 people incl. many dark-skinned volunteers, 3+ phones, 3+ lights; print, screen replay, mask), measured with `python -m tools.pad_eval --protocol`: BPCER, worst-attack APCER, ACER, per group. Decide with numbers, not brochures.

## How it plugs in

`app/services/pad.py` is a pluggable provider (advisory score, never decides). A vendor SDK gets its own module with the same `score(image) -> PadOutcome` shape, enabled by an environment variable; never a mandatory dependency.
