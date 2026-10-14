import re


def parse_task(task, domain, supplied_parameters=None):
    patterns = {
        "spindle_speed": r"(?:转速|spindle_speed)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*(?:rpm|r/min|转/分)?",
        "feed_rate": r"(?:进给(?:速度)?|feed_rate)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*(?:mm/min)?",
        "cut_depth": r"(?:切深|切削深度|cut_depth)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?",
        "tool_diameter": r"(?:刀径|刀具直径|tool_diameter)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?",
        "vibration_rms": r"(?:振动(?:有效值)?|vibration_rms)\s*[:：=]?\s*(\d+(?:\.\d+)?)\s*(?:mm/s)?",
        "temperature": r"(?:温度|temperature)\s*[:：=]?\s*(-?\d+(?:\.\d+)?)\s*(?:°C|℃)?",
    }
    extracted = {}
    for field, pattern in patterns.items():
        match = re.search(pattern + r"(?![\d.A-Za-z/])", task, re.IGNORECASE)
        if match:
            extracted[field] = float(match.group(1))
    parameters = {**extracted, **(supplied_parameters or {})}
    return {
        "task": task,
        "domain": domain,
        "intent": "process_planning" if domain == "cam" else "fault_diagnosis",
        "parameters": parameters,
        "extracted_parameters": extracted,
        "deliverables": ["工艺候选方案", "检索证据", "参数验证报告"]
        if domain == "cam"
        else ["候选故障原因", "检查建议", "检索证据"],
        "required_capabilities": [
            "knowledge.search",
            "reasoning.generate",
            "constraints.validate",
        ],
        "parser_version": "industrial-pattern-v1",
        "needs_confirmation": ["材料、几何与装夹条件"]
        if domain == "cam"
        else ["运行工况与测量质量"],
    }
