import asyncio
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

from backend.admin.router import put_admin_informational_legal_pages
from backend.settings import informational_legal
from backend.settings.informational_legal import (
    InformationalLegalPage,
    InformationalLegalPages,
    default_informational_pages,
)
from utils.database.models.app_settings import AppSettings


def test_seeded_visibility_matches_the_existing_navigation() -> None:
    pages = default_informational_pages()

    assert all(
        page.visible_in_legal_menu and page.visible_in_settings
        for page in (
            pages.pages.legal_notice,
            pages.pages.accessibility,
            pages.pages.ecodesign,
        )
    )


def test_fresh_settings_have_independent_seeded_configuration() -> None:
    first = AppSettings()
    first.informational_legal_pages["legal_notice"]["mode"] = "external"

    assert AppSettings().informational_legal_pages["legal_notice"]["mode"] == "internal"


def test_external_mode_requires_an_absolute_https_url() -> None:
    with pytest.raises(ValidationError, match="required in external mode"):
        InformationalLegalPage(mode="external")

    with pytest.raises(ValidationError, match="absolute HTTPS URL"):
        InformationalLegalPage(mode="external", external_url="http://example.test")

    page = InformationalLegalPage(
        mode="external", external_url=" https://example.test/legal "
    )
    assert page.external_url == "https://example.test/legal"


def test_blank_stored_configuration_falls_back_to_seed() -> None:
    settings = SimpleNamespace(informational_legal_pages=None)
    with patch.object(
        informational_legal, "get_app_settings", AsyncMock(return_value=settings)
    ):
        pages = asyncio.run(informational_legal.get_informational_legal_pages())

    assert pages == default_informational_pages()


def test_admin_update_replaces_the_single_unversioned_configuration() -> None:
    body = InformationalLegalPages.model_validate(
        default_informational_pages().model_dump()
    )
    body.pages.ecodesign.mode = "external"
    body.pages.ecodesign.external_url = "https://example.test/ecodesign"
    admin = SimpleNamespace(id=uuid.uuid4())

    with patch(
        "backend.admin.router.update_app_settings", new_callable=AsyncMock
    ) as update:
        returned = asyncio.run(put_admin_informational_legal_pages(body, admin))

    assert returned == body
    update.assert_awaited_once_with(
        {"informational_legal_pages": body.pages.model_dump(mode="json")},
        updated_by=admin.id,
    )
