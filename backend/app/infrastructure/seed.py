import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.security import hash_password
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import (
    User,
    Resource,
    Entity,
    Relation,
    Document,
    Rule,
    Agent,
    Workflow,
    CamProject,
    Machine,
    Anomaly,
)


def initialize_admin(db):
    username = os.getenv("ADMIN_USERNAME", "admin")
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return user
    password = os.getenv("ADMIN_PASSWORD", "")
    if len(password) < 12 or password.startswith("REPLACE_"):
        raise ValueError("ADMIN_PASSWORD需配置为至少12位密码")
    user = User(
        username=username,
        display_name="平台管理员",
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(user)
    db.flush()
    return user


def seed_demo(db):
    if db.scalar(select(Entity).where(Entity.name == "TC4钛合金")):
        return
    source = "平台示例知识集 v1（演示资料）"
    specs = [
        ("TC4钛合金", "材料", "低导热材料，切削参数需结合刀具、装夹与冷却条件确认。"),
        ("整体叶盘", "零件", "叶片与轮毂一体结构，具有叶间狭窄通道。"),
        ("五轴加工中心", "设备", "多轴联动加工设备，需要校验行程与旋转轴边界。"),
        ("球头铣刀", "刀具", "用于曲面精加工，刀径与伸出量影响可达性。"),
        ("侧铣精加工", "工艺", "叶片表面加工策略，需检查干涉与过切。"),
        ("分层粗加工", "工艺", "逐层去除叶间材料，保留均匀余量。"),
        ("碰撞仿真", "验证", "使用真实几何、刀具和机床模型检查碰撞。"),
        ("主轴", "部件", "数控机床关键旋转部件，监测振动与温度。"),
        ("轴承磨损", "故障", "可能引起振动与温升，需结合频谱和现场检查确认。"),
        ("振动超限", "症状", "振动指标超出配置阈值，需要复核传感器与运行工况。"),
        ("温升异常", "症状", "温度高于阈值，需检查冷却和润滑。"),
        ("润滑不足", "故障", "润滑状态异常可能影响轴承温度与振动。"),
        ("润滑检查", "维护", "核对润滑供给、油品和维护记录。"),
        ("轴承检查", "维护", "检查轴承状态、装配与特征频率。"),
    ]
    entities = {}
    for name, kind, description in specs:
        entity = Entity(
            name=name,
            kind=kind,
            description=description,
            source=source,
            aliases=[],
            properties={},
        )
        db.add(entity)
        db.flush()
        entities[name] = entity
    for a, relation, b in [
        ("整体叶盘", "材料", "TC4钛合金"),
        ("整体叶盘", "使用设备", "五轴加工中心"),
        ("整体叶盘", "粗加工策略", "分层粗加工"),
        ("整体叶盘", "精加工策略", "侧铣精加工"),
        ("侧铣精加工", "使用刀具", "球头铣刀"),
        ("侧铣精加工", "需要验证", "碰撞仿真"),
        ("五轴加工中心", "包含部件", "主轴"),
        ("主轴", "可能故障", "轴承磨损"),
        ("轴承磨损", "表现为", "振动超限"),
        ("轴承磨损", "表现为", "温升异常"),
        ("润滑不足", "表现为", "温升异常"),
        ("润滑不足", "表现为", "振动超限"),
        ("润滑不足", "维护动作", "润滑检查"),
        ("轴承磨损", "维护动作", "轴承检查"),
    ]:
        db.add(
            Relation(
                source_id=entities[a].id,
                target_id=entities[b].id,
                kind=relation,
                source=source,
                properties={},
            )
        )
    for title, content, names in [
        (
            "TC4叶盘工艺示例",
            "TC4钛合金整体叶盘可采用分层粗加工、半精加工与五轴侧铣精加工的工序组合。刀具直径、进给、转速和切深应经约束检查及真实仿真确定。示例参数不能直接作为生产依据。",
            ["TC4钛合金", "整体叶盘", "侧铣精加工"],
        ),
        (
            "叶盘工程验证示例",
            "刀路生成后应检查刀具、夹具与机床的碰撞和干涉，并确认轴行程、过切与残留。参数检查通过不等于几何仿真通过。",
            ["碰撞仿真", "球头铣刀"],
        ),
        (
            "主轴异常诊断示例",
            "主轴振动超限并伴随温升时，可将轴承磨损、润滑不足和传感器安装问题列为候选原因。需要频谱、润滑记录及现场检查进行确认。",
            ["主轴", "振动超限", "温升异常", "轴承磨损"],
        ),
        (
            "维护决策示例",
            "维护前确认工况与测量质量，核查润滑供给并检查轴承。维护工单记录实际故障原因、采取措施和复测结果，结果经审核后再修订知识。",
            ["润滑检查", "轴承检查"],
        ),
    ]:
        db.add(
            Document(
                title=title,
                content=content,
                source=source,
                entity_ids=[entities[n].id for n in names],
            )
        )
    resource = Resource(
        name="五轴加工中心 · 示例资源",
        kind="machine",
        capabilities={"max_rpm": 12000, "max_feed": 8000, "max_power": 30},
        description="用于流程验证的资源档案，未连接现场设备。",
    )
    db.add(resource)
    db.flush()
    for name, scope, field, low, high, unit in [
        ("主轴转速范围", "cam", "spindle_speed", 500, 10000, "rpm"),
        ("进给速度范围", "cam", "feed_rate", 50, 3000, "mm/min"),
        ("切削深度范围", "cam", "cut_depth", 0.05, 1.5, "mm"),
        ("刀具直径范围", "cam", "tool_diameter", 2, 20, "mm"),
        ("振动测量有效性", "phm", "vibration_rms", 0, 100, "mm/s"),
        ("温度测量有效性", "phm", "temperature", -20, 150, "°C"),
    ]:
        db.add(
            Rule(
                name=name,
                scope=scope,
                field=field,
                operator="between",
                expected={"min": low, "max": high},
                unit=unit,
                severity="hard",
            )
        )
    for name, description, capabilities in [
        ("知识检索Agent", "组织图谱、路径和资料证据", ["knowledge.search"]),
        ("验证Agent", "检查工艺参数与资源能力", ["constraints.validate"]),
        ("工艺规划Agent", "组织叶盘工序和候选参数", ["cam.plan", "reasoning.generate"]),
        ("设备诊断Agent", "组织故障候选与维护检查项", ["phm.diagnose"]),
    ]:
        db.add(Agent(name=name, description=description, capabilities=capabilities))
    db.add(
        Workflow(
            name="知识与验证协同流程",
            description="检索证据后执行候选方案生成和约束验证。",
            nodes=[
                {
                    "id": "search",
                    "action": "knowledge.search",
                    "depends_on": [],
                    "input": {"query": {"$ref": "context.query"}},
                },
                {
                    "id": "reasoning",
                    "action": "reasoning.generate",
                    "depends_on": ["search"],
                    "input": {
                        "task": {"$ref": "context.task"},
                        "domain": {"$ref": "context.domain"},
                        "parameters": {"$ref": "context.parameters"},
                        "mode": "template",
                    },
                },
                {
                    "id": "validation",
                    "action": "constraints.validate",
                    "depends_on": ["reasoning"],
                    "input": {
                        "scope": {"$ref": "context.domain"},
                        "parameters": {"$ref": "context.parameters"},
                    },
                },
            ],
        )
    )
    db.add(
        CamProject(
            name="TC4整体叶盘 · 流程示例",
            material="TC4",
            description="工艺、验证与工程服务接入示例。",
            resource_id=resource.id,
            parameters={
                "spindle_speed": 3200,
                "feed_rate": 600,
                "cut_depth": 0.3,
                "tool_diameter": 8,
            },
        )
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    telemetry = [
        {
            "time": (now - timedelta(hours=23 - i)).isoformat().replace("+00:00", "Z"),
            "vibration_rms": round(2.4 + i * 0.13 + (0.04 if i % 3 else -0.03), 2),
            "temperature": round(52 + i * 1.2, 1),
        }
        for i in range(24)
    ]
    machine = Machine(
        name="五轴加工中心主轴 · 示例",
        code="DEMO-CNC-001",
        component="主轴",
        thresholds={"vibration_rms": 4.5, "temperature": 75},
        telemetry=telemetry,
    )
    db.add(machine)
    db.flush()
    db.add(
        Anomaly(
            machine_id=machine.id,
            title="示例事件：主轴振动与温度超限",
            severity="high",
            measurements={**telemetry[-1], "thresholds": machine.thresholds},
        )
    )


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    arguments = parser.parse_args()
    with SessionLocal() as db:
        initialize_admin(db)
        if arguments.demo:
            seed_demo(db)
        db.commit()
    print("账户初始化完成" + ("；示例数据已就绪" if arguments.demo else ""))


if __name__ == "__main__":
    main()
