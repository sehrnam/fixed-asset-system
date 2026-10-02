from sqlmodel import SQLModel, Session, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    # Import models so they register with SQLModel.metadata before create_all.
    # Every new SQLModel table must be imported here or it will not be created.
    from app.models import user as _user  # noqa: F401
    from app.models import auth_session as _auth_session  # noqa: F401
    from app.models import audit as _audit  # noqa: F401
    from app.models import category as _category  # noqa: F401
    from app.models import asset as _asset  # noqa: F401
    from app.models import period as _period  # noqa: F401
    from app.models import depreciation_record as _dep  # noqa: F401
    from app.models import workbook as _workbook  # noqa: F401
    from app.models import sheet as _sheet  # noqa: F401
    from app.models import cell as _cell  # noqa: F401
    from app.models import disposal as _disposal  # noqa: F401
    from app.models import journal as _journal  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session