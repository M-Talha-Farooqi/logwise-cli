import pytest

CLEAN = "2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms"


@pytest.fixture
def clean_line():
    return CLEAN
