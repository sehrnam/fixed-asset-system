"""
Seed one user per role for demo/testing.

Idempotent — safe to re-run. Skips users that already exist.
"""
from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "password": "Admin123!",
        "role": Role.ADMIN.value,
    },
    {
        "username": "accounting",
        "email": "accounting@example.com",
        "full_name": "Accounting Officer",
        "password": "Account123!",
        "role": Role.ACCOUNTING.value,
    },
    {
        "username": "approver",
        "email": "approver@example.com",
        "full_name": "Approver User",
        "password": "Approve123!",
        "role": Role.APPROVER.value,
    },
    {
        "username": "auditor",
        "email": "auditor@example.com",
        "full_name": "Auditor User",
        "password": "Auditor123!",
        "role": Role.AUDITOR.value,
    },
]


def main() -> None:
    init_db()
    created = 0
    skipped = 0
    with Session(engine) as db:
        for spec in USERS:
            existing = db.exec(
                select(User).where(User.username == spec["username"])
            ).first()
            if existing:
                print(f"  SKIP  {spec['username']:12} (id={existing.id}, role={existing.role})")
                skipped += 1
                continue

            user = User(
                username=spec["username"],
                email=spec["email"],
                full_name=spec["full_name"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"  CREATE {user.username:12} (id={user.id}, role={user.role})")
            created += 1

    print(f"\nDone: {created} created, {skipped} skipped.")
    print("\nCredentials:")
    for s in USERS:
        print(f"  {s['username']:12} / {s['password']:14} ({s['role']})")


if __name__ == "__main__":
    main()