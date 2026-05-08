"""Tests for API authentication module."""
from unittest.mock import MagicMock

from api.auth import (
    APIAuthMiddleware,
    authenticate_user,
    create_token,
    decode_token,
    ensure_default_user,
)


class TestTokenCreation:
    def test_create_token(self):
        user = {"id": 1, "username": "test_user", "role": "admin"}
        token = create_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token(self):
        user = {"id": 1, "username": "test_user", "role": "admin"}
        token = create_token(user)
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("sub") == "test_user"
        assert payload.get("role") == "admin"

    def test_decode_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        payload = decode_token("")
        assert payload is None


class TestAuthenticateUser:
    def test_authenticate_user_not_found(self):
        result = authenticate_user("nonexistent_user_xyz", "wrongpassword")
        assert result is None

    def test_authenticate_user_wrong_password(self):
        ensure_default_user()
        result = authenticate_user("admin", "wrongpassword123")
        assert result is None


class TestDefaultUser:
    def test_ensure_default_user(self):
        ensure_default_user()
        user = authenticate_user("admin", "admin123")
        assert user is not None
        assert user.get("username") == "admin"


class TestAPIAuthMiddleware:
    def test_middleware_init(self):
        app = MagicMock()
        middleware = APIAuthMiddleware(app)
        assert middleware is not None

    def test_middleware_has_api_key(self):
        app = MagicMock()
        middleware = APIAuthMiddleware(app, api_key="test_key")
        assert middleware._api_key == "test_key"
