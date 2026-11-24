"""
PackCheck AI — Administrative User Provisioning Utility
Allows administrators to securely provision or reset authorized officer accounts
without relying on automatic or predictable default credentials.
"""

import argparse
import asyncio
import os
import sys

# Ensure backend root is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User


async def provision_user(email: str, password: str, name: str, role: str, department: str = "", region: str = ""):
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    role_clean = role.lower().strip()
    if role_clean not in ["admin", "inspector"]:
        raise ValueError("Role must be either 'admin' or 'inspector'.")

    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.name = name or user.name
            user.password_hash = hash_password(password)
            user.role = role_clean
            user.department = department or user.department
            user.region = region or user.region
            user.is_active = True
            await session.commit()
            print(f"[PROVISION SUCCESS] Updated existing user account: {email} (Role: {role_clean})")
        else:
            new_user = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role=role_clean,
                department=department or ("Central Legal Metrology Division" if role_clean == "admin" else "Field Inspection Squad"),
                region=region or "National HQ",
                is_active=True,
            )
            session.add(new_user)
            await session.commit()
            print(f"[PROVISION SUCCESS] Created new authorized user account: {email} (Role: {role_clean})")


def main():
    parser = argparse.ArgumentParser(description="PackCheck AI Officer Provisioning Tool")
    parser.add_argument("--email", required=True, help="Officer official email address")
    parser.add_argument("--password", required=True, help="Secure password (minimum 8 characters)")
    parser.add_argument("--name", default="Authorized Officer", help="Full name of officer")
    parser.add_argument("--role", choices=["admin", "inspector"], default="inspector", help="System RBAC role")
    parser.add_argument("--department", default="", help="Department name")
    parser.add_argument("--region", default="", help="Assigned jurisdiction/region")

    args = parser.parse_args()

    try:
        asyncio.run(provision_user(
            email=args.email,
            password=args.password,
            name=args.name,
            role=args.role,
            department=args.department,
            region=args.region,
        ))
    except Exception as e:
        print(f"[PROVISION ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
