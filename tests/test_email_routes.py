from datetime import datetime, timedelta, timezone


class TestListEmails:
    async def test_list_emails(self, get_client, test_user, email_factory, async_db):
        """Test listing emails for authenticated user"""
        now = datetime.now(timezone.utc)

        await email_factory(
            message_id="google-1",
            provider="google",
            sender="ceo@example.com",
            recipient="finance@example.com",
            recipients_cc=["assistant@example.com"],
            recipients_bcc=[],
            subject="Urgent wire request",
            body_text="Please process the wire today.",
            body_html=None,
            received_at=now - timedelta(minutes=2),  # Oldest
            headers={"X-Test": "1"},
            attachments=[],
            raw_data={"provider": "google"},
            user_id=test_user.id,
        )

        await email_factory(
            message_id="microsoft-1",
            provider="microsoft",
            sender="supplier@example.com",
            recipient="ap@example.com",
            recipients_cc=[],
            recipients_bcc=["audit@example.com"],
            subject="Updated bank details",
            body_text="Please update our bank account.",
            body_html=None,
            received_at=now - timedelta(minutes=1),  # Middle
            headers={"X-Test": "2"},
            attachments=[],
            raw_data={"provider": "microsoft"},
            user_id=test_user.id,
        )

        await email_factory(
            message_id="google-2",
            provider="google",
            sender="cfo@example.com",
            recipient="finance@example.com",
            recipients_cc=[],
            recipients_bcc=[],
            subject="Payment follow-up",
            body_text="Following up on the payment.",
            body_html=None,
            received_at=now,  # Most recent
            headers={"X-Test": "3"},
            attachments=[],
            raw_data={"provider": "google"},
            user_id=test_user.id,
        )

        # Get authenticated client for the test user
        client = get_client(test_user)

        # Test listing emails for the authenticated user
        response = await client.get("/emails")
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["count"] == 3

        # Emails should be ordered by received_at descending (most recent first)
        assert response_data["emails"][0]["message_id"] == "google-2"  # Most recent
        assert response_data["emails"][1]["message_id"] == "microsoft-1"  # Middle
        assert response_data["emails"][2]["message_id"] == "google-1"  # Oldest

    async def test_user_isolation(self, get_client, user_factory, email_factory):
        """Test that users can only see their own emails"""
        # Create two users with different emails
        user1 = await user_factory(email="user1@example.com")
        user2 = await user_factory(email="user2@example.com")

        now = datetime.now(timezone.utc)

        # Create emails for both users
        await email_factory(
            message_id="user1-email",
            provider="google",
            sender="sender1@example.com",
            recipient="recipient1@example.com",
            recipients_cc=[],
            recipients_bcc=[],
            subject="User 1 email",
            body_text="This belongs to user 1",
            body_html=None,
            received_at=now,
            headers={},
            attachments=[],
            raw_data={},
            user_id=user1.id,
        )

        await email_factory(
            message_id="user2-email",
            provider="google",
            sender="sender2@example.com",
            recipient="recipient2@example.com",
            recipients_cc=[],
            recipients_bcc=[],
            subject="User 2 email",
            body_text="This belongs to user 2",
            body_html=None,
            received_at=now,
            headers={},
            attachments=[],
            raw_data={},
            user_id=user2.id,
        )

        # Get client for user 1 and verify they only see their email
        client1 = get_client(user1)
        response1 = await client1.get("/emails")
        assert response1.status_code == 200

        response1_data = response1.json()
        assert response1_data["count"] == 1
        assert response1_data["emails"][0]["message_id"] == "user1-email"

        # Get client for user 2 and verify they only see their email
        client2 = get_client(user2)
        response2 = await client2.get("/emails")
        assert response2.status_code == 200

        response2_data = response2.json()
        assert response2_data["count"] == 1
        assert response2_data["emails"][0]["message_id"] == "user2-email"
