# type: ignore

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import factory
from sqlalchemy.ext.asyncio import AsyncSession

from models import EmailTable, UserTable
from services.auth import get_password_hash


class AsyncFactory(factory.Factory):
    class Meta:
        abstract = True

    @classmethod
    async def create_async(
        cls,
        session: AsyncSession,
        *,
        commit: bool = True,
        **kwargs: Any,
    ):
        obj = cls.build(**kwargs)
        session.add(obj)

        if commit:
            await session.commit()
            await session.refresh(obj)
        else:
            await session.flush()

        return obj

    @classmethod
    async def create_batch_async(
        cls,
        session: AsyncSession,
        size: int,
        *,
        commit: bool = True,
        **kwargs: Any,
    ):
        """Create multiple instances at once"""
        objects = []
        for _ in range(size):
            obj = cls.build(**kwargs)
            session.add(obj)
            objects.append(obj)

        if commit:
            await session.commit()
            for obj in objects:
                await session.refresh(obj)
        else:
            await session.flush()

        return objects


class UserFactory(AsyncFactory):
    class Meta:
        model = UserTable

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password_hash = factory.LazyFunction(lambda: get_password_hash("testpassword"))


class EmailFactory(AsyncFactory):
    class Meta:
        model = EmailTable

    message_id = factory.Sequence(lambda n: f"message-{n}")
    provider = "google"
    sender = factory.Sequence(lambda n: f"sender{n}@example.com")
    recipient = factory.Sequence(lambda n: f"recipient{n}@example.com")
    recipients_cc = factory.LazyFunction(list)
    recipients_bcc = factory.LazyFunction(list)
    subject = factory.Sequence(lambda n: f"Test subject {n}")
    body_text = factory.Sequence(lambda n: f"Test body {n}")
    body_html = None
    received_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    headers = factory.LazyFunction(dict)
    attachments = factory.LazyFunction(list)
    raw_data = factory.LazyFunction(dict)
    user_id = None
