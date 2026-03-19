#!/usr/bin/env python3
"""
Development seed script.

Usage:
    python scripts/seed.py

Creates:
  - Admin user  (admin@example.com / Admin1234)
  - Regular user (user@example.com  / User1234!)
  - One API key for each user
"""
import asyncio
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.api_key import APIKey
from app.services.user_service import hash_password
import uuid


USERS = [
    {
        "email": "admin@example.com",
        "password": "Admin1234",
        "is_superuser": True,
        "key_name": "Admin Default Key",
        "rate_limit": 1000,
    },
    {
        "email": "user@example.com",
        "password": "User1234!",
        "is_superuser": False,
        "key_name": "User Default Key",
        "rate_limit": 100,
    },
]


async def seed():
    await init_db()

    async with AsyncSessionLocal() as db:
        for spec in USERS:
            # Check if user already exists
            from sqlalchemy import select
            existing = await db.execute(
                select(User).where(User.email == spec["email"])
            )
            user = existing.scalar_one_or_none()

            if user:
                print(f"  ⚠  User {spec['email']} already exists — skipping")
                continue

            user = User(
                id=str(uuid.uuid4()),
                email=spec["email"],
                hashed_password=hash_password(spec["password"]),
                is_superuser=spec["is_superuser"],
            )
            db.add(user)
            await db.flush()

            api_key = APIKey(
                user_id=user.id,
                name=spec["key_name"],
                rate_limit=spec["rate_limit"],
            )
            db.add(api_key)
            await db.flush()

            print(f"  ✓  Created {'admin' if spec['is_superuser'] else 'user'}: {spec['email']}")
            print(f"     API Key : {api_key.key}")
            print(f"     Rate    : {api_key.rate_limit} req / {api_key.rate_limit_window}s")

        await db.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
