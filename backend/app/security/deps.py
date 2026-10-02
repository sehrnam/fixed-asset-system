from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session as DBSession

from app.config import settings
from app.database import get_session
from app.models.user import User
from app.security.permissions import ROLE_PERMISSIONS, Permission, Role
from app.security.sessions import get_valid_session


def get_current_user(
    request: Request,
    db: DBSession = Depends(get_session),
) -> User:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    sess = get_valid_session(db, token)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid or expired")

    user = db.get(User, sess.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    return user


def require_permission(perm: Permission):
    def checker(user: User = Depends(get_current_user)) -> User:
        try:
            role = Role(user.role)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role")
        if perm not in ROLE_PERMISSIONS.get(role, set()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return checker