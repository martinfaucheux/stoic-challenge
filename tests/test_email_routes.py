from tests.factories import EmailFactory, UserFactory


class TestListEmails:
    async def test_list_emails(self, get_client, test_user, email_factory, async_db):
        """
        GIVEN some emails
        WHEN an authenticated user requests their emails
        THEN they should receive a list of their emails
        """
        # Create 5 emails for the test user using batch
        emails = await EmailFactory.create_batch_async(
            async_db, 5, user_id=test_user.id
        )

        # Get authenticated client
        client = get_client(test_user)

        # Request emails
        response = await client.get("/emails")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert len(data["emails"]) == 5
        assert data["offset"] == 0
        assert data["limit"] == 50

        # Verify emails belong to the user
        email_ids = {str(email.id) for email in emails}
        returned_ids = {email["id"] for email in data["emails"]}
        assert returned_ids == email_ids

    async def test_user_isolation(
        self, get_client, user_factory, email_factory, async_db
    ):
        """
        GIVEN several user with several emails
        WHEN a user list their emails
        THEN they should only receive their own emails
        """
        # Create 3 users
        users = await UserFactory.create_batch_async(async_db, 3)
        user1, user2, user3 = users

        # Create emails for each user using batch
        user1_emails = await EmailFactory.create_batch_async(
            async_db, 3, user_id=user1.id
        )
        await EmailFactory.create_batch_async(async_db, 4, user_id=user2.id)
        await EmailFactory.create_batch_async(async_db, 2, user_id=user3.id)

        # Get authenticated client for user1
        client = get_client(user1)

        # Request emails as user1
        response = await client.get("/emails")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["emails"]) == 3

        # Verify only user1's emails are returned
        user1_email_ids = {str(email.id) for email in user1_emails}
        returned_ids = {email["id"] for email in data["emails"]}
        assert returned_ids == user1_email_ids
