import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://ikeap@127.0.0.1:3306/ikeap_platform?charset=utf8mb4",
)
SECRET_KEY = os.getenv("SECRET_KEY", "")
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
PUBLIC_URL = os.getenv("APP_PUBLIC_URL", "http://localhost:8000").rstrip("/")
