# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

# This file is automatically imported by all tests.
# Add your global fixtures here

import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Remove errors when no tests where collected.

    See https://github.com/pytest-dev/pytest/issues/2393#issuecomment-452634365.
    """
    if exitstatus == 5:
        session.exitstatus = 0
