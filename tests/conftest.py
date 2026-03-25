import pytest

from parser.utils import get_available_versions_from_config, get_conandata


@pytest.fixture(autouse=True)
def clear_utils_lru_caches():
    """Avoid cross-test pollution from cached config/conandata paths."""
    get_available_versions_from_config.cache_clear()
    get_conandata.cache_clear()
    yield
    get_available_versions_from_config.cache_clear()
    get_conandata.cache_clear()
