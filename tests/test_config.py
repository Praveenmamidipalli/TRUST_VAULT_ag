import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secret_key_rejects_placeholder():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SECRET_KEY="change_me_with_openssl_rand_hex_32")


def test_secret_key_requires_at_least_32_random_bytes():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SECRET_KEY="too-short")
