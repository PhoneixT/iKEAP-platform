import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
test_configuration = dotenv_values(Path(__file__).resolve().parents[1] / ".env.test")
database_url = os.getenv("IKEAP_TEST_DATABASE_URL") or test_configuration.get(
    "IKEAP_TEST_DATABASE_URL"
)
if database_url:
    from sqlalchemy.engine import make_url

    if "_test_" not in (make_url(database_url).database or ""):
        raise RuntimeError("测试数据库名必须包含_test_，禁止使用业务数据库")
else:
    directory = tempfile.mkdtemp(prefix="ikeap_test_")
    database_url = "sqlite:///" + (Path(directory) / "test.db").as_posix()
os.environ["DATABASE_URL"] = database_url
os.environ["SECRET_KEY"] = secrets.token_hex(32)
os.environ["ADMIN_USERNAME"] = "test_admin"
os.environ["ADMIN_PASSWORD"] = secrets.token_urlsafe(20)

from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database import Base, engine, SessionLocal
from app.infrastructure.seed import initialize_admin, seed_demo
from app.core.security import hash_password
from app.modules.platform.models.entities import User


@pytest.fixture(scope="session")
def client():
    # database_url在模块入口校验为独立测试库，不能指向业务数据库。
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        initialize_admin(db)
        seed_demo(db)
        viewer = User(
            username="test_viewer",
            display_name="只读账户",
            password_hash=hash_password("viewer-test-password"),
            role="viewer",
        )
        db.add(viewer)
        db.commit()
    with TestClient(app) as instance:
        yield instance


@pytest.fixture(scope="session")
def headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["ADMIN_USERNAME"],
            "password": os.environ["ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture(scope="session")
def viewer_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_viewer", "password": "viewer-test-password"},
    )
    return {"Authorization": "Bearer " + response.json()["access_token"]}
