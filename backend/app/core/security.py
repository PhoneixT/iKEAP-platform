import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import config
from app.infrastructure.database import get_db
from app.modules.platform.models.entities import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 600_000
    ).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    _, rounds, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(rounds)
    ).hex()
    return hmac.compare_digest(actual, expected)


def token_for(user: User) -> str:
    if len(config.SECRET_KEY) < 32:
        raise HTTPException(503, "请配置至少32位的SECRET_KEY")
    return jwt.encode(
        {
            "sub": user.id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
            "iat": datetime.now(timezone.utc),
        },
        config.SECRET_KEY,
        algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        if not credentials:
            raise ValueError("missing token")
        claims = jwt.decode(
            credentials.credentials,
            config.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user = db.get(User, claims["sub"])
        if not user or not user.active:
            raise ValueError("inactive account")
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            401, "登录已失效，请重新登录", headers={"WWW-Authenticate": "Bearer"}
        )


def writer(user: User = Depends(current_user)):
    if user.role not in {"admin", "engineer"}:
        raise HTTPException(403, "当前账户仅有查看权限")
    return user


def administrator(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user
