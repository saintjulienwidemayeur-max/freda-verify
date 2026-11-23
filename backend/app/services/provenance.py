"""Refuses document photos that obviously do NOT come from a camera: screenshots (PNG / WebP files; the hosted page always sends JPEG from the camera) and files whose metadata names an
image editor. HONEST LIMITS: this is a weak, bypassable heuristic. Anyone who calls the API directly can send a JPEG with no metadata; a photo of a screen showing an edited document
is still a camera photo; there is NO pixel-level tamper / forgery detection here. The real protection is that the hosted page takes documents from the live camera only. Returns a reason code or None."""
import re

EDITORS = re.compile(rb"photoshop|lightroom|gimp|canva|snapseed|picsart|pixlr|photopea|affinity photo|paint\.net|fotor|facetune|remini|meitu|midjourney|stable diffusion|dall-e|firefly", re.I)


def _metadata_segments(jpeg: bytes):
    """Yields the EXIF / XMP application segments (APP1) of a JPEG: the only places an editor names itself. The bare word 'Adobe' is NOT used: an APP14 'Adobe' marker is written by ordinary encoders."""
    i, n = 2, len(jpeg)
    while i + 4 <= n and jpeg[i] == 0xFF:
        m = jpeg[i + 1]
        if m == 0xDA or m == 0xD9:                      # start of scan / end: no more metadata
            return
        ln = int.from_bytes(jpeg[i + 2:i + 4], "big")
        if m == 0xE1:
            yield jpeg[i + 4:i + 2 + ln]
        i += 2 + ln


def check(image: bytes, content_type: str) -> str | None:
    if content_type != "image/jpeg":
        return "not_camera_photo"                    # screenshots are normally PNG; edited exports are often PNG / WebP
    if image[:2] != b"\xff\xd8":
        return "not_camera_photo"
    for seg in _metadata_segments(image):
        if EDITORS.search(seg):
            return "edited_image"
    return None
