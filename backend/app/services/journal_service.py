from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.accounting.rounding import round_money
from app.audit.writer import write_audit
from app.models.depreciation_record import DepreciationRecord
from app.models.journal import JournalEntry, JournalLine, JournalStatus
from app.models.period import AccountingPeriod
from app.models.user import User
from app.schemas.journal import JournalLineRead, JournalRead, PrepareJournalRequest
from app.services import period_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_journal_code(db: Session) -> str:
    rows = db.exec(select(JournalEntry.code)).all()
    max_n = 0
    for code in rows:
        if code and code.startswith("JE-"):
            try:
                n = int(code[3:])
                max_n = max(max_n, n)
            except ValueError:
                continue
    return f"JE-{max_n + 1:06d}"


def _to_read(db: Session, entry: JournalEntry) -> JournalRead:
    lines = list(
        db.exec(
            select(JournalLine).where(JournalLine.journal_entry_id == entry.id)
        ).all()
    )
    return JournalRead(
        id=entry.id,
        code=entry.code,
        period_label=entry.period_label,
        entry_date=entry.entry_date,
        description=entry.description,
        kind=entry.kind,
        status=entry.status,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
        prepared_by=entry.prepared_by,
        approved_by=entry.approved_by,
        approved_at=entry.approved_at,
        lines=[
            JournalLineRead(
                id=l.id,
                account_code=l.account_code,
                account_name=l.account_name,
                debit=l.debit,
                credit=l.credit,
                memo=l.memo,
            )
            for l in lines
        ],
    )


def prepare_depreciation_journal(
    db: Session, payload: PrepareJournalRequest, actor: User
) -> JournalRead:
    """Prepare (do NOT post) the depreciation journal for a period.

    Idempotent: if a DRAFT entry already exists for this period, return it.
    """
    period = period_service.get_period_by_label(db, payload.period_label)
    if period.status == "LOCKED":
        raise HTTPException(status_code=409, detail="Period is locked")

    # Recompute from authoritative records.
    records = list(
        db.exec(
            select(DepreciationRecord).where(
                DepreciationRecord.period_label == period.label
            )
        ).all()
    )
    total = round_money(sum(r.depreciation for r in records))

    existing = db.exec(
        select(JournalEntry)
        .where(JournalEntry.period_id == period.id)
        .where(JournalEntry.kind == "DEPRECIATION")
    ).first()

    if existing is not None:
        # Refresh totals in case depreciation was rerun.
        existing.total_debit = total
        existing.total_credit = total
        existing.updated_at = _now()
        db.add(existing)

        # Replace lines
        old_lines = list(
            db.exec(
                select(JournalLine).where(JournalLine.journal_entry_id == existing.id)
            ).all()
        )
        for l in old_lines:
            db.delete(l)
        db.flush()

        db.add(
            JournalLine(
                journal_entry_id=existing.id,
                account_code="5100",
                account_name="Depreciation Expense",
                debit=total,
                credit=0.0,
                memo=f"Depreciation for {period.label}",
            )
        )
        db.add(
            JournalLine(
                journal_entry_id=existing.id,
                account_code="1590",
                account_name="Accumulated Depreciation",
                debit=0.0,
                credit=total,
                memo=f"Depreciation for {period.label}",
            )
        )
        write_audit(
            db,
            action="JOURNAL_REPREPARED",
            actor_id=actor.id,
            actor_username=actor.username,
            target_type="JournalEntry",
            target_id=existing.code,
        )
        db.commit()
        db.refresh(existing)
        return _to_read(db, existing)

    entry = JournalEntry(
        code=_next_journal_code(db),
        period_id=period.id,
        period_label=period.label,
        entry_date=period.end_date,
        description=f"Depreciation for period {period.label}",
        kind="DEPRECIATION",
        status=JournalStatus.DRAFT,
        total_debit=total,
        total_credit=total,
        prepared_by=actor.id,
    )
    db.add(entry)
    db.flush()

    db.add(
        JournalLine(
            journal_entry_id=entry.id,
            account_code="5100",
            account_name="Depreciation Expense",
            debit=total,
            credit=0.0,
            memo=f"Depreciation for {period.label}",
        )
    )
    db.add(
        JournalLine(
            journal_entry_id=entry.id,
            account_code="1590",
            account_name="Accumulated Depreciation",
            debit=0.0,
            credit=total,
            memo=f"Depreciation for {period.label}",
        )
    )

    write_audit(
        db,
        action="JOURNAL_PREPARED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="JournalEntry",
        target_id=entry.code,
    )
    db.commit()
    db.refresh(entry)
    return _to_read(db, entry)


def approve_journal(db: Session, journal_id: int, actor: User) -> JournalRead:
    entry = db.get(JournalEntry, journal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal not found")
    if entry.status != JournalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Journal is {entry.status}; only DRAFT can be approved",
        )
    if entry.prepared_by == actor.id:
        raise HTTPException(
            status_code=403,
            detail="The approver cannot be the user who prepared the journal",
        )

    entry.status = JournalStatus.APPROVED
    entry.approved_by = actor.id
    entry.approved_at = _now()
    entry.updated_at = _now()
    db.add(entry)
    write_audit(
        db,
        action="JOURNAL_APPROVED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="JournalEntry",
        target_id=entry.code,
    )
    db.commit()
    db.refresh(entry)
    return _to_read(db, entry)


def list_journals(db: Session) -> list[JournalRead]:
    rows = db.exec(select(JournalEntry).order_by(JournalEntry.created_at.desc())).all()
    return [_to_read(db, e) for e in rows]


def get_journal(db: Session, journal_id: int) -> JournalRead:
    entry = db.get(JournalEntry, journal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal not found")
    return _to_read(db, entry)