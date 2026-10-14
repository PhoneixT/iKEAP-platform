from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.modules.cnc_phm.models.entities import Machine, Anomaly
from app.modules.hybrid_reasoning.services.reasoning import run_reasoning
from app.shared.services import require


def ingest(db, machine_id, samples):
    machine = require(db, Machine, machine_id)
    combined = {item["time"]: item for item in machine.telemetry}
    for sample in samples:
        stamp = sample.time
        if stamp.tzinfo is None:
            raise HTTPException(422, "采样时间必须包含时区")
        time_key = stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        combined[time_key] = {
            "time": time_key,
            "vibration_rms": sample.vibration_rms,
            "temperature": sample.temperature,
        }
    machine.telemetry = sorted(combined.values(), key=lambda v: v["time"])[-10000:]
    latest = machine.telemetry[-1]
    exceeded = [
        field
        for field, threshold in machine.thresholds.items()
        if field in latest and latest[field] > threshold
    ]
    anomaly = None
    if exceeded:
        existing = db.scalar(
            select(Anomaly).where(
                Anomaly.machine_id == machine.id,
                Anomaly.measurements["time"].as_string() == latest["time"],
            )
        )
        if existing:
            return {
                "machine_id": machine.id,
                "sample_count": len(machine.telemetry),
                "anomaly": existing.as_dict(),
                "deduplicated": True,
            }
        anomaly = Anomaly(
            machine_id=machine.id,
            title=machine.name + "：" + "、".join(exceeded) + "超限",
            severity="high" if len(exceeded) > 1 else "medium",
            measurements={**latest, "thresholds": machine.thresholds},
        )
        db.add(anomaly)
        db.flush()
    return {
        "machine_id": machine.id,
        "sample_count": len(machine.telemetry),
        "anomaly": anomaly.as_dict() if anomaly else None,
    }


def diagnose(db, anomaly_id, mode="template"):
    anomaly = require(db, Anomaly, anomaly_id)
    if anomaly.status == "closed":
        raise HTTPException(409, "事件已关闭")
    machine = require(db, Machine, anomaly.machine_id)
    run = run_reasoning(
        db,
        f"{machine.component}振动温度异常，轴承故障和润滑状态检查",
        "phm",
        mode,
        {k: v for k, v in anomaly.measurements.items() if isinstance(v, (float, int))},
    )
    anomaly.diagnosis = {
        "reasoning_run_id": run["id"],
        "candidates": run["candidates"],
        "evidence": run["evidence"]["evidence"],
        "recommendation": "补充现场检查后确定故障原因；安排润滑、轴承和传感器检查。",
        "confirmed": False,
    }
    anomaly.status = "diagnosed"
    db.flush()
    return anomaly.as_dict()


def estimate_rul(db, machine_id, failure_threshold=7.1):
    machine = require(db, Machine, machine_id)
    points = machine.telemetry
    base = {
        "machine_id": machine.id,
        "method": "linear-trend-v1",
        "result_source": "趋势外推示例",
        "unit": "hours",
        "failure_threshold": failure_threshold,
        "sample_count": len(points),
        "validated_life_model": False,
    }
    if len(points) < 5:
        return {
            **base,
            "status": "insufficient_data",
            "remaining_hours": None,
            "reason": "至少需要5个不同时间的采样点",
        }
    stamps = [
        datetime.fromisoformat(p["time"].replace("Z", "+00:00")).timestamp()
        for p in points
    ]
    x = [(t - stamps[0]) / 3600 for t in stamps]
    y = [p["vibration_rms"] for p in points]
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    denominator = sum((v - mean_x) ** 2 for v in x)
    slope = (
        sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y)) / denominator
        if denominator
        else 0
    )
    intercept = mean_y - slope * mean_x
    fitted = [intercept + slope * v for v in x]
    total = sum((v - mean_y) ** 2 for v in y)
    r_squared = 1 - sum((a - b) ** 2 for a, b in zip(y, fitted)) / total if total else 0
    if y[-1] >= failure_threshold:
        return {
            **base,
            "status": "threshold_reached",
            "remaining_hours": 0,
            "as_of": points[-1]["time"],
            "r_squared": round(r_squared, 4),
        }
    if slope <= 0 or r_squared < 0.5:
        return {
            **base,
            "status": "not_predictable",
            "remaining_hours": None,
            "reason": "无稳定上升趋势",
            "r_squared": round(r_squared, 4),
        }
    remaining = (failure_threshold - fitted[-1]) / slope
    return {
        **base,
        "status": "estimated",
        "remaining_hours": round(max(0, remaining), 2),
        "as_of": points[-1]["time"],
        "slope_per_hour": round(slope, 6),
        "r_squared": round(r_squared, 4),
    }
