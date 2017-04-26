import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def correct_privkey_permissions(request):
    os.chmod('tests/keys/privkey_repo', 0o600)
    os.chmod('tests/keys/privkey_submodule', 0o600)
