import json
import httpx
from app.modules.hybrid_reasoning.adapters import model_service
from app.modules.blisk_cam.services import workflow, metaalgorithm

PREFIX = "/api/v1"


def test_external_model_enforces_evidence_ids(client, headers, monkeypatch):
    monkeypatch.setenv("MODEL_BASE_URL", "https://models.example.test/v1")
    monkeypatch.setenv("MODEL_NAME", "test-model-v1")
    original_client = httpx.Client

    def responder(request):
        body = json.loads(request.content)
        context = json.loads(body["messages"][1]["content"])["evidence"]
        reference = context.split("]")[0][1:]
        result = {
            "candidates": [
                {
                    "name": "外部服务测试方案",
                    "description": "结构化候选",
                    "parameters": {
                        "spindle_speed": 3200,
                        "feed_rate": 600,
                        "cut_depth": 0.3,
                        "tool_diameter": 8,
                    },
                    "evidence_ids": [reference],
                    "actions": ["检查参数"],
                }
            ]
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(result)}}]}
        )

    monkeypatch.setattr(
        model_service.httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(responder), **kwargs
        ),
    )
    result = client.post(
        PREFIX + "/hybrid-reasoning/runs",
        headers=headers,
        json={"task": "TC4叶盘加工", "mode": "external"},
    )
    assert result.status_code == 201
    assert result.json()["service_metadata"]["model"] == "test-model-v1"

    def invalid_reference(request):
        result = {
            "candidates": [
                {
                    "name": "无效引用",
                    "description": "测试",
                    "parameters": {},
                    "evidence_ids": ["D:missing"],
                    "actions": [],
                }
            ]
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(result)}}]}
        )

    monkeypatch.setattr(
        model_service.httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(invalid_reference), **kwargs
        ),
    )
    assert (
        client.post(
            PREFIX + "/hybrid-reasoning/runs",
            headers=headers,
            json={"task": "TC4叶盘加工", "mode": "external"},
        ).status_code
        == 502
    )


def test_engineering_adapter_full_state_sequence(client, headers, monkeypatch):
    geometry = client.post(
        PREFIX + "/platform/files",
        headers=headers,
        files={
            "file": (
                "fixture.step",
                b"ISO-10303-21; END-ISO-10303-21;",
                "application/octet-stream",
            )
        },
    ).json()
    resource = next(
        r
        for r in client.get(PREFIX + "/platform/resources", headers=headers).json()
        if r["capabilities"].get("max_rpm", 0) >= 3200
    )
    project = client.post(
        PREFIX + "/blisk-cam/projects",
        headers=headers,
        json={
            "name": "工程适配器测试",
            "geometry_file_id": geometry["id"],
            "resource_id": resource["id"],
        },
    ).json()
    path = PREFIX + "/blisk-cam/projects/" + project["id"]
    assert client.post(path + "/plan", headers=headers).status_code == 200
    algorithm = client.post(
        path + "/algorithm",
        headers=headers,
        json={"mode": "local", "engagement_width_mm": 1},
    )
    assert algorithm.status_code == 200
    candidates = algorithm.json()["execution"]["algorithm"]["candidates"]
    assert (
        candidates
        and candidates[0]["theoretical_removal_mm3_min"]
        >= candidates[-1]["theoretical_removal_mm3_min"]
    )
    assert (
        client.post(
            path + "/simulate", headers=headers, json={"mode": "external"}
        ).status_code
        == 409
    )

    def engineering_fixture(operation, payload):
        return {
            "input_digest": payload["input_digest"],
            "success": True,
            "software_version": "fixture-1",
            "artifact_id": "fixture-toolpath",
            "collision_free": True,
            "constraint_passed": True,
            "program": "TEST-PROGRAM-NOT-FOR-MACHINING",
            "accepted": True,
            "receipt_id": "fixture-receipt",
        }

    monkeypatch.setattr(metaalgorithm, "call_engineering", engineering_fixture)
    monkeypatch.setattr(workflow, "call_engineering", engineering_fixture)
    assert client.post(path + "/toolpath", headers=headers).status_code == 200
    assert (
        client.post(
            path + "/simulate", headers=headers, json={"mode": "external"}
        ).status_code
        == 200
    )
    assert client.post(path + "/approve", headers=headers).status_code == 200
    assert (
        client.post(path + "/dispatch", headers=headers).json()["status"]
        == "dispatched"
    )
    feedback = client.post(
        path + "/feedback",
        headers=headers,
        json={
            "operator": "测试人员",
            "accepted": True,
            "notes": "测试夹具返回，不代表真实制造结果",
        },
    )
    assert feedback.json()["status"] == "completed"


def test_invalid_engineering_response_is_rejected(client, headers, monkeypatch):
    from app.modules.blisk_cam.adapters.engineering_service import call_engineering
    from fastapi import HTTPException
    import pytest

    monkeypatch.setenv("CAM_SERVICE_URL", "http://engineering.example.test")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={"success": True, "input_digest": "stale"},
            request=httpx.Request("POST", "http://engineering.example.test/simulate"),
        ),
    )
    with pytest.raises(HTTPException) as error:
        call_engineering("simulate", {"input_digest": "current"})
    assert error.value.status_code == 502
