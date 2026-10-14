import hashlib
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import BACKEND_ROOT
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.modules.platform.models.entities import FileAsset
from app.shared.services import require, listing, save

router = APIRouter(prefix="/platform/files", tags=["文件管理"])
STORAGE = BACKEND_ROOT / "storage"
MAX_FILE_SIZE = 20 * 1024 * 1024


@router.get("")
def files(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, FileAsset)


@router.post("", status_code=201)
def upload(file: UploadFile, db: Session = Depends(get_db), user=Depends(writer)):
    name = (file.filename or "").replace("\\", "/").split("/")[-1]
    if (
        not name
        or len(name) > 255
        or Path(name).suffix.lower()
        not in {".json", ".csv", ".txt", ".step", ".stp", ".stl", ".nc", ".pdf", ".png"}
    ):
        raise HTTPException(422, "请上传JSON、CSV、TXT、STEP、STL、NC、PDF或PNG文件")
    STORAGE.mkdir(parents=True, exist_ok=True)
    key = str(uuid4())
    path = STORAGE / key
    size, digest = 0, hashlib.sha256()
    try:
        with path.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(413, "单个文件不能超过20MB")
                digest.update(chunk)
                output.write(chunk)
        return save(
            db,
            FileAsset(
                name=name,
                storage_key=key,
                content_type=(file.content_type or "application/octet-stream")[:120],
                size=size,
                sha256=digest.hexdigest(),
                owner_id=user.id,
            ),
            user,
            "platform.file.upload",
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/{identifier}/download")
def download(
    identifier: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    record = require(db, FileAsset, identifier)
    path = STORAGE / record.storage_key
    if not path.is_file():
        raise HTTPException(404, "文件内容不存在")
    return FileResponse(
        path,
        filename=record.name,
        media_type="application/octet-stream",
        headers={"X-Content-Type-Options": "nosniff"},
    )
