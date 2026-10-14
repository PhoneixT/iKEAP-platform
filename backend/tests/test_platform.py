from uuid import uuid4

PREFIX = "/api/v1"


def test_authentication_and_role_boundary(client, headers, viewer_headers):
    assert client.get(PREFIX + "/knowledge-graph/entities").status_code == 401
    assert (
        "password_hash" not in client.get(PREFIX + "/auth/me", headers=headers).json()
    )
    assert (
        client.post(
            PREFIX + "/platform/resources",
            headers=viewer_headers,
            json={"name": "禁止创建", "kind": "machine"},
        ).status_code
        == 403
    )
    assert (
        client.get(PREFIX + "/platform/users", headers=viewer_headers).status_code
        == 403
    )


def test_retrieval_provenance_and_multihop(client, headers):
    result = client.post(
        PREFIX + "/knowledge-graph/search",
        headers=headers,
        json={"query": "TC4叶盘加工刀具", "hops": 2},
    ).json()
    assert result["evidence"] and all(
        item["source"] and item["evidence_id"] for item in result["evidence"]
    )
    entities = client.get(PREFIX + "/knowledge-graph/entities", headers=headers).json()
    lookup = {e["name"]: e["id"] for e in entities}
    path = client.get(
        PREFIX + "/knowledge-graph/paths",
        headers=headers,
        params={
            "source": lookup["整体叶盘"],
            "target": lookup["球头铣刀"],
            "max_hops": 3,
        },
    ).json()
    assert path["paths"] and path["paths"][0]["hops"] == 2


def test_atomic_import_rollback(client, headers):
    name = "rollback-" + str(uuid4())
    response = client.post(
        PREFIX + "/knowledge-graph/import",
        headers=headers,
        json={
            "entities": [{"name": name, "kind": "工艺", "source": "测试"}],
            "relations": [
                {
                    "source_name": name,
                    "target_name": "missing",
                    "kind": "测试",
                    "source": "测试",
                }
            ],
        },
    )
    assert response.status_code == 422
    assert not any(
        e["name"] == name
        for e in client.get(
            PREFIX + "/knowledge-graph/entities", headers=headers
        ).json()
    )


def test_export_can_be_imported_with_document_links(client, headers):
    exported = client.get(PREFIX + "/knowledge-graph/export", headers=headers)
    assert exported.status_code == 200
    assert any(d["entity_keys"] for d in exported.json()["documents"])
    imported = client.post(
        PREFIX + "/knowledge-graph/import", headers=headers, json=exported.json()
    )
    assert imported.status_code == 200


def test_validation_hard_failure_unknown_and_unit_conversion(client, headers):
    base = {
        "scope": "cam",
        "parameters": {
            "spindle_speed": 3200,
            "feed_rate": 600,
            "cut_depth": 0.3,
            "tool_diameter": 8,
        },
    }
    assert (
        client.post(
            PREFIX + "/constraint-validation/evaluate", headers=headers, json=base
        ).json()["status"]
        == "passed"
    )
    base["parameters"]["cut_depth"] = 5
    assert (
        client.post(
            PREFIX + "/constraint-validation/evaluate", headers=headers, json=base
        ).json()["status"]
        == "failed"
    )
    del base["parameters"]["cut_depth"]
    assert (
        client.post(
            PREFIX + "/constraint-validation/evaluate", headers=headers, json=base
        ).json()["status"]
        == "unknown"
    )
    base["parameters"].update(cut_depth=0.3, spindle_speed=60)
    base["units"] = {"spindle_speed": "Hz"}
    report = client.post(
        PREFIX + "/constraint-validation/evaluate", headers=headers, json=base
    ).json()
    assert (
        next(f for f in report["findings"] if f.get("field") == "spindle_speed")[
            "value"
        ]
        == 3600
    )


def test_resource_limit_uses_converted_units(client, headers):
    resource = client.post(
        PREFIX + "/platform/resources",
        headers=headers,
        json={
            "name": "低转速资源",
            "kind": "machine",
            "capabilities": {"max_rpm": 3000, "max_feed": 8000},
        },
    ).json()
    result = client.post(
        PREFIX + "/constraint-validation/evaluate",
        headers=headers,
        json={
            "scope": "cam",
            "parameters": {
                "spindle_speed": 60,
                "feed_rate": 600,
                "cut_depth": 0.3,
                "tool_diameter": 8,
            },
            "units": {"spindle_speed": "Hz"},
            "resource_id": resource["id"],
        },
    ).json()
    assert result["status"] == "failed"


def test_reasoning_evidence_validation_and_external_configuration(
    client, headers, monkeypatch
):
    result = client.post(
        PREFIX + "/hybrid-reasoning/runs",
        headers=headers,
        json={"task": "TC4整体叶盘加工工艺", "domain": "cam", "mode": "template"},
    ).json()
    assert len(result["candidates"]) == 2
    allowed = {e["evidence_id"] for e in result["evidence"]["evidence"]}
    assert all(set(c["evidence_ids"]).issubset(allowed) for c in result["candidates"])
    assert all(c["validation"]["status"] == "passed" for c in result["candidates"])
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    assert (
        client.post(
            PREFIX + "/hybrid-reasoning/runs",
            headers=headers,
            json={"task": "TC4整体叶盘加工", "mode": "external"},
        ).status_code
        == 503
    )
    assert (
        client.post(
            PREFIX + "/hybrid-reasoning/runs",
            headers=headers,
            json={"task": "TC4加工", "parameters": {"feed_rate": "bad"}},
        ).status_code
        == 422
    )


def test_workflow_execution_idempotency_and_failed_constraint(client, headers):
    workflows = client.get(
        PREFIX + "/agent-orchestration/workflows", headers=headers
    ).json()
    workflow = next(w for w in workflows if w["name"] == "知识与验证协同流程")
    body = {
        "context": {
            "query": "TC4叶盘",
            "task": "TC4叶盘加工工艺",
            "domain": "cam",
            "parameters": {
                "spindle_speed": 3200,
                "feed_rate": 600,
                "cut_depth": 0.3,
                "tool_diameter": 8,
            },
        },
        "idempotency_key": str(uuid4()),
    }
    submitted = client.post(
        PREFIX + f"/agent-orchestration/workflows/{workflow['id']}/run",
        headers=headers,
        json=body,
    )
    assert submitted.status_code == 202
    job_id = submitted.json()["id"]
    result = client.get(
        PREFIX + "/agent-orchestration/jobs/" + job_id, headers=headers
    ).json()
    assert result["status"] == "completed" and result["progress"] == 100
    assert len(result["events"]) >= 8
    repeated = client.post(
        PREFIX + f"/agent-orchestration/workflows/{workflow['id']}/run",
        headers=headers,
        json=body,
    )
    assert repeated.json()["id"] == job_id
    body["context"]["parameters"]["cut_depth"] = 5
    assert (
        client.post(
            PREFIX + f"/agent-orchestration/workflows/{workflow['id']}/run",
            headers=headers,
            json=body,
        ).status_code
        == 409
    )
    body["idempotency_key"] = str(uuid4())
    rejected = client.post(
        PREFIX + f"/agent-orchestration/workflows/{workflow['id']}/run",
        headers=headers,
        json=body,
    ).json()
    assert (
        client.get(
            PREFIX + "/agent-orchestration/jobs/" + rejected["id"], headers=headers
        ).json()["status"]
        == "failed"
    )


def test_workflow_rejects_cycle_and_unknown_action(client, headers):
    nodes = [
        {"id": "a", "action": "knowledge.search", "depends_on": ["b"], "input": {}},
        {"id": "b", "action": "knowledge.search", "depends_on": ["a"], "input": {}},
    ]
    assert (
        client.post(
            PREFIX + "/agent-orchestration/workflows",
            headers=headers,
            json={"name": "cycle", "nodes": nodes},
        ).status_code
        == 422
    )
    nodes = [{"id": "a", "action": "system.execute", "input": {}}]
    assert (
        client.post(
            PREFIX + "/agent-orchestration/workflows",
            headers=headers,
            json={"name": "unknown", "nodes": nodes},
        ).status_code
        == 422
    )


def test_cam_demonstration_cannot_be_approved(client, headers):
    resource = next(
        r
        for r in client.get(PREFIX + "/platform/resources", headers=headers).json()
        if r["capabilities"].get("max_rpm", 0) >= 3200
    )
    project = client.post(
        PREFIX + "/blisk-cam/projects",
        headers=headers,
        json={"name": "测试加工", "resource_id": resource["id"]},
    ).json()
    prefix = PREFIX + "/blisk-cam/projects/" + project["id"]
    assert (
        client.post(
            prefix + "/simulate", headers=headers, json={"mode": "demonstration"}
        ).status_code
        == 409
    )
    assert client.post(prefix + "/plan", headers=headers).status_code == 200
    response = client.post(
        prefix + "/simulate", headers=headers, json={"mode": "demonstration"}
    )
    assert response.status_code == 200
    assert response.json()["execution"]["simulation"]["engineering_verified"] is False
    assert client.post(prefix + "/approve", headers=headers).status_code == 409
    assert client.post(prefix + "/dispatch", headers=headers).status_code == 409


def test_phm_ingestion_diagnosis_maintenance_closure(client, headers):
    machine = client.post(
        PREFIX + "/cnc-phm/machines",
        headers=headers,
        json={"name": "测试主轴", "code": "TEST-" + str(uuid4())[:8]},
    ).json()
    response = client.post(
        PREFIX + f"/cnc-phm/machines/{machine['id']}/telemetry",
        headers=headers,
        json={
            "samples": [
                {"time": "2026-10-14T08:00:00Z", "vibration_rms": 6, "temperature": 82}
            ]
        },
    )
    assert response.status_code == 200
    anomaly = response.json()["anomaly"]
    assert anomaly
    duplicate = client.post(
        PREFIX + f"/cnc-phm/machines/{machine['id']}/telemetry",
        headers=headers,
        json={
            "samples": [
                {"time": "2026-10-14T08:00:00Z", "vibration_rms": 6, "temperature": 82}
            ]
        },
    ).json()
    assert (
        duplicate["anomaly"]["id"] == anomaly["id"]
        and duplicate["deduplicated"] is True
    )
    diagnosis = client.post(
        PREFIX + f"/cnc-phm/anomalies/{anomaly['id']}/diagnose",
        headers=headers,
        json={"mode": "template"},
    )
    assert diagnosis.json()["diagnosis"]["confirmed"] is False
    order = client.post(
        PREFIX + "/cnc-phm/maintenance",
        headers=headers,
        json={
            "anomaly_id": anomaly["id"],
            "title": "检查主轴",
            "assignee": "测试人员",
            "actions": ["检查润滑与轴承"],
        },
    ).json()
    endpoint = PREFIX + "/cnc-phm/maintenance/" + order["id"]
    assert (
        client.patch(
            endpoint,
            headers=headers,
            json={"status": "completed", "feedback": "维护完成"},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            endpoint, headers=headers, json={"status": "in_progress"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            endpoint, headers=headers, json={"status": "completed"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            endpoint,
            headers=headers,
            json={"status": "completed", "feedback": "补充润滑后复测振动恢复"},
        ).status_code
        == 200
    )
    closed = next(
        a
        for a in client.get(PREFIX + "/cnc-phm/anomalies", headers=headers).json()
        if a["id"] == anomaly["id"]
    )
    assert closed["status"] == "closed"
    assert (
        client.post(
            PREFIX + f"/cnc-phm/machines/{machine['id']}/rul", headers=headers, json={}
        ).json()["remaining_hours"]
        is None
    )


def test_rul_uses_real_time_intervals_and_handles_stable_signal(client, headers):
    machine = client.post(
        PREFIX + "/cnc-phm/machines",
        headers=headers,
        json={"name": "趋势测试", "code": "TREND-" + str(uuid4())[:8]},
    ).json()
    samples = [
        {"time": f"2026-10-14T0{i}:00:00Z", "vibration_rms": i + 1, "temperature": 50}
        for i in range(5)
    ]
    client.post(
        PREFIX + f"/cnc-phm/machines/{machine['id']}/telemetry",
        headers=headers,
        json={"samples": samples},
    )
    result = client.post(
        PREFIX + f"/cnc-phm/machines/{machine['id']}/rul",
        headers=headers,
        json={"failure_threshold": 10},
    ).json()
    assert result["remaining_hours"] == 5 and result["r_squared"] == 1
    assert result["validated_life_model"] is False


def test_mcp_and_a2a_exchange(client, headers, viewer_headers):
    rpc = lambda method, params={}: {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    assert (
        client.post("/mcp", headers=headers, json=rpc("initialize")).json()["result"][
            "protocolVersion"
        ]
        == "2025-06-18"
    )
    assert (
        len(
            client.post("/mcp", headers=headers, json=rpc("tools/list")).json()[
                "result"
            ]["tools"]
        )
        == 3
    )
    output = client.post(
        "/mcp",
        headers=headers,
        json=rpc(
            "tools/call",
            {"name": "knowledge_search", "arguments": {"query": "TC4叶盘"}},
        ),
    ).json()
    assert output["result"]["isError"] is False
    assert (
        client.post(
            "/mcp",
            headers={**headers, "Origin": "http://invalid.example"},
            json=rpc("tools/list"),
        ).status_code
        == 403
    )
    denied = client.post(
        "/mcp",
        headers=viewer_headers,
        json=rpc(
            "tools/call",
            {
                "name": "constraints_validate",
                "arguments": {"scope": "cam", "parameters": {}},
            },
        ),
    ).json()
    assert denied["result"]["isError"] is True
    response = client.post(
        "/a2a",
        headers=headers,
        json=rpc(
            "message/send",
            {
                "message": {
                    "kind": "message",
                    "messageId": str(uuid4()),
                    "role": "user",
                    "parts": [{"kind": "text", "text": "TC4叶盘加工"}],
                }
            },
        ),
    )
    task_id = response.json()["result"]["id"]
    task = client.post(
        "/a2a", headers=headers, json=rpc("tasks/get", {"id": task_id})
    ).json()["result"]
    assert task["status"]["state"] == "completed" and task["artifacts"]


def test_file_upload_digest_download_and_permissions(client, headers, viewer_headers):
    import hashlib

    content = b'{"fixture": 1}'
    response = client.post(
        PREFIX + "/platform/files",
        headers=headers,
        files={"file": ("fixture.json", content, "application/json")},
    )
    assert response.status_code == 201
    assert response.json()["sha256"] == hashlib.sha256(content).hexdigest()
    downloaded = client.get(
        PREFIX + "/platform/files/" + response.json()["id"] + "/download",
        headers=headers,
    )
    assert downloaded.content == content
    assert (
        client.post(
            PREFIX + "/platform/files",
            headers=viewer_headers,
            files={"file": ("x.json", b"{}")},
        ).status_code
        == 403
    )
