"""Tests for Google OAuth and email configuration endpoints"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from models import UserEmailConfiguration
from services.auth import create_oauth_state_token


class TestGoogleEmailConfiguration:
    """Tests for the /email-configuration/google endpoint"""

    @patch("routes.email.google_oauth_service.generate_authorization_url")
    async def test_configure_google_email_success(
        self, mock_auth_url, get_client, test_user
    ):
        """
        GIVEN an authenticated user
        WHEN they request Google email configuration
        THEN they should receive an authorization URL
        """
        mock_auth_url.return_value = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test&state=test_state"

        client = get_client(test_user)
        response = await client.post("/email-configuration/google")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "message" in data
        assert "https://accounts.google.com" in data["authorization_url"]
        # User ID should be encoded in the state JWT token
        assert "state=" in data["authorization_url"]

    @patch("routes.email.google_oauth_service.generate_authorization_url")
    async def test_configure_google_email_includes_state(
        self, mock_auth_url, get_client, test_user
    ):
        """
        GIVEN an authenticated user
        WHEN they request Google email configuration
        THEN the authorization URL should include a state parameter
        """
        mock_auth_url.return_value = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test&state=test_state"

        client = get_client(test_user)
        response = await client.post("/email-configuration/google")

        assert response.status_code == 200
        data = response.json()
        auth_url = data["authorization_url"]
        assert "state=" in auth_url


class TestGetEmailConfigurations:
    """Tests for the /email-configuration endpoint"""

    async def test_get_email_configurations_empty(self, get_client, test_user):
        """
        GIVEN an authenticated user with no email configurations
        WHEN they request their email configurations
        THEN they should receive an empty list
        """
        client = get_client(test_user)
        response = await client.get("/email-configuration")

        assert response.status_code == 200
        data = response.json()
        assert data["configurations"] == []

    async def test_get_email_configurations_with_data(
        self, get_client, test_user, async_db
    ):
        """
        GIVEN an authenticated user with stored email configurations
        WHEN they request their email configurations
        THEN they should receive their configurations without sensitive tokens
        """
        # Create a configuration for the user
        config = UserEmailConfiguration(
            user_id=test_user.id,
            provider="google",
            access_token_encrypted="encrypted_access_token",
            refresh_token_encrypted="encrypted_refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_db.add(config)
        await async_db.flush()

        client = get_client(test_user)
        response = await client.get("/email-configuration")

        assert response.status_code == 200
        data = response.json()
        assert len(data["configurations"]) == 1

        config_data = data["configurations"][0]
        assert config_data["provider"] == "google"
        assert "token_expires_at" in config_data
        assert "is_token_valid" in config_data
        # Sensitive tokens should not be in response
        assert "access_token" not in config_data
        assert "refresh_token" not in config_data

    async def test_get_email_configurations_user_isolation(
        self, get_client, user_factory, async_db
    ):
        """
        GIVEN multiple users with different configurations
        WHEN a user requests their configurations
        THEN they should only see their own configurations
        """
        # Create two users with unique emails
        user1 = await user_factory(email=f"user1_{uuid4()}@example.com")
        user2 = await user_factory(email=f"user2_{uuid4()}@example.com")

        # Create configurations for both users
        config1 = UserEmailConfiguration(
            user_id=user1.id,
            provider="google",
            access_token_encrypted="token1",
        )
        config2 = UserEmailConfiguration(
            user_id=user2.id,
            provider="google",
            access_token_encrypted="token2",
        )
        async_db.add(config1)
        async_db.add(config2)
        await async_db.flush()

        # Get configs as user1
        client = get_client(user1)
        response = await client.get("/email-configuration")

        assert response.status_code == 200
        data = response.json()
        assert len(data["configurations"]) == 1
        assert data["configurations"][0]["provider"] == "google"


class TestGoogleOAuthCallback:
    """Tests for the /auth/callback/google endpoint"""

    async def test_google_callback_missing_code(self, async_client, test_user):
        """
        GIVEN an OAuth callback request without a code
        WHEN processing the callback
        THEN it should return a 400 error
        """

        state = create_oauth_state_token(str(test_user.id))
        response = await async_client.get(
            "/auth/callback/google", params={"state": state}
        )

        assert response.status_code == 400
        assert (
            "code" in response.text.lower() or "authorization" in response.text.lower()
        )

    async def test_google_callback_missing_state(self, test_user, async_client):
        """
        GIVEN an OAuth callback request without a state parameter
        WHEN processing the callback
        THEN it should return a 400 error
        """

        response = await async_client.get(
            "/auth/callback/google", params={"code": "test_code"}
        )

        assert response.status_code == 400
        assert "state" in response.text.lower()

    async def test_google_callback_oauth_error(self, async_client):
        """
        GIVEN an OAuth callback with an error parameter
        WHEN processing the callback
        THEN it should return a 400 error with the OAuth error message
        """
        response = await async_client.get(
            "/auth/callback/google", params={"error": "access_denied"}
        )

        assert response.status_code == 400
        assert "OAuth" in response.json()["detail"]

    async def test_google_callback_invalid_state(self, async_client):
        """
        GIVEN an OAuth callback with an invalid state token
        WHEN processing the callback
        THEN it should return a 400 error
        """
        response = await async_client.get(
            "/auth/callback/google",
            params={"code": "test_code", "state": "invalid_state_token"},
        )

        assert response.status_code == 400

    async def test_google_callback_user_not_found(self, async_client):
        """
        GIVEN an OAuth callback with a state token for a non-existent user
        WHEN processing the callback
        THEN it should return a 404 error
        """
        fake_user_id = str(uuid4())
        state = create_oauth_state_token(fake_user_id)

        response = await async_client.get(
            "/auth/callback/google",
            params={"code": "test_code", "state": state},
        )

        # Should return 404 because user doesn't exist (before trying to call Google API)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSyncEmails:
    """Tests for the /emails/sync endpoint"""

    async def test_sync_emails_no_configuration(self, get_client, test_user):
        """
        GIVEN an authenticated user with no email configuration
        WHEN they request to sync emails
        THEN the request should fail with an error
        """
        client = get_client(test_user)
        response = await client.post("/emails/sync")

        assert response.status_code in [400, 422]

    async def test_sync_emails_with_configuration(
        self, get_client, test_user, async_db
    ):
        """
        GIVEN an authenticated user with a valid email configuration
        WHEN they request to sync emails
        THEN it should return success (with mocked email service)
        """
        # Create a configuration for the user
        config = UserEmailConfiguration(
            user_id=test_user.id,
            provider="google",
            access_token_encrypted="encrypted_access_token",
            refresh_token_encrypted="encrypted_refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_db.add(config)
        await async_db.flush()

        # Mock the email sync service
        with patch(
            "services.email_sync.EmailSyncService.sync_user_emails"
        ) as mock_sync:
            mock_sync.return_value = {
                "synced_count": 5,
                "new_count": 3,
                "error_count": 0,
            }

            client = get_client(test_user)
            response = await client.post("/emails/sync", params={"provider": "google"})

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "sync_result" in data
        assert data["sync_result"]["synced_count"] == 5
        assert data["sync_result"]["new_count"] == 3
        assert data["sync_result"]["error_count"] == 0

    async def test_sync_emails_with_max_count(self, get_client, test_user, async_db):
        """
        GIVEN an authenticated user with a configuration
        WHEN they request to sync with a max_count parameter
        THEN the request should pass the max_count to the service
        """
        # Create a configuration for the user
        config = UserEmailConfiguration(
            user_id=test_user.id,
            provider="google",
            access_token_encrypted="encrypted_access_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_db.add(config)
        await async_db.flush()

        # Mock the email sync service
        with patch(
            "services.email_sync.EmailSyncService.sync_user_emails"
        ) as mock_sync:
            mock_sync.return_value = {
                "synced_count": 3,
                "new_count": 2,
                "error_count": 0,
            }

            client = get_client(test_user)
            response = await client.post(
                "/emails/sync", params={"provider": "google", "max_count": 3}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["sync_result"]["synced_count"] == 3
        assert data["sync_result"]["new_count"] == 2
        assert data["sync_result"]["error_count"] == 0
        # Verify the mock was called with the correct parameters
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["max_count"] == 3
        assert call_kwargs["provider"] == "google"

    async def test_sync_emails_provider_parameter(
        self, get_client, test_user, async_db
    ):
        """
        GIVEN an authenticated user
        WHEN they request to sync with a specific provider
        THEN the sync should use that provider
        """
        # Create a configuration for the user
        config = UserEmailConfiguration(
            user_id=test_user.id,
            provider="google",
            access_token_encrypted="encrypted_access_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_db.add(config)
        await async_db.flush()

        # Mock the email sync service
        with patch(
            "services.email_sync.EmailSyncService.sync_user_emails"
        ) as mock_sync:
            mock_sync.return_value = {
                "synced_count": 2,
                "new_count": 1,
                "error_count": 0,
            }

            client = get_client(test_user)
            response = await client.post("/emails/sync", params={"provider": "google"})

        assert response.status_code == 200
        data = response.json()
        assert data["sync_result"]["synced_count"] == 2
        # Verify the mock was called with the correct provider
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["provider"] == "google"

    async def test_sync_emails_authentication_required(self, async_client):
        """
        GIVEN an unauthenticated request
        WHEN trying to sync emails
        THEN it should return a 401 error
        """

        response = await async_client.post("/emails/sync")

        assert response.status_code == 401
