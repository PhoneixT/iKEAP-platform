import os
import httpx
from fastapi import HTTPException


def call_engineering(operation, payload):
    url = os.getenv("CAM_SERVICE_URL", "").rstrip("/")
    if not url:
        raise HTTPException(503, "CAM_SERVICE_URL未配置")
    try:
        response = httpx.post(
            url + "/" + operation,
            json=payload,
            headers={"Authorization": "Bearer " + os.getenv("CAM_SERVICE_TOKEN", "")},
            timeout=60,
            follow_redirects=False,
        )
        response.raise_for_status()
        result = response.json()
        if (
            not isinstance(result, dict)
            or result.get("input_digest") != payload["input_digest"]
        ):
            raise ValueError("结果未关联当前输入版本")
        if result.get("success") is not True:
            raise ValueError("工程服务未返回成功状态")
        return result
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(502, f"工程服务结果不可用：{type(error).__name__}")
