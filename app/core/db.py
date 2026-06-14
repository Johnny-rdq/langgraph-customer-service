from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path

# 动态获取项目根目录，并在根目录下创建 storage 文件夹（专门放聊天数据）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)  # 如果没有这个文件夹，自动创建

# SQLite 数据库文件路径
SQLITE_URL = f"sqlite:///{STORAGE_DIR}/chat_database.db"

# 创建数据库引擎
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """在 FastAPI 启动时自动建表"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """依赖注入：获取数据库会话"""
    with Session(engine) as session:
        yield session