"""从项目根目录运行：backend/.venv/Scripts/python deploy/mysql/02_seed_demo.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from app.infrastructure.database import SessionLocal
from app.infrastructure.seed import initialize_admin, seed_demo

with SessionLocal() as db:
    initialize_admin(db)
    seed_demo(db)
    db.commit()
print('账户及示例数据已初始化。')
