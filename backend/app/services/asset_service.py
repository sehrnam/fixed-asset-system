from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.audit.writer import write_audit
from app.models.asset import Asset, AssetStatus, DepreciationMethod
from app.models.category import AssetCategory
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(db: Session, asset: Asset) -> AssetRead:
    category = db.get(AssetCategory, asset.category_id)
    return AssetRead(
        id=asset.id,
        asset_code=asset.asset_code,
        name=asset.name,
        category_id=asset.category_id,
        category_name=category.name if category else None,
        cost=asset.cost,
        acquisition_date=asset.acquisition_date,
        useful_life_years=asset.useful_life_years,
        depreciation_method=asset.depreciation_method,
        residual_value=asset.residual_value,
        rate=asset.rate,
        description=asset.description,
        location=asset.location,
        status=asset.status,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _generate_asset_code(db: Session) -> str:
    rows = db.exec(select(Asset.asset_code)).all()
    max_n = 0
    for code in rows:
        if code and code.startswith("FA-"):
            try:
                n = int(code[3:])
                max_n = max(max_n, n)
            except ValueError:
                continue
    return f"FA-{max_n + 1:05d}"


def _validate_asset_payload(
    db: Session,
    *,
    cost: float,
    residual_value: float,
    useful_life_years: int,
    depreciation_method: str,
    rate: Optional[float],
    acquisition_date: datetime,
    category_id: int,
) -> None:
    if cost <= 0:
        raise HTTPException(status_code=400, detail="Cost must be greater than zero")
    if residual_value < 0:
        raise HTTPException(status_code=400, detail="Residual value cannot be negative")
    if residual_value >= cost:
        raise HTTPException(
            status_code=400,
            detail="Residual value must be less than cost",
        )
    if useful_life_years <= 0:
        raise HTTPException(status_code=400, detail="Useful life must be greater than zero")

    if depreciation_method not in DepreciationMethod.ALL:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported depreciation method: {depreciation_method}",
        )

    if depreciation_method == DepreciationMethod.REDUCING_BALANCE:
        if rate is None:
            raise HTTPException(
                status_code=400,
                detail="Rate is required for the reducing-balance method",
            )
        if rate <= 0 or rate >= 100:
            raise HTTPException(
                status_code=400,
                detail="Rate must be greater than 0 and less than 100",
            )

    # Acquisition date: reject future dates (project MVP default).
    now = _now()
    acq = acquisition_date
    if acq.tzinfo is None:
        acq = acq.replace(tzinfo=timezone.utc)
    if acq > now:
        raise HTTPException(
            status_code=400,
            detail="Acquisition date cannot be in the future",
        )

    category = db.get(AssetCategory, category_id)
    if category is None:
        raise HTTPException(status_code=400, detail="Category does not exist")


def list_assets(
    db: Session,
    *,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    asset_status: Optional[str] = None,
) -> list[AssetRead]:
    stmt = select(Asset)
    if category_id is not None:
        stmt = stmt.where(Asset.category_id == category_id)
    if asset_status is not None:
        stmt = stmt.where(Asset.status == asset_status)

    assets = list(db.exec(stmt.order_by(Asset.asset_code)).all())

    if search:
        needle = search.strip().lower()
        assets = [a for a in assets if needle in a.name.lower() or needle in a.asset_code.lower()]

    return [_to_read(db, a) for a in assets]


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


def read_asset(db: Session, asset_id: int) -> AssetRead:
    return _to_read(db, get_asset(db, asset_id))


def create_asset(db: Session, payload: AssetCreate, actor: User) -> AssetRead:
    asset_code = (payload.asset_code or "").strip() or _generate_asset_code(db)

    existing = db.exec(select(Asset).where(Asset.asset_code == asset_code)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with that code already exists",
        )

    _validate_asset_payload(
        db,
        cost=payload.cost,
        residual_value=payload.residual_value,
        useful_life_years=payload.useful_life_years,
        depreciation_method=payload.depreciation_method,
        rate=payload.rate,
        acquisition_date=payload.acquisition_date,
        category_id=payload.category_id,
    )

    asset = Asset(
        asset_code=asset_code,
        name=payload.name.strip(),
        category_id=payload.category_id,
        cost=payload.cost,
        acquisition_date=payload.acquisition_date,
        useful_life_years=payload.useful_life_years,
        depreciation_method=payload.depreciation_method,
        residual_value=payload.residual_value,
        rate=payload.rate,
        description=payload.description,
        location=payload.location,
        status=AssetStatus.ACTIVE,
    )
    db.add(asset)
    db.flush()

    write_audit(
        db,
        action="ASSET_CREATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Asset",
        target_id=asset.asset_code,
    )
    db.commit()
    db.refresh(asset)
    return _to_read(db, asset)


def update_asset(
    db: Session,
    asset_id: int,
    payload: AssetUpdate,
    actor: User,
) -> AssetRead:
    asset = get_asset(db, asset_id)

    # Compute effective values after applying the patch, then validate.
    new_cost = payload.cost if payload.cost is not None else asset.cost
    new_residual = (
        payload.residual_value if payload.residual_value is not None else asset.residual_value
    )
    new_life = (
        payload.useful_life_years
        if payload.useful_life_years is not None
        else asset.useful_life_years
    )
    new_method = (
        payload.depreciation_method
        if payload.depreciation_method is not None
        else asset.depreciation_method
    )
    new_rate = payload.rate if payload.rate is not None else asset.rate
    new_acq = (
        payload.acquisition_date
        if payload.acquisition_date is not None
        else asset.acquisition_date
    )
    new_category_id = (
        payload.category_id if payload.category_id is not None else asset.category_id
    )

    _validate_asset_payload(
        db,
        cost=new_cost,
        residual_value=new_residual,
        useful_life_years=new_life,
        depreciation_method=new_method,
        rate=new_rate,
        acquisition_date=new_acq,
        category_id=new_category_id,
    )

    # Apply
    if payload.name is not None:
        asset.name = payload.name.strip()
    asset.category_id = new_category_id
    asset.cost = new_cost
    asset.acquisition_date = new_acq
    asset.useful_life_years = new_life
    asset.depreciation_method = new_method
    asset.residual_value = new_residual
    asset.rate = new_rate
    if payload.description is not None:
        asset.description = payload.description
    if payload.location is not None:
        asset.location = payload.location
    asset.updated_at = _now()

    db.add(asset)
    write_audit(
        db,
        action="ASSET_UPDATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Asset",
        target_id=asset.asset_code,
    )
    db.commit()
    db.refresh(asset)
    return _to_read(db, asset)