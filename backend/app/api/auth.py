from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select

from app.audit.writer import write_audit
from app.config import settings
from app.database import get_session
from app.models.user import User
from app.security.deps import get_current_user
from app.security.passwords import verify_password
from app.security.rate_limit import login_limiter
from app.security.sessions import create_session, revoke_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.allow(f"login:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user = db.exec(select(User).where(User.username == payload.username)).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        write_audit(
            db,
            action="LOGIN_FAILED",
            result="FAILURE",
            actor_username=payload.username,
            source_context=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        write_audit(
            db,
            action="LOGIN_FAILED",
            result="FAILURE",
            actor_id=user.id,
            actor_username=user.username,
            source_context=client_ip,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    sess = create_session(db, user.id)

    response.set_cookie(
        key=settings.cookie_name,
        value=sess.id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
    )

    write_audit(
        db,
        action="LOGIN_SUCCESS",
        result="SUCCESS",
        actor_id=user.id,
        actor_username=user.username,
        source_context=client_ip,
    )

    return {
        "user": UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    token = request.cookies.get(settings.cookie_name)
    if token:
        revoke_session(db, token)

    response.delete_cookie(settings.cookie_name, path="/")

    write_audit(
        db,
        action="LOGOUT",
        result="SUCCESS",
        actor_id=user.id,
        actor_username=user.username,
    )

    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )