"""Refuses document photos that obviously do NOT come from a camera: screenshots (PNG / WebP files; the hosted page always sends JPEG from the camera) and files whose metadata names an
image editor. HONEST LIMITS: this is a weak, bypassable heuristic. Anyone who calls the API directly can send a JPEG with no metadata; a photo of a screen showing an edited document
is still a camera photo; there is NO pixel-level tamper / forgery detection here. The real protection is that the hosted page takes documents from the live camera only. Returns a reason code or None."""
import re

EDITORS = re.compile(rb"photoshop|adobe|gimp|lightroom|canva|snapseed|picsart|pixlr|photopea|affinity|paint\.net|fotor|facetune|remini|meitu|ai-generated|midjourney|stable diffusion|dall-e", re.I)


def check(image: bytes, content_type: str) -> str | None:
    if content_type != "image/jpeg":
        return "not_camera_photo"                    # screenshots are normally PNG; edited exports are often PNG / WebP
    head = image[:65536]                             # EXIF / XMP live at the start of a JPEG
    if EDITORS.search(head):
        return "edited_image"
    return None
