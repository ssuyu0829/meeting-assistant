import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meeting_assistant.db")

# SQLite needs check_same_thread=False; PostgreSQL doesn't need it
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    engine = create_engine(
        DATABASE_URL,
        # Supabase 的 pooler 會主動切掉閒置連線，Render 休眠醒來後第一個請求就會 500。
        # pool_pre_ping 在借出前先探一下，壞的丟掉重連；pool_recycle 讓連線活不過 5 分鐘。
        pool_pre_ping=True,
        pool_recycle=300,
        # 端點都是同步 def（跑在 Starlette 的 threadpool），連線數要撐得住同時進來的請求
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
