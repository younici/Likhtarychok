from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os

DB_ONLINE = os.getenv("DB_ONLINE", "false").lower() == "true"
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

try:
    int(str(DB_PORT))
except (ValueError, TypeError):
    DB_PORT = "5432"

_has_db_config = DB_ONLINE and all([DB_USER, DB_PASS, DB_HOST, DB_NAME])

AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None

if _has_db_config:
    try:
        db_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_async_engine(db_url)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as e:
        engine = None
        AsyncSessionLocal = None
        print(f"[warn] Failed to initialize DB engine: {e}; DB features are disabled.")
else:
    engine = None
    AsyncSessionLocal = None
    if not DB_ONLINE:
        print("[info] DB is disabled via DB_ONLINE=false.")
    else:
        print("[warn] DB config is incomplete; DB features are disabled.")

def db_available():
    return engine is not None and AsyncSessionLocal is not None
