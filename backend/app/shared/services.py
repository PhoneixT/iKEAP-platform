from fastapi import HTTPException
from sqlalchemy import select
from app.modules.platform.models.entities import AuditLog


def require(db, model, identifier):
    record = db.get(model, identifier)
    if record is None:
        raise HTTPException(404, "记录不存在")
    return record


def listing(db, model, limit=200):
    return [
        row.as_dict()
        for row in db.scalars(
            select(model).order_by(model.created_at.desc()).limit(limit)
        )
    ]


def audit(db, user, action, target="", detail=None):
    db.add(
        AuditLog(
            actor=user.username if hasattr(user, "username") else str(user),
            action=action,
            target=target,
            detail=detail or {},
        )
    )


def save(db, record, user, action):
    db.add(record)
    db.flush()
    audit(db, user, action, record.id)
    db.commit()
    return record.as_dict()
