"""
Shrink an admin-uploaded logo to what the pages will show.

A logo is served to every visitor on every model card, so its stored size is
what matters, not what the admin picked. Rasters are resized into a box and
re-encoded as WebP. SVGs scale on their own and stay as they are, within a
size cap and a cheap scripting check.
"""

import re
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from backend.config import LOGO_SVG_MAX_SIZE, LOGO_UPLOAD_MAX_SIZE
from backend.errors import LogoRejectedError

LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}

# Scripts and inline handlers. The logo route answers with a sandbox CSP that
# stops scripting anyway; this only keeps the obvious cases out of the database.
_SVG_SCRIPTING = re.compile(rb"<script|\bon[a-z]+\s*=", re.IGNORECASE)


def normalize_logo(
    content: bytes, content_type: str, box: tuple[int, int]
) -> tuple[bytes, str]:
    """The bytes to store and their content type, or a 400 for the admin."""
    if content_type not in LOGO_CONTENT_TYPES:
        raise LogoRejectedError("logo_unsupported_type")
    if len(content) > LOGO_UPLOAD_MAX_SIZE:
        raise LogoRejectedError("logo_too_large")
    if content_type == "image/svg+xml":
        return _check_svg(content), content_type
    return _shrink_raster(content, box), "image/webp"


def _check_svg(content: bytes) -> bytes:
    if len(content) > LOGO_SVG_MAX_SIZE:
        raise LogoRejectedError("logo_too_large")
    if b"<svg" not in content or _SVG_SCRIPTING.search(content):
        raise LogoRejectedError("logo_invalid")
    return content


def _shrink_raster(content: bytes, box: tuple[int, int]) -> bytes:
    # Pillow's default MAX_IMAGE_PIXELS stays on: a decompression bomb is
    # refused before it is decoded.
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            logo = image.convert("RGBA")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise LogoRejectedError("logo_invalid")
    # thumbnail keeps the aspect ratio and never upscales.
    logo.thumbnail(box, Image.Resampling.LANCZOS)
    out = BytesIO()
    logo.save(out, format="WEBP", lossless=False, quality=85, method=6)
    return out.getvalue()
