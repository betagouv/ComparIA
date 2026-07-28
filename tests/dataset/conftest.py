import pytest

from tests.dataset.test_comparison_to_turns import patched_llms_data


@pytest.fixture(autouse=True)
def stub_llms_data():
    """
    `compute.get_llms_data` reads the database. Both dataset modules go through
    it, so stub it for the whole package and put it back afterwards rather than
    leaving the patch installed for the rest of the session.
    """
    with patched_llms_data():
        yield
