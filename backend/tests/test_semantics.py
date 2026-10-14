from uuid import uuid4

PREFIX = "/api/v1"


def test_task_parser_and_semantic_consistency(client, headers):
    task = client.post(
        PREFIX + "/hybrid-reasoning/parse",
        headers=headers,
        json={
            "task": "TC4叶盘加工，转速3600rpm，进给速度500mm/min，切深0.2mm",
            "domain": "cam",
        },
    )
    assert task.status_code == 200
    assert task.json()["extracted_parameters"]["spindle_speed"] == 3600
    assert task.json()["extracted_parameters"]["cut_depth"] == 0.2
    unsupported = client.post(
        PREFIX + "/hybrid-reasoning/parse",
        headers=headers,
        json={"task": "转速60Hz，进给500mm/s", "domain": "cam"},
    ).json()
    assert unsupported["extracted_parameters"] == {}
    entities = client.get(PREFIX + "/knowledge-graph/entities", headers=headers).json()
    material = next(e for e in entities if e["name"] == "TC4钛合金")
    part = next(e for e in entities if e["name"] == "整体叶盘")
    payload = {
        "scope": "cam",
        "parameters": {
            "spindle_speed": 3200,
            "feed_rate": 600,
            "cut_depth": 0.3,
            "tool_diameter": 8,
        },
        "semantic_constraints": {
            "entities": [{"entity_id": material["id"], "expected_kind": "材料"}],
            "relations": [
                {"source_id": part["id"], "target_id": material["id"], "kind": "材料"}
            ],
        },
    }
    assert (
        client.post(
            PREFIX + "/constraint-validation/evaluate", headers=headers, json=payload
        ).json()["status"]
        == "passed"
    )
    payload["semantic_constraints"]["entities"][0]["expected_kind"] = "设备"
    assert (
        client.post(
            PREFIX + "/constraint-validation/evaluate", headers=headers, json=payload
        ).json()["status"]
        == "failed"
    )


def test_cancelled_job_is_not_executed(client, headers, monkeypatch):
    from app.modules.agent_orchestration.api import routes
    from app.modules.agent_orchestration.services.executor import run_job

    monkeypatch.setattr(routes, "run_job", lambda identifier: None)
    workflow = client.get(
        PREFIX + "/agent-orchestration/workflows", headers=headers
    ).json()[0]
    response = client.post(
        PREFIX + f"/agent-orchestration/workflows/{workflow['id']}/run",
        headers=headers,
        json={"context": {}, "idempotency_key": str(uuid4())},
    )
    job_id = response.json()["id"]
    assert response.json()["status"] == "submitted"
    assert (
        client.post(
            PREFIX + f"/agent-orchestration/jobs/{job_id}/cancel", headers=headers
        ).status_code
        == 200
    )
    run_job(job_id)
    result = client.get(
        PREFIX + f"/agent-orchestration/jobs/{job_id}", headers=headers
    ).json()
    assert result["status"] == "cancelled" and result["result"] == {}
