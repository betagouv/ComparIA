"""
What an uploaded logo turns into before it is stored (no DB).

A logo is served to every visitor on every model card, so a 2 MB PNG must
come out a few KB wide enough for the largest slot, and nothing else.

Run with pytest, or directly:
    uv run python tests/admin/test_logos.py
"""

import os
import random
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from backend.admin.logos import normalize_logo  # noqa: E402
from backend.config import LAB_LOGO_BOX, LOGO_UPLOAD_MAX_SIZE  # noqa: E402
from backend.errors import LogoRejectedError  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'


def png(width: int, height: int) -> bytes:
    # Coarse noise keeps the file from compressing to nothing, like a photo
    # would: 2000x2000 comes out at about 1.6 MB.
    base = max(width * 3 // 10, 1), max(height * 3 // 10, 1)
    pixels = random.Random(0).randbytes(base[0] * base[1] * 3)
    image = Image.frombytes("RGB", base, pixels).resize(
        (width, height), Image.Resampling.NEAREST
    )
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def jpeg(width: int, height: int) -> bytes:
    out = BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(out, format="JPEG")
    return out.getvalue()


def decoded(data: bytes) -> Image.Image:
    return Image.open(BytesIO(data))


def test_a_big_png_comes_out_webp_inside_the_box_and_far_smaller():
    original = png(2000, 2000)
    assert len(original) > 1024 * 1024

    data, content_type = normalize_logo(original, "image/png", LAB_LOGO_BOX)

    assert content_type == "image/webp"
    image = decoded(data)
    assert image.format == "WEBP"
    assert image.size == LAB_LOGO_BOX
    assert len(data) < len(original) / 20


def test_a_wide_png_keeps_its_aspect_ratio():
    data, _ = normalize_logo(png(800, 200), "image/png", (320, 120))

    assert decoded(data).size == (320, 80)


def test_a_small_png_is_not_upscaled():
    data, content_type = normalize_logo(png(40, 40), "image/png", LAB_LOGO_BOX)

    assert content_type == "image/webp"
    assert decoded(data).size == (40, 40)


def test_a_jpeg_is_accepted():
    data, content_type = normalize_logo(jpeg(600, 300), "image/jpeg", LAB_LOGO_BOX)

    assert content_type == "image/webp"
    assert decoded(data).size == (160, 80)


def test_an_svg_passes_through_unchanged():
    assert normalize_logo(SVG, "image/svg+xml", LAB_LOGO_BOX) == (SVG, "image/svg+xml")


@pytest.mark.parametrize(
    "svg",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
    ],
)
def test_an_svg_with_scripting_is_refused(svg: bytes):
    with pytest.raises(LogoRejectedError) as error:
        normalize_logo(svg, "image/svg+xml", LAB_LOGO_BOX)

    assert error.value.detail == "logo_invalid"


def test_garbage_bytes_are_refused():
    with pytest.raises(LogoRejectedError) as error:
        normalize_logo(b"not an image at all", "image/png", LAB_LOGO_BOX)

    assert error.value.detail == "logo_invalid"


def test_an_unknown_type_is_refused():
    with pytest.raises(LogoRejectedError) as error:
        normalize_logo(SVG, "text/html", LAB_LOGO_BOX)

    assert error.value.detail == "logo_unsupported_type"


def test_an_upload_over_the_cap_is_refused():
    with pytest.raises(LogoRejectedError) as error:
        normalize_logo(b"x" * (LOGO_UPLOAD_MAX_SIZE + 1), "image/png", LAB_LOGO_BOX)

    assert error.value.detail == "logo_too_large"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
