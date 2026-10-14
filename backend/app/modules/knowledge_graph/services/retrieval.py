import math
import re
from collections import Counter, defaultdict, deque
from sqlalchemy import select
from app.modules.knowledge_graph.models.entities import Entity, Relation, Document


def tokens(text):
    text = text.lower()
    words = re.findall(r"[a-z0-9_]+", text)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(segment[i : i + 2] for i in range(max(1, len(segment) - 1)))
    return Counter(words)


def similarity(a, b):
    denominator = math.sqrt(
        sum(v * v for v in a.values()) * sum(v * v for v in b.values())
    )
    return (
        sum(v * b.get(k, 0) for k, v in a.items()) / denominator if denominator else 0
    )


def graph(db, limit=500):
    entities = list(db.scalars(select(Entity).order_by(Entity.name).limit(limit)))
    ids = {e.id for e in entities}
    relations = [
        r
        for r in db.scalars(select(Relation))
        if r.source_id in ids and r.target_id in ids
    ]
    return {
        "nodes": [e.as_dict() for e in entities],
        "edges": [r.as_dict() for r in relations],
        "limit": limit,
    }


def retrieve(db, query, limit=8, hops=2):
    query_tokens = tokens(query)
    entities = list(db.scalars(select(Entity).limit(5000)))
    by_id = {e.id: e for e in entities}
    ranked = []
    for entity in entities:
        text = " ".join([entity.name, entity.kind, entity.description, *entity.aliases])
        score = similarity(query_tokens, tokens(text))
        if entity.name.lower() in query.lower() or any(
            a.lower() in query.lower() for a in entity.aliases if a
        ):
            score += 0.6
        if score > 0:
            ranked.append((score, entity))
    ranked.sort(key=lambda row: (-row[0], row[1].id))
    selected = ranked[:limit]
    selected_ids = {entity.id for _, entity in selected}
    visited = set(selected_ids)
    relations = list(db.scalars(select(Relation).limit(20000)))
    adjacency = defaultdict(list)
    for relation in relations:
        adjacency[relation.source_id].append((relation.target_id, relation))
        adjacency[relation.target_id].append((relation.source_id, relation))
    evidence_edges = {}
    frontier = deque((identifier, 0) for identifier in sorted(selected_ids))
    while frontier and len(visited) < 200:
        identifier, depth = frontier.popleft()
        if depth >= hops:
            continue
        for neighbor, relation in adjacency[identifier]:
            evidence_edges[relation.id] = relation
            if neighbor not in visited and neighbor in by_id and len(visited) < 200:
                visited.add(neighbor)
                frontier.append((neighbor, depth + 1))
    documents = []
    for document in db.scalars(select(Document).limit(5000)):
        score = similarity(
            query_tokens, tokens(document.title + " " + document.content)
        )
        if visited.intersection(document.entity_ids):
            score += 0.25
        if score > 0:
            documents.append((score, document))
    documents.sort(key=lambda row: (-row[0], row[1].id))
    evidence = [
        {
            "evidence_id": f"D:{d.id}",
            "title": d.title,
            "text": d.content[:2500],
            "source": d.source,
            "version": d.version,
            "score": round(score, 4),
        }
        for score, d in documents[:limit]
    ]
    evidence += [
        {
            "evidence_id": f"R:{r.id}",
            "title": f"{by_id[r.source_id].name} — {r.kind} → {by_id[r.target_id].name}",
            "source": r.source,
            "text": str(r.properties),
        }
        for r in evidence_edges.values()
        if r.source_id in by_id and r.target_id in by_id
    ][:30]
    return {
        "query": query,
        "status": "found" if evidence else "no_evidence",
        "entities": [
            {"score": round(score, 4), **e.as_dict()} for score, e in selected
        ],
        "subgraph": {
            "nodes": [by_id[i].as_dict() for i in sorted(visited)],
            "edges": [r.as_dict() for r in evidence_edges.values()],
        },
        "evidence": evidence,
        "retrieval_method": "character-bigram-cosine+entity-linking+graph-expansion",
        "hops": hops,
        "context": "\n".join(
            f"[{item['evidence_id']}] {item['title']}\n{item['text']}\n来源：{item['source']}"
            for item in evidence
        )[:16000],
    }


def paths(db, source, target, max_hops=4, directed=True):
    adjacency = defaultdict(list)
    for relation in db.scalars(select(Relation).limit(20000)):
        adjacency[relation.source_id].append((relation.target_id, relation))
        if not directed:
            adjacency[relation.target_id].append((relation.source_id, relation))
    queue = deque([(source, [source], [])])
    found, expanded = [], 0
    while queue and len(found) < 20 and expanded < 10000:
        current, nodes, edges = queue.popleft()
        expanded += 1
        if current == target:
            found.append({"nodes": nodes, "edges": edges, "hops": len(edges)})
            continue
        if len(edges) >= max_hops:
            continue
        for neighbor, relation in adjacency[current]:
            if neighbor not in nodes:
                queue.append(
                    (neighbor, [*nodes, neighbor], [*edges, relation.as_dict()])
                )
    return {"paths": found, "expanded": expanded, "truncated": bool(queue)}
