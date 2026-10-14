# iKEAP-platform

工业软件云平台。采用Vue 3、TypeScript、Vite、Element Plus前端，Python、FastAPI、SQLAlchemy后端，MySQL统一持久化业务数据、图谱、任务与报告。

## 功能

| 前后端模块目录 | 已实现能力 |
| --- | --- |
| `knowledge_graph` | 实体与关系维护、文档管理、原子导入、知识包导出、GraphRAG检索、多跳路径和来源证据 |
| `hybrid_reasoning` | 任务参数解析、上下文预览、证据注入、规则模板、外部模型调用、候选方案、约束检查与修正关联 |
| `constraint_validation` | 规则管理、单位换算、参数范围、语义类型与关系一致性、资源能力检查和验证报告 |
| `agent_orchestration` | Agent能力登记与发现、DAG流程定义、任务执行、输入引用、状态事件、取消、幂等、MCP和A2A接口 |
| `blisk_cam` | 工艺规划、参数比选、元算法接口、几何文件关联、刀路与仿真接口、审核、程序分发和执行反馈 |
| `cnc_phm` | 设备台账、时序采样、异常事件、故障候选分析、规则检查、RUL趋势估计、维护工单与反馈 |
| `platform` | 工作台、管理员/工程师/查看者权限、账户创建、资源档案、文件上传下载、服务配置状态与操作审计 |

规则模板、示例知识与采样均有演示标识。真实模型和工程软件通过适配器接入；缺少配置时返回明确错误。演示仿真不能进入工程审核或程序分发。

## 开发环境

- Python 3.11及以上；本地验证使用3.13。
- Node.js 22.12及以上；可通过 `-NodeExecutable` 指定Node路径。
- MySQL 5.7.44或8.x；本地验证使用5.7.44。

### 安装

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
```

修改 `.env` 中的数据库URL、随机 `SECRET_KEY`、管理员用户名与密码。管理员初始密码至少12位，密钥至少32位。

```powershell
cd ..\frontend
npm ci
cd ..
```

### 初始化MySQL

由数据库管理员先执行 `deploy/mysql/00_create_database.sql` 并为应用账户授权到项目库。然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-database.ps1 -Demo
```

脚本执行Alembic迁移、初始化管理员及示例数据；不需要示例数据时省略 `-Demo`。建表SQL另见 `deploy/mysql/01_schema.sql`，两种建表方式不要混用。完整说明见 [MySQL脚本](deploy/mysql/README.md)。

### 启动与停止

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1
```

- 页面：<http://127.0.0.1:5173>
- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- 初始登录信息：`backend/.env` 的 `ADMIN_USERNAME` 与 `ADMIN_PASSWORD`。
- 本地日志：`work/`。程序后台启动，不额外打开终端窗口。

也可分别在两个终端运行：后端目录执行 `.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`；前端目录执行 `npm run dev`。

## 检查

```powershell
cd frontend
npm run build
cd ..\backend
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m alembic check
```

MySQL测试必须使用名称含 `_test_` 的独立数据库，并配置 `IKEAP_TEST_DATABASE_URL` 或 `backend/.env.test`；测试会重建该测试库的表。未配置时使用临时SQLite文件执行通用业务测试，运行环境仍默认MySQL。

## 文档

- [软件功能模块大纲](docs/软件功能模块大纲.md)：产品规划。
- [工程目录与开发约定](docs/工程目录与开发约定.md)：模块边界。
- [运行与接口接入说明](docs/运行与接口接入说明.md)：使用步骤、服务协议和当前边界。
- [验证记录](docs/验证记录.md)：测试覆盖与验证环境。
- [容器部署](deploy/README.md)：独立容器部署配置。

当前执行器面向单进程本地部署，依赖图按拓扑顺序执行，不提供跨进程分布式调度。项目空间目前为共享空间，权限按角色控制。生产扩展所需的组织隔离、分布式队列和专业仿真/寿命模型需结合现场系统部署。
