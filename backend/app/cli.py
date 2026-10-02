import argparse
import getpass
import sys

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role
from app.services.demo_seed import seed_demo_data
from app.services.depreciation_service import run_depreciation


def _cmd_init_db(_args) -> None:
    init_db()
    print("Database initialized.")


def _cmd_seed_admin(args) -> None:
    init_db()

    password = args.password
    if not password:
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(2)

    if not password:
        print("Password must not be empty.", file=sys.stderr)
        sys.exit(2)

    with Session(engine) as db:
        existing = db.exec(select(User).where(User.username == args.username)).first()
        if existing:
            print(f"User '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)

        user = User(
            username=args.username,
            email=args.email,
            full_name=args.full_name,
            password_hash=hash_password(password),
            role=Role.ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Admin user '{user.username}' created (id={user.id}).")


def _cmd_seed_demo(_args) -> None:
    init_db()
    with Session(engine) as db:
        result = seed_demo_data(db)

    if result["categories"] == 0 and result["assets"] == 0:
        print("Demo data already present; nothing to do.")
    else:
        print(
            f"Demo data seeded: {result['categories']} categories, "
            f"{result['assets']} assets."
        )


def _cmd_depreciate(args) -> None:
    init_db()
    with Session(engine) as db:
        result = run_depreciation(db, through_period=args.through)

    print(
        f"Depreciation run through {result.through_period}: "
        f"{result.assets_processed} assets processed, "
        f"{result.records_written} records written."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Create database tables")
    p_init.set_defaults(func=_cmd_init_db)

    p_seed = sub.add_parser("seed-admin", help="Create the initial administrator account")
    p_seed.add_argument("--username", required=True)
    p_seed.add_argument("--email", required=True)
    p_seed.add_argument("--full-name", required=True)
    p_seed.add_argument("--password", default=None, help="If omitted, will prompt securely.")
    p_seed.set_defaults(func=_cmd_seed_admin)

    p_demo = sub.add_parser(
        "seed-demo",
        help="Insert deterministic demo categories and assets",
    )
    p_demo.set_defaults(func=_cmd_seed_demo)

    p_dep = sub.add_parser(
        "depreciate",
        help="Compute and persist depreciation for all active assets",
    )
    p_dep.add_argument(
        "--through",
        required=True,
        help="End period label, e.g. 2024",
    )
    p_dep.set_defaults(func=_cmd_depreciate)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()