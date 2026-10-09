"""
CLI commands - v3.0 (monthly).

v3.0 changes:
  - seed-demo -> seed-bank (uses bank_seed.py)
  - depreciate now takes a monthly label ('YYYY-MM')
  - new catchup command (runs to current month)
  - new list-periods command for inspection
"""
import argparse
import getpass
import sys
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.period import period_label as make_label
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


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


def _cmd_seed_bank(_args) -> None:
    """Seed the bank's fixed assets (one representative asset per category).

    No-op if any asset already exists. Wipe the DB to re-seed.
    """
    init_db()
    from app.services.bank_seed import seed_bank_data

    with Session(engine) as db:
        result = seed_bank_data(db)

    if result["categories"] == 0 and result["assets"] == 0:
        print("Bank data already present; nothing to do.")
    else:
        print(
            f"Bank data seeded: {result['categories']} categories, "
            f"{result['assets']} assets."
        )


def _cmd_depreciate(args) -> None:
    """Run depreciation through a specific monthly period.

    Args:
        --through: 'YYYY-MM' label, e.g. '2026-10'
    """
    init_db()
    from app.services.depreciation_service import run_depreciation

    with Session(engine) as db:
        try:
            result = run_depreciation(db, through_period=args.through)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print(
        f"Depreciation run through {result.through_period}: "
        f"{result.assets_processed} assets processed, "
        f"{result.records_written} records written."
    )


def _cmd_catchup(_args) -> None:
    """Run depreciation from the latest existing record through the
    current calendar month. Same routine as startup bootstrap."""
    init_db()
    from app.services.depreciation_service import run_depreciation

    today = datetime.now(timezone.utc).date()
    through = make_label(today.year, today.month)

    with Session(engine) as db:
        result = run_depreciation(db, through_period=through)

    print(
        f"Catch-up complete through {result.through_period}: "
        f"{result.assets_processed} assets processed, "
        f"{result.records_written} records written."
    )


def _cmd_list_periods(_args) -> None:
    """List every monthly period that has depreciation records."""
    init_db()
    from app.models.depreciation_record import DepreciationRecord

    with Session(engine) as db:
        labels = list(
            db.exec(
                select(DepreciationRecord.period_label)
                .distinct()
                .order_by(DepreciationRecord.period_label.desc())
            ).all()
        )

    if not labels:
        print("No depreciation periods yet.")
        return

    print(f"{len(labels)} period(s):")
    for label in labels:
        print(f"  {label}")


def _cmd_bootstrap(_args) -> None:
    """Run the full self-healing bootstrap (same as startup)."""
    init_db()
    from app.services.bootstrap import bootstrap_if_empty

    summary = bootstrap_if_empty()
    print("Bootstrap summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Create database tables")
    p_init.set_defaults(func=_cmd_init_db)

    p_seed = sub.add_parser("seed-admin", help="Create an administrator account")
    p_seed.add_argument("--username", required=True)
    p_seed.add_argument("--email", required=True)
    p_seed.add_argument("--full-name", required=True)
    p_seed.add_argument("--password", default=None, help="If omitted, will prompt securely.")
    p_seed.set_defaults(func=_cmd_seed_admin)

    p_bank = sub.add_parser(
        "seed-bank",
        help="Insert the bank's fixed assets (one asset per category from the sheet)",
    )
    p_bank.set_defaults(func=_cmd_seed_bank)

    p_dep = sub.add_parser(
        "depreciate",
        help="Run depreciation through a monthly period",
    )
    p_dep.add_argument(
        "--through",
        required=True,
        help="End period label, e.g. 2026-10",
    )
    p_dep.set_defaults(func=_cmd_depreciate)

    p_catchup = sub.add_parser(
        "catchup",
        help="Run depreciation from latest record through current month",
    )
    p_catchup.set_defaults(func=_cmd_catchup)

    p_periods = sub.add_parser(
        "list-periods",
        help="List every monthly period that has depreciation records",
    )
    p_periods.set_defaults(func=_cmd_list_periods)

    p_boot = sub.add_parser(
        "bootstrap",
        help="Run the full self-healing bootstrap (same as app startup)",
    )
    p_boot.set_defaults(func=_cmd_bootstrap)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()