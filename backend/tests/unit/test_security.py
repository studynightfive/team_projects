"""Unit tests for auth security module."""
import time

import jwt
import pytest

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.common.config import settings


class TestPasswordHashing:
    """Test Argon2 password hashing."""

    def test_hash_returns_different_string(self):
        """Hashed password is not the plain password."""
        password = "secure_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$argon2")

    def test_verify_correct_password(self):
        """Correct password verification succeeds."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password verification fails."""
        hashed = hash_password("right_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_empty_password(self):
        """Empty password verification fails gracefully."""
        hashed = hash_password("some_password")
        assert verify_password("", hashed) is False

    def test_same_password_different_hash(self):
        """Same password generates different hashes (salt)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTAccessToken:
    """Test JWT access token creation and decoding."""

    def test_create_and_decode_access_token(self):
        """Created token can be decoded with valid payload."""
        token = create_access_token("user-1", ["chat.use", "admin.user.view"])
        payload = decode_access_token(token)

        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"
        assert "chat.use" in payload["permissions"]
        assert "admin.user.view" in payload["permissions"]
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_decode_invalid_token_raises(self):
        """Decoding an invalid token raises PyJWTError."""
        with pytest.raises(jwt.PyJWTError):
            decode_access_token("not.a.valid.token")

    def test_decode_expired_token_raises(self):
        """Decoding an expired token raises ExpiredSignatureError."""
        # Create a token and immediately decrease its expiry
        import jwt as jwt_module
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-1",
            "permissions": [],
            "type": "access",
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(seconds=1),
            "jti": "test-jti",
        }
        token = jwt_module.encode(payload, settings.secret_key, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_token_without_required_fields(self):
        """Token missing required fields raises error."""
        import jwt as jwt_module

        token = jwt_module.encode(
            {"sub": "user-1"}, settings.secret_key, algorithm="HS256"
        )
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(token)

    def test_create_token_empty_permissions(self):
        """Token can be created with empty permissions."""
        token = create_access_token("user-2", [])
        payload = decode_access_token(token)
        assert payload["sub"] == "user-2"
        assert payload["permissions"] == []


class TestRefreshToken:
    """Test refresh token creation."""

    def test_create_refresh_token_returns_pair(self):
        """Returns raw_token and token_hash."""
        raw_token, token_hash = create_refresh_token("user-1")
        assert raw_token != token_hash
        assert "." in raw_token
        assert len(token_hash) == 64  # SHA-256 hex digest

    def test_refresh_tokens_are_unique(self):
        """Each call generates unique tokens."""
        r1, h1 = create_refresh_token("user-1")
        r2, h2 = create_refresh_token("user-1")
        assert r1 != r2
        assert h1 != h2

    def test_refresh_token_hash_consistent(self):
        """Same raw token produces same hash."""
        import hashlib

        raw, _ = create_refresh_token("user-1")
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()

        raw2, hash2 = create_refresh_token("user-1")
        actual_hash = hashlib.sha256(raw2.encode()).hexdigest()
        assert actual_hash == hash2
