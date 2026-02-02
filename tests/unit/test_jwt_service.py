"""Unit tests for JWT service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.app.services.jwt_service import (
    ESI_REFRESH_THRESHOLD_SECONDS,
    JWT_EXPIRY_HOURS,
    JWT_REFRESH_THRESHOLD_MINUTES,
    _revoked_token_expiry,
    _revoked_tokens,
    cleanup_revoked_tokens,
    clear_revoked_tokens,
    decrypt_token,
    encrypt_token,
    generate_client_fingerprint,
    generate_jwt,
    is_token_revoked,
    revoke_token,
    should_refresh_esi_token,
    should_refresh_jwt,
    validate_jwt,
)


class TestTokenEncryption:
    """Tests for token encryption/decryption."""

    def test_encrypt_and_decrypt_token(self):
        """Test round-trip encryption and decryption."""
        original = "test-access-token-12345"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original
        assert encrypted != original  # Should be different

    def test_encrypt_with_custom_secret(self):
        """Test encryption with custom secret key."""
        original = "test-token"
        secret = "custom-secret-key-for-testing-12345678"

        encrypted = encrypt_token(original, secret)
        decrypted = decrypt_token(encrypted, secret)

        assert decrypted == original

    def test_different_secrets_produce_different_ciphertext(self):
        """Test that different secrets produce different encryptions."""
        original = "test-token"
        test_key_a = "test-fixture-key-a-1234567890123"
        test_key_b = "test-fixture-key-b-1234567890123"

        encrypted1 = encrypt_token(original, test_key_a)
        encrypted2 = encrypt_token(original, test_key_b)

        assert encrypted1 != encrypted2

    def test_wrong_secret_returns_garbage(self):
        """Test that wrong secret produces wrong decryption."""
        original = "test-token"
        test_key_correct = "test-fixture-correct-key-123456"
        test_key_wrong = "test-fixture-wrong-key-12345678"

        encrypted = encrypt_token(original, test_key_correct)
        # Decryption with wrong key should not match original
        decrypted = decrypt_token(encrypted, test_key_wrong)

        assert decrypted != original

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        result = encrypt_token("")
        assert result == ""

    def test_decrypt_empty_string(self):
        """Test decryption of empty string."""
        result = decrypt_token("")
        assert result == ""

    def test_decrypt_invalid_base64(self):
        """Test decryption of invalid base64 returns original."""
        invalid = "not-valid-base64!!!"
        result = decrypt_token(invalid)
        assert result == invalid  # Returns original on failure

    def test_encryption_produces_different_results(self):
        """Test that encryption with random salt produces different results."""
        original = "test-token"
        encrypted1 = encrypt_token(original)
        encrypted2 = encrypt_token(original)

        # Different salt should produce different ciphertext
        assert encrypted1 != encrypted2

        # Both should decrypt to original
        assert decrypt_token(encrypted1) == original
        assert decrypt_token(encrypted2) == original


class TestJWTGeneration:
    """Tests for JWT generation."""

    def test_generate_jwt_basic(self):
        """Test basic JWT generation."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        assert token.access_token is not None
        assert token.token_type == "Bearer"
        assert token.character_id == 12345
        assert token.character_name == "Test Pilot"
        assert token.expires_at > datetime.now(UTC)

    def test_generate_jwt_with_fingerprint(self):
        """Test JWT generation with client fingerprint."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            fingerprint="test-fingerprint",
        )

        assert token.access_token is not None
        # Verify fingerprint is in token by validating with it
        payload, error = validate_jwt(token.access_token, verify_fingerprint="test-fingerprint")
        assert error is None
        assert payload.fingerprint == "test-fingerprint"

    def test_generate_jwt_custom_expiry(self):
        """Test JWT generation with custom expiry."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            expiry_hours=48,
        )

        # Token should expire in ~48 hours
        expected_expiry = datetime.now(UTC) + timedelta(hours=48)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 5

    def test_generate_jwt_has_three_parts(self):
        """Test that generated JWT has header.payload.signature format."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
        )

        parts = token.access_token.split(".")
        assert len(parts) == 3


class TestJWTValidation:
    """Tests for JWT validation."""

    def test_validate_valid_jwt(self):
        """Test validation of a valid JWT."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        payload, error = validate_jwt(token.access_token)

        assert error is None
        assert payload is not None
        assert payload.sub == 12345
        assert payload.name == "Test Pilot"
        assert "esi-location.read_location.v1" in payload.scopes

    def test_validate_expired_jwt(self):
        """Test validation of an expired JWT."""
        # Generate token with 0 hour expiry (already expired)
        with patch("backend.app.services.jwt_service.datetime") as mock_dt:
            # Generate token 2 hours in the past
            past_time = datetime.now(UTC) - timedelta(hours=2)
            mock_dt.now.return_value = past_time
            mock_dt.fromtimestamp = datetime.fromtimestamp

            token = generate_jwt(
                character_id=12345,
                character_name="Test Pilot",
                scopes=[],
                expiry_hours=1,
            )

        # Now validate with current time
        payload, error = validate_jwt(token.access_token)

        assert payload is None
        assert error == "Token expired"

    def test_validate_invalid_signature(self):
        """Test validation of JWT with tampered signature."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
        )

        # Tamper with the signature
        parts = token.access_token.split(".")
        parts[2] = "tampered_signature"
        tampered_token = ".".join(parts)

        payload, error = validate_jwt(tampered_token)

        assert payload is None
        assert error == "Invalid signature"

    def test_validate_invalid_format(self):
        """Test validation of malformed JWT."""
        payload, error = validate_jwt("not.a.valid.jwt.token")
        assert payload is None
        assert error == "Invalid token format"

        payload, error = validate_jwt("no-dots")
        assert payload is None
        assert error == "Invalid token format"

    def test_validate_with_fingerprint_match(self):
        """Test validation with matching fingerprint."""
        fingerprint = "client-fingerprint-123"
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            fingerprint=fingerprint,
        )

        payload, error = validate_jwt(token.access_token, verify_fingerprint=fingerprint)

        assert error is None
        assert payload is not None

    def test_validate_with_fingerprint_mismatch(self):
        """Test validation with mismatched fingerprint."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            fingerprint="original-fingerprint",
        )

        payload, error = validate_jwt(
            token.access_token, verify_fingerprint="different-fingerprint"
        )

        assert payload is None
        assert error == "Token fingerprint mismatch"


class TestJWTRefresh:
    """Tests for JWT refresh detection."""

    def test_should_refresh_jwt_not_needed(self):
        """Test that fresh JWT doesn't need refresh."""
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            expiry_hours=JWT_EXPIRY_HOURS,
        )

        payload, _ = validate_jwt(token.access_token)
        assert not should_refresh_jwt(payload)

    def test_should_refresh_jwt_needed(self):
        """Test that expiring JWT needs refresh."""
        from backend.app.services.jwt_service import JWTPayload

        # Create a payload that expires within threshold
        now = datetime.now(UTC)
        payload = JWTPayload(
            sub=12345,
            name="Test Pilot",
            scopes=[],
            iat=now - timedelta(hours=23),
            exp=now + timedelta(minutes=JWT_REFRESH_THRESHOLD_MINUTES - 5),
            jti="test-jti",
        )

        assert should_refresh_jwt(payload)


class TestESITokenRefresh:
    """Tests for ESI token refresh detection."""

    def test_should_refresh_esi_token_not_needed(self):
        """Test that fresh ESI token doesn't need refresh."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        assert not should_refresh_esi_token(expires)

    def test_should_refresh_esi_token_needed(self):
        """Test that expiring ESI token needs refresh."""
        # Expires within threshold
        expires = datetime.now(UTC) + timedelta(seconds=ESI_REFRESH_THRESHOLD_SECONDS - 60)
        assert should_refresh_esi_token(expires)

    def test_should_refresh_esi_token_expired(self):
        """Test that expired ESI token needs refresh."""
        expires = datetime.now(UTC) - timedelta(hours=1)
        assert should_refresh_esi_token(expires)


class TestClientFingerprint:
    """Tests for client fingerprint generation."""

    def test_generate_fingerprint_basic(self):
        """Test basic fingerprint generation."""
        fingerprint = generate_client_fingerprint(
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        assert fingerprint is not None
        assert len(fingerprint) == 16  # Truncated to 16 chars

    def test_generate_fingerprint_consistent(self):
        """Test that same inputs produce same fingerprint."""
        fp1 = generate_client_fingerprint("Mozilla/5.0", "192.168.1.1")
        fp2 = generate_client_fingerprint("Mozilla/5.0", "192.168.1.1")

        assert fp1 == fp2

    def test_generate_fingerprint_different_inputs(self):
        """Test that different inputs produce different fingerprints."""
        fp1 = generate_client_fingerprint("Mozilla/5.0", "192.168.1.1")
        fp2 = generate_client_fingerprint("Chrome/100.0", "192.168.1.1")
        fp3 = generate_client_fingerprint("Mozilla/5.0", "10.0.0.1")

        assert fp1 != fp2
        assert fp1 != fp3
        assert fp2 != fp3

    def test_generate_fingerprint_none_values(self):
        """Test fingerprint generation with None values."""
        fp1 = generate_client_fingerprint(None, None)
        fp2 = generate_client_fingerprint("Mozilla", None)
        fp3 = generate_client_fingerprint(None, "192.168.1.1")

        assert fp1 is not None
        assert fp2 is not None
        assert fp3 is not None


class TestTokenRevocation:
    """Tests for token revocation."""

    def setup_method(self):
        """Clear revocation list before each test."""
        clear_revoked_tokens()

    def test_revoke_token(self):
        """Test token revocation."""
        jti = "test-token-id"
        expires = datetime.now(UTC) + timedelta(hours=1)

        revoke_token(jti, expires)

        assert is_token_revoked(jti)

    def test_is_token_not_revoked(self):
        """Test checking non-revoked token."""
        assert not is_token_revoked("non-existent-token")

    def test_cleanup_revoked_tokens(self):
        """Test cleanup of expired revoked tokens."""
        # Add expired token
        expired_jti = "expired-token"
        _revoked_tokens.add(expired_jti)
        _revoked_token_expiry[expired_jti] = datetime.now(UTC) - timedelta(hours=1)

        # Add valid token
        valid_jti = "valid-token"
        _revoked_tokens.add(valid_jti)
        _revoked_token_expiry[valid_jti] = datetime.now(UTC) + timedelta(hours=1)

        count = cleanup_revoked_tokens()

        assert count == 1
        assert not is_token_revoked(expired_jti)
        assert is_token_revoked(valid_jti)

    def test_clear_revoked_tokens(self):
        """Test clearing all revoked tokens."""
        revoke_token("token1", datetime.now(UTC) + timedelta(hours=1))
        revoke_token("token2", datetime.now(UTC) + timedelta(hours=1))

        count = clear_revoked_tokens()

        assert count == 2
        assert not is_token_revoked("token1")
        assert not is_token_revoked("token2")


class TestIntegration:
    """Integration tests for JWT workflow."""

    def setup_method(self):
        """Clear revocation list before each test."""
        clear_revoked_tokens()

    def test_full_jwt_lifecycle(self):
        """Test complete JWT lifecycle: generate, validate, revoke."""
        # Generate
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        # Validate
        payload, error = validate_jwt(token.access_token)
        assert error is None
        assert payload.sub == 12345

        # Revoke
        revoke_token(payload.jti, payload.exp)

        # Should now be rejected
        assert is_token_revoked(payload.jti)

    def test_jwt_with_encryption(self):
        """Test JWT generation doesn't interfere with encryption."""
        # Generate JWT
        token = generate_jwt(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
        )

        # Encrypt the JWT (simulating storage)
        encrypted = encrypt_token(token.access_token)
        assert encrypted != token.access_token

        # Decrypt and validate
        decrypted = decrypt_token(encrypted)
        payload, error = validate_jwt(decrypted)

        assert error is None
        assert payload.sub == 12345
