from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return category_service.list_categories(db)


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.EDIT_ASSETS)),
):
    return category_service.create_category(db, payload, user)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return category_service.get_category(db, category_id)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.EDIT_ASSETS)),
):
    return category_service.update_category(db, category_id, payload, user)