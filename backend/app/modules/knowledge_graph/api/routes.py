from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.core.security import current_user, writer
from app.infrastructure.database import get_db
from app.shared.services import require, save, listing, audit
from app.modules.knowledge_graph.models.entities import Entity, Relation, Document
from app.modules.knowledge_graph.schemas.contracts import (
    EntityInput,
    RelationInput,
    DocumentInput,
    SearchInput,
    ImportInput,
)
from app.modules.knowledge_graph.services.retrieval import retrieve, graph, paths

router = APIRouter(prefix="/knowledge-graph", tags=["知识图谱"])


@router.get("/entities")
def entities(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Entity, 1000)


@router.post("/entities", status_code=201)
def create_entity(
    body: EntityInput, db: Session = Depends(get_db), user=Depends(writer)
):
    return save(db, Entity(**body.model_dump()), user, "knowledge.entity.create")


@router.put("/entities/{identifier}")
def update_entity(
    identifier: str,
    body: EntityInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    record = require(db, Entity, identifier)
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    return save(db, record, user, "knowledge.entity.update")


@router.delete("/entities/{identifier}")
def delete_entity(identifier: str, db: Session = Depends(get_db), user=Depends(writer)):
    if any(identifier in d.entity_ids for d in db.scalars(select(Document))):
        raise HTTPException(409, "实体被知识文档引用，请先修改文档关联")
    db.delete(require(db, Entity, identifier))
    audit(db, user, "knowledge.entity.delete", identifier)
    db.commit()
    return {"deleted": identifier}


@router.get("/relations")
def relations(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Relation, 2000)


@router.post("/relations", status_code=201)
def create_relation(
    body: RelationInput, db: Session = Depends(get_db), user=Depends(writer)
):
    require(db, Entity, body.source_id)
    require(db, Entity, body.target_id)
    return save(db, Relation(**body.model_dump()), user, "knowledge.relation.create")


@router.delete("/relations/{identifier}")
def delete_relation(
    identifier: str, db: Session = Depends(get_db), user=Depends(writer)
):
    db.delete(require(db, Relation, identifier))
    audit(db, user, "knowledge.relation.delete", identifier)
    db.commit()
    return {"deleted": identifier}


@router.get("/documents")
def documents(db: Session = Depends(get_db), user=Depends(current_user)):
    return listing(db, Document, 1000)


@router.put("/documents/{identifier}")
def update_document(
    identifier: str,
    body: DocumentInput,
    db: Session = Depends(get_db),
    user=Depends(writer),
):
    record = require(db, Document, identifier)
    for entity_id in body.entity_ids:
        require(db, Entity, entity_id)
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    record.version += 1
    return save(db, record, user, "knowledge.document.update")


@router.get("/export")
def export_knowledge(db: Session = Depends(get_db), user=Depends(current_user)):
    records = list(db.scalars(select(Entity)))
    keys = {e.id: e.kind + ":" + e.name for e in records}
    return {
        "entities": [
            {k: getattr(e, k) for k in EntityInput.model_fields} for e in records
        ],
        "relations": [
            {
                "source_key": keys[r.source_id],
                "target_key": keys[r.target_id],
                "kind": r.kind,
                "source": r.source,
                "properties": r.properties,
            }
            for r in db.scalars(select(Relation))
        ],
        "documents": [
            {
                "title": d.title,
                "content": d.content,
                "source": d.source,
                "entity_keys": [keys[i] for i in d.entity_ids if i in keys],
            }
            for d in db.scalars(select(Document))
        ],
    }


@router.post("/documents", status_code=201)
def create_document(
    body: DocumentInput, db: Session = Depends(get_db), user=Depends(writer)
):
    for identifier in body.entity_ids:
        require(db, Entity, identifier)
    return save(db, Document(**body.model_dump()), user, "knowledge.document.create")


@router.get("/graph")
def get_graph(db: Session = Depends(get_db), user=Depends(current_user)):
    return graph(db)


@router.post("/search")
def search(
    body: SearchInput, db: Session = Depends(get_db), user=Depends(current_user)
):
    return retrieve(db, **body.model_dump())


@router.get("/paths")
def get_paths(
    source: str,
    target: str,
    max_hops: int = Query(4, ge=1, le=6),
    directed: bool = True,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    require(db, Entity, source)
    require(db, Entity, target)
    return paths(db, source, target, max_hops, directed)


@router.post("/import")
def import_knowledge(
    body: ImportInput, db: Session = Depends(get_db), user=Depends(writer)
):
    existing_entities = list(db.scalars(select(Entity)))
    name_counts = {}
    name_map = {}
    for entity in existing_entities:
        name_counts[entity.name] = name_counts.get(entity.name, 0) + 1
        name_map[entity.kind + ":" + entity.name] = entity.id
        name_map[entity.name] = entity.id
    added = 0
    relations_added = 0
    documents_added = 0
    for item in body.entities:
        existing = db.scalar(
            select(Entity).where(Entity.name == item.name, Entity.kind == item.kind)
        )
        if existing:
            name_map[item.name] = existing.id
            name_map[item.kind + ":" + item.name] = existing.id
            continue
        entity = Entity(**item.model_dump())
        db.add(entity)
        db.flush()
        name_map[entity.name] = entity.id
        name_map[entity.kind + ":" + entity.name] = entity.id
        name_counts[entity.name] = name_counts.get(entity.name, 0) + 1
        added += 1
    for item in body.relations:
        if any(
            name_counts.get(item.get(key), 0) > 1
            for key in ["source_name", "target_name"]
        ):
            raise HTTPException(
                422, "存在同名不同类型实体，请使用source_key/target_key（类型:名称）"
            )
        source_id = name_map.get(
            item.get("source_key") or item.get("source_name"), item.get("source_id")
        )
        target_id = name_map.get(
            item.get("target_key") or item.get("target_name"), item.get("target_id")
        )
        if not source_id or not target_id:
            raise HTTPException(422, "关系端点未找到")
        try:
            validated = RelationInput(
                source_id=source_id,
                target_id=target_id,
                kind=item.get("kind", ""),
                source=item.get("source", ""),
                properties=item.get("properties", {}),
            )
        except ValidationError:
            raise HTTPException(422, "关系字段不完整或格式无效")
        require(db, Entity, source_id)
        require(db, Entity, target_id)
        duplicate = db.scalar(
            select(Relation).where(
                Relation.source_id == source_id,
                Relation.target_id == target_id,
                Relation.kind == validated.kind,
                Relation.source == validated.source,
            )
        )
        if not duplicate:
            db.add(Relation(**validated.model_dump()))
            db.flush()
            relations_added += 1
    for document in body.documents:
        linked_ids = list(document.entity_ids)
        for entity_key in document.entity_keys:
            if entity_key not in name_map:
                raise HTTPException(422, "文档引用的实体不存在：" + entity_key)
            linked_ids.append(name_map[entity_key])
        for identifier in linked_ids:
            require(db, Entity, identifier)
        duplicate = db.scalar(
            select(Document).where(
                Document.title == document.title,
                Document.source == document.source,
                Document.content == document.content,
            )
        )
        if not duplicate:
            db.add(
                Document(
                    **document.model_dump(exclude={"entity_keys", "entity_ids"}),
                    entity_ids=sorted(set(linked_ids)),
                )
            )
            db.flush()
            documents_added += 1
    audit(
        db,
        user,
        "knowledge.import",
        detail={
            "entities_added": added,
            "relations": len(body.relations),
            "documents": len(body.documents),
        },
    )
    db.commit()
    return {
        "entities_added": added,
        "relations_added": relations_added,
        "documents_added": documents_added,
    }
