from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
_db_url = settings.DATABASE_URL
_is_sqlite = _db_url.startswith("sqlite")

connect_args = (
    {"check_same_thread": False, "timeout": 30}
    if _is_sqlite
    else {}
)

engine_kwargs: dict = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if not _is_sqlite:
    # Railway Postgres — keep pool modest for free/hobby tiers
    engine_kwargs.update(pool_size=5, max_overflow=10, pool_recycle=280)

engine = create_engine(_db_url, **engine_kwargs)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
