"""Image upload helpers: the declared type must match the real bytes; SVG and anything else is refused; the body is read with a hard size cap."""
from fastapi import Request

from app.core.errors import AppError

_SIG = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}


def sniff_ok(ctype: str, data: bytes) -> bool:
    if ctype == "image/webp":
        return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    sig = _SIG.get(ctype)
    return bool(sig) and data.startswith(sig) and len(data) > 32


async def read_limited(request: Request, limit: int) -> bytes:
    """Never buffers more than `limit` bytes, whatever Content-Length claims."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise AppError(413, "file_too_large", f"The file must be {limit // 1024} KB or smaller")
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > limit:
            raise AppError(413, "file_too_large", f"The file must be {limit // 1024} KB or smaller")
    return bytes(buf)


def sniff_video(ctype: str, data: bytes) -> bool:
    """WebM (EBML header) or MP4/MOV ('ftyp' box). The declared type must match the bytes; anything else is refused."""
    if len(data) < 1024:
        return False
    if ctype == "video/webm":
        return data[:4] == b"\x1a\x45\xdf\xa3"
    if ctype == "video/mp4":
        return data[4:8] == b"ftyp"
    return False
