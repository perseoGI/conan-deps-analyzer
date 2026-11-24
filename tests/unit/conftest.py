import pytest

from parser.utils import _get_available_versions_from_config, _get_conandata


@pytest.fixture(autouse=True)
def clear_utils_lru_caches():
    """Avoid cross-test pollution from cached config/conandata paths."""
    _get_available_versions_from_config.cache_clear()
    _get_conandata.cache_clear()
    yield
    _get_available_versions_from_config.cache_clear()
    _get_conandata.cache_clear()
