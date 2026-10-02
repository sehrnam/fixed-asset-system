from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.audit.writer import write_audit
from app.models.category import AssetCategory
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate


def _clean_name(value: str) -> str:
    return value.strip()


def list_categories(db: Session) -> list[AssetCategory]:
    return list(db.exec(select(AssetCategory).order_by(AssetCategory.name)).all())


def get_category(db: Session, category_id: int) -> AssetCategory:
    cat = db.get(AssetCategory, category_id)
    if cat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return cat


def create_category(db: Session, payload: CategoryCreate, actor: User) -> AssetCategory:
    name = _clean_name(payload.name)
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name is required")

    existing = db.exec(select(AssetCategory).where(AssetCategory.name == name)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists",
        )

    cat = AssetCategory(name=name, description=payload.description)
    db.add(cat)
    db.flush()
    write_audit(
        db,
        action="CATEGORY_CREATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="AssetCategory",
        target_id=str(cat.id),
    )
    db.commit()
    db.refresh(cat)
    return cat


def update_category(
    db: Session,
    category_id: int,
    payload: CategoryUpdate,
    actor: User,
) -> AssetCategory:
    cat = get_category(db, category_id)

    if payload.name is not None:
        name = _clean_name(payload.name)
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name is required",
            )
        if name != cat.name:
            dup = db.exec(select(AssetCategory).where(AssetCategory.name == name)).first()
            if dup is not None and dup.id != cat.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A category with that name already exists",
                )
            cat.name = name

    if payload.description is not None:
        cat.description = payload.description

    db.add(cat)
    write_audit(
        db,
        action="CATEGORY_UPDATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="AssetCategory",
        target_id=str(cat.id),
    )
    db.commit()
    db.refresh(cat)
    return cat