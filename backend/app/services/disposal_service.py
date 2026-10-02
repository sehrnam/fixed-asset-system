from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.accounting.engine import net_book_value_at
from app.accounting.rounding import round_money
from app.audit.writer import write_audit
from app.models.asset import Asset, AssetStatus
from app.models.depreciation_record import DepreciationRecord
from app.models.disposal import Disposal, DisposalStatus
from app.models.user import User
from app.schemas.disposal import DisposalCreate, DisposalRead
from app.services import period_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_label_for(dt: datetime) -> str:
    return str(dt.year)


def _to_read(db: Session, d: Disposal) -> DisposalRead:
    asset = db.get(Asset, d.asset_id)
    return DisposalRead(
        id=d.id,
        asset_id=d.asset_id,
        asset_code=asset.asset_code if asset else "",
        asset_name=asset.name if asset else "",
        disposal_date=d.disposal_date,
        proceeds=d.proceeds,
        reason=d.reason,
        nbv_at_disposal=d.nbv_at_disposal,
        gain_loss=d.gain_loss,
        method_used=d.method_used,
        period_label_used=d.period_label_used,
        status=d.status,
        requested_by=d.requested_by,
        approved_by=d.approved_by,
        approved_at=d.approved_at,
        created_at=d.created_at,
    )


def _compute_nbv(db: Session, asset: Asset, disposal_date: datetime) -> tuple[float, str]:
    """Return (NBV, method) at disposal date under the frozen demo policy."""
    period_label = _period_label_for(disposal_date)
    records = list(
        db.exec(
            select(DepreciationRecord).where(DepreciationRecord.asset_id == asset.id)
        ).all()
    )
    nbv = net_book_value_at(asset, records, period_label)
    return round_money(nbv), asset.depreciation_method


def create_disposal(db: Session, payload: DisposalCreate, actor: User) -> DisposalRead:
    asset = db.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.status != AssetStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Asset is {asset.status}; only ACTIVE assets can be disposed",
        )

    # Ensure we have a PENDING record doesn't already exist for this asset.
    existing = db.exec(
        select(Disposal)
        .where(Disposal.asset_id == asset.id)
        .where(Disposal.status == DisposalStatus.PENDING)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="A pending disposal already exists for this asset",
        )

    # No future disposal dates.
    disposal_date = payload.disposal_date
    if disposal_date.tzinfo is None:
        disposal_date = disposal_date.replace(tzinfo=timezone.utc)
    if disposal_date > _now():
        raise HTTPException(status_code=400, detail="Disposal date cannot be in the future")
    if disposal_date < asset.acquisition_date:
        raise HTTPException(
            status_code=400,
            detail="Disposal date cannot be before the acquisition date",
        )

    period_label = _period_label_for(disposal_date)
    period_service.assert_period_open(db, period_label)

    nbv, method = _compute_nbv(db, asset, disposal_date)
    gain_loss = round_money(payload.proceeds - nbv)

    d = Disposal(
        asset_id=asset.id,
        disposal_date=disposal_date,
        proceeds=payload.proceeds,
        reason=payload.reason,
        nbv_at_disposal=nbv,
        gain_loss=gain_loss,
        method_used=method,
        period_label_used=period_label,
        status=DisposalStatus.PENDING,
        requested_by=actor.id,
    )
    db.add(d)
    db.flush()
    write_audit(
        db,
        action="DISPOSAL_REQUESTED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Disposal",
        target_id=str(d.id),
    )
    db.commit()
    db.refresh(d)
    return _to_read(db, d)


def approve_disposal(db: Session, disposal_id: int, actor: User) -> DisposalRead:
    d = db.get(Disposal, disposal_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Disposal not found")
    if d.status != DisposalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Disposal is {d.status}; only PENDING can be approved",
        )

    period_service.assert_period_open(db, d.period_label_used)

    # Maker-checker: approver cannot be the same user who created the request.
    if d.requested_by == actor.id:
        raise HTTPException(
            status_code=403,
            detail="The approver cannot be the same user who created the disposal request",
        )

    d.status = DisposalStatus.APPROVED
    d.approved_by = actor.id
    d.approved_at = _now()
    d.updated_at = _now()

    asset = db.get(Asset, d.asset_id)
    if asset is not None:
        asset.status = AssetStatus.DISPOSED
        asset.updated_at = _now()
        db.add(asset)

    db.add(d)
    write_audit(
        db,
        action="DISPOSAL_APPROVED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Disposal",
        target_id=str(d.id),
    )
    db.commit()
    db.refresh(d)
    return _to_read(db, d)


def reject_disposal(
    db: Session, disposal_id: int, actor: User, reason: Optional[str] = None
) -> DisposalRead:
    d = db.get(Disposal, disposal_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Disposal not found")
    if d.status != DisposalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Disposal is {d.status}")

    d.status = DisposalStatus.REJECTED
    d.approved_by = actor.id
    d.approved_at = _now()
    d.updated_at = _now()
    if reason:
        d.reason = (d.reason or "") + f" | Rejected: {reason}"
    db.add(d)
    write_audit(
        db,
        action="DISPOSAL_REJECTED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Disposal",
        target_id=str(d.id),
    )
    db.commit()
    db.refresh(d)
    return _to_read(db, d)


def list_disposals(db: Session, status_filter: Optional[str] = None) -> list[DisposalRead]:
    stmt = select(Disposal)
    if status_filter:
        stmt = stmt.where(Disposal.status == status_filter)
    rows = db.exec(stmt.order_by(Disposal.created_at.desc())).all()
    return [_to_read(db, d) for d in rows]


def get_disposal(db: Session, disposal_id: int) -> DisposalRead:
    d = db.get(Disposal, disposal_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Disposal not found")
    return _to_read(db, d)