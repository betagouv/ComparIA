import asyncio
import io
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from backend.admin.llms import router as admin_lab_router
from backend.config import LAB_LOGO_BOX, LOGO_UPLOAD_MAX_SIZE
from backend.llms import router as public_lab_router
from utils.database.models.llms import LLMLab


class FakeResult:
    def __init__(self, lab: LLMLab | None):
        self.lab = lab

    def one_or_none(self) -> LLMLab | None:
        return self.lab


class FakeSession:
    def __init__(self, lab: LLMLab | None):
        self.lab = lab

    async def get(self, _model, _id):
        return self.lab

    async def exec(self, _statement):
        return FakeResult(self.lab)

    def add(self, _lab):
        pass

    async def commit(self):
        pass

    async def refresh(self, _lab):
        pass


def session_factory(lab: LLMLab | None):
    @asynccontextmanager
    async def get_session():
        yield FakeSession(lab)

    return get_session


def make_lab() -> LLMLab:
    return LLMLab(name="Example", logo="example.svg", origin_country="FR")


def test_upload_and_public_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    lab = make_lab()
    monkeypatch.setattr(admin_lab_router, "get_session", session_factory(lab))
    monkeypatch.setattr(public_lab_router, "get_session", session_factory(lab))
    monkeypatch.setattr(admin_lab_router, "invalidate_cache", lambda _key: None)
    upload = UploadFile(filename="logo.svg", file=io.BytesIO(b"<svg></svg>"))
    upload.headers = {"content-type": "image/svg+xml"}

    result = asyncio.run(admin_lab_router.upload_lab_logo(lab.id, upload))
    response = asyncio.run(public_lab_router.get_lab_logo(lab.id))

    assert result.has_custom_logo is True
    assert response.body == b"<svg></svg>"
    assert response.media_type == "image/svg+xml"
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_a_big_png_is_served_as_a_small_webp(monkeypatch: pytest.MonkeyPatch) -> None:
    lab = make_lab()
    monkeypatch.setattr(admin_lab_router, "get_session", session_factory(lab))
    monkeypatch.setattr(public_lab_router, "get_session", session_factory(lab))
    monkeypatch.setattr(admin_lab_router, "invalidate_cache", lambda _key: None)
    png = io.BytesIO()
    Image.new("RGB", (2000, 2000), (0, 0, 145)).save(png, format="PNG")
    upload = UploadFile(filename="logo.png", file=io.BytesIO(png.getvalue()))
    upload.headers = {"content-type": "image/png"}

    result = asyncio.run(admin_lab_router.upload_lab_logo(lab.id, upload))
    response = asyncio.run(public_lab_router.get_lab_logo(lab.id))

    assert result.has_custom_logo is True
    assert result.logo_version is not None
    assert response.media_type == "image/webp"
    assert len(response.body) < 10 * 1024
    assert Image.open(io.BytesIO(response.body)).size == LAB_LOGO_BOX


def test_rejects_unsupported_and_oversized_uploads() -> None:
    bad_type = UploadFile(filename="logo.gif", file=io.BytesIO(b"GIF"))
    bad_type.headers = {"content-type": "image/gif"}
    with pytest.raises(HTTPException, match="logo_unsupported_type"):
        asyncio.run(admin_lab_router.upload_lab_logo(uuid4(), bad_type))

    too_large = UploadFile(
        filename="logo.png", file=io.BytesIO(b"x" * (LOGO_UPLOAD_MAX_SIZE + 1))
    )
    too_large.headers = {"content-type": "image/png"}
    with pytest.raises(HTTPException, match="logo_too_large"):
        asyncio.run(admin_lab_router.upload_lab_logo(uuid4(), too_large))


def test_remove_restores_builtin_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    lab = make_lab()
    lab.logo_data = b"custom"
    lab.logo_content_type = "image/png"
    monkeypatch.setattr(admin_lab_router, "get_session", session_factory(lab))
    monkeypatch.setattr(admin_lab_router, "invalidate_cache", lambda _key: None)

    result = asyncio.run(admin_lab_router.delete_lab_logo(lab.id))

    assert result.has_custom_logo is False
    assert result.logo == "example.svg"
    assert lab.logo_data is None
    assert lab.logo_content_type is None


def test_missing_lab_or_logo_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public_lab_router, "get_session", session_factory(None))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(public_lab_router.get_lab_logo(uuid4()))
    assert exc.value.status_code == 404

    monkeypatch.setattr(admin_lab_router, "get_session", session_factory(None))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_lab_router.delete_lab_logo(uuid4()))
    assert exc.value.status_code == 404
