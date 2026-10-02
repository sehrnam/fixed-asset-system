import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import create_app
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role
from app.security.rate_limit import login_limiter


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    # Ensure models are imported before create_all
    from app.models import user as _u  # noqa: F401
    from app.models import auth_session as _s  # noqa: F401
    from app.models import audit as _a  # noqa: F401

    SQLModel.metadata.create_all(eng)
    yield eng


@pytest.fixture
def db(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def seeded_user(db):
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        password_hash=hash_password("Passw0rd!"),
        role=Role.ADMIN.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client(engine):
    login_limiter.reset()
    app = create_app()

    def override_get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()