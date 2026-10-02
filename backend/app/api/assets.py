from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import asset_service

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(
    search: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return asset_service.list_assets(
        db, search=search, category_id=category_id, asset_status=status
    )


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(
    payload: AssetCreate,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.EDIT_ASSETS)),
):
    return asset_service.create_asset(db, payload, user)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return asset_service.read_asset(db, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.EDIT_ASSETS)),
):
    return asset_service.update_asset(db, asset_id, payload, user)