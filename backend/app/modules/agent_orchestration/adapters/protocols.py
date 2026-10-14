import json
from uuid import uuid4
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import PUBLIC_URL, CORS_ORIGINS
from app.core.security import current_user
from app.infrastructure.database import get_db
from app.modules.knowledge_graph.schemas.contracts import SearchInput
from app.modules.knowledge_graph.services.retrieval import retrieve
from app.modules.constraint_validation.schemas.contracts import ValidationInput
from app.modules.constraint_validation.services.engine import evaluate
from app.modules.platform.models.entities import Resource, Job
from app.modules.agent_orchestration.models.entities import Workflow
from app.modules.agent_orchestration.services.executor import (
    submit,
    run_job,
    append_event,
)
from app.shared.services import listing, require

router = APIRouter(tags=["协议接口"])


def rpc_error(identifier, code, message):
    return {
        "jsonrpc": "2.0",
        "id": identifier,
        "error": {"code": code, "message": message},
    }


@router.api_route("/mcp", methods=["GET", "DELETE"])
def unsupported_mcp_transport():
    return Response(status_code=405)


@router.post("/mcp")
async def mcp(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    origin = request.headers.get("origin")
    if origin and origin not in CORS_ORIGINS:
        raise HTTPException(403, "Origin不在允许列表")
    if int(request.headers.get("content-length", "0")) > 1_000_000:
        raise HTTPException(413, "请求过大")
    try:
        body = await request.json()
    except ValueError:
        return rpc_error(None, -32700, "Parse error")
    if (
        not isinstance(body, dict)
        or body.get("jsonrpc") != "2.0"
        or not isinstance(body.get("method"), str)
    ):
        return rpc_error(None, -32600, "Invalid Request")
    identifier, method = body.get("id"), body["method"]
    if method.startswith("notifications/"):
        return Response(status_code=202)
    params = body.get("params") or {}
    if not isinstance(params, dict):
        return rpc_error(identifier, -32602, "Invalid params")
    if (
        method != "initialize"
        and request.headers.get("mcp-protocol-version", "2025-06-18") != "2025-06-18"
    ):
        raise HTTPException(400, "不支持的MCP协议版本")
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "iKEAP-platform", "version": "1.0.0"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "knowledge_search",
                        "description": "检索工业知识和来源证据",
                        "inputSchema": SearchInput.model_json_schema(),
                    },
                    {
                        "name": "constraints_validate",
                        "description": "执行工业参数和资源能力验证",
                        "inputSchema": ValidationInput.model_json_schema(),
                    },
                    {
                        "name": "resources_list",
                        "description": "查询平台登记资源",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        },
                    },
                ]
            }
        elif method == "tools/call":
            name, arguments = params.get("name"), params.get("arguments", {})
            if name == "knowledge_search":
                output = retrieve(
                    db, **SearchInput.model_validate(arguments).model_dump()
                )
            elif name == "constraints_validate":
                if user.role == "viewer":
                    raise HTTPException(403, "需要写入权限")
                output = evaluate(
                    db, **ValidationInput.model_validate(arguments).model_dump()
                )
                db.commit()
            elif name == "resources_list":
                output = {"resources": listing(db, Resource)}
            else:
                return rpc_error(identifier, -32602, "Unknown tool")
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(output, ensure_ascii=False)}
                ],
                "isError": False,
            }
        else:
            return rpc_error(identifier, -32601, "Method not found")
    except (ValueError, HTTPException) as error:
        result = {
            "content": [
                {
                    "type": "text",
                    "text": str(error.detail)
                    if isinstance(error, HTTPException)
                    else str(error),
                }
            ],
            "isError": True,
        }
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


@router.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "name": "iKEAP Industrial Task Agent",
        "description": "工业知识检索与约束验证任务",
        "url": PUBLIC_URL + "/a2a",
        "version": "1.0.0",
        "protocolVersion": "0.3.0",
        "preferredTransport": "JSONRPC",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
        "security": [{"bearer": []}],
        "skills": [
            {
                "id": "industrial-task",
                "name": "工业任务处理",
                "description": "通过已发布流程组织知识检索和验证",
                "tags": ["knowledge", "validation"],
            }
        ],
    }


def a2a_task(job):
    state = {
        "submitted": "submitted",
        "running": "working",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "canceled",
    }.get(job.status, "unknown")
    result = {
        "id": job.id,
        "contextId": job.id,
        "status": {"state": state, "timestamp": job.updated_at.isoformat() + "Z"},
        "kind": "task",
    }
    if job.result:
        result["artifacts"] = [
            {
                "artifactId": job.id + "-result",
                "name": "workflow-result",
                "parts": [{"kind": "data", "data": job.result}],
            }
        ]
    if job.error:
        result["status"]["message"] = {
            "role": "agent",
            "messageId": str(uuid4()),
            "parts": [{"kind": "text", "text": job.error}],
            "kind": "message",
        }
    return result


@router.post("/a2a")
async def a2a(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    try:
        body = await request.json()
    except ValueError:
        return rpc_error(None, -32700, "Parse error")
    if (
        not isinstance(body, dict)
        or body.get("jsonrpc") != "2.0"
        or not isinstance(body.get("params", {}), dict)
    ):
        return rpc_error(None, -32600, "Invalid Request")
    identifier, params = body.get("id"), body.get("params", {})
    method = body.get("method")
    try:
        if method == "message/send":
            if user.role == "viewer":
                raise HTTPException(403, "需要任务提交权限")
            message = params.get("message") or {}
            if (
                not isinstance(message, dict)
                or not message.get("messageId")
                or message.get("role") != "user"
            ):
                return rpc_error(identifier, -32602, "Invalid message")
            parts = message.get("parts", [])
            text = " ".join(
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("kind") == "text"
            )
            if not text or len(text) > 5000:
                return rpc_error(
                    identifier, -32602, "Text part required, maximum 5000 characters"
                )
            metadata = params.get("metadata") or {}
            workflow_id = metadata.get("workflow_id")
            workflow = (
                db.get(Workflow, workflow_id)
                if workflow_id
                else db.scalar(
                    select(Workflow).where(Workflow.name == "知识与验证协同流程")
                )
            )
            if not workflow:
                return rpc_error(identifier, -32602, "Workflow unavailable")
            context = {
                "query": text,
                "task": text,
                "domain": "cam",
                "parameters": {
                    "spindle_speed": 3200,
                    "feed_rate": 600,
                    "cut_depth": 0.3,
                    "tool_diameter": 8,
                },
                **metadata.get("context", {}),
            }
            job, created = submit(
                db, workflow.id, context, user, "a2a:" + message["messageId"]
            )
            if created:
                background.add_task(run_job, job.id)
            result = a2a_task(job)
        elif method in {"tasks/get", "tasks/cancel"}:
            job = require(db, Job, params.get("id"))
            if job.owner_id != user.id and user.role != "admin":
                raise HTTPException(403, "无权访问此任务")
            if method == "tasks/cancel":
                if job.status not in {"submitted", "running"}:
                    return rpc_error(identifier, -32002, "Task cannot be canceled")
                job.status = "cancelled"
                append_event(db, job.id, "A2A客户端取消任务")
                db.commit()
            result = a2a_task(job)
        else:
            return rpc_error(identifier, -32601, "Method not found")
        return {"jsonrpc": "2.0", "id": identifier, "result": result}
    except HTTPException as error:
        return rpc_error(
            identifier,
            -32001 if error.status_code == 404 else -32602,
            str(error.detail),
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        return rpc_error(identifier, -32602, "Invalid params")
