# MySQL脚本

支持MySQL 5.7.44及8.x；使用InnoDB、utf8mb4、JSON字段和外键。业务数据、知识图谱及任务记录统一存放在MySQL，无需另行安装图数据库。

## 推荐初始化方式

1. 使用数据库管理员账户执行 `00_create_database.sql`。
2. 为项目创建只授权到 `ikeap_platform.*` 的独立账户。
3. 配置 `backend/.env` 的 `DATABASE_URL`、`SECRET_KEY`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`。
4. 从项目根目录执行 `powershell -ExecutionPolicy Bypass -File scripts/init-database.ps1 -Demo`。

迁移脚本位于 `backend/migrations/versions/`。初始化脚本通过Alembic建表，随后创建管理员并导入示例知识、规则、资源、流程、CAM项目和PHM采样。`-Demo`可省略，省略时仅初始化管理员。

## SQL建表方式

也可在空库中按顺序执行 `00_create_database.sql` 和 `01_schema.sql`，之后进入backend目录执行 `.venv/Scripts/python -m alembic stamp head` 标记迁移版本，再从项目根目录运行 `backend/.venv/Scripts/python deploy/mysql/02_seed_demo.py`。

SQL建表方式和Alembic建表方式二选一。已有数据库升级使用 `alembic upgrade head`，不要重复执行初始建表SQL。

应用账户的Host需匹配数据库识别到的客户端地址。通过容器端口映射连接时，MySQL看到的客户端地址可能不是127.0.0.1；可由管理员执行 `SELECT USER()` 核对，再给对应Host授权。

密码只写入本地配置。URL中的特殊字符应进行URL编码；生产环境使用独立账号、强密码和受控网络访问。

## 测试

测试使用独立库，名称必须含 `_test_`。通过 `IKEAP_TEST_DATABASE_URL` 或本地 `backend/.env.test` 指定。测试会清理该独立测试库的表，禁止指向业务库。未指定MySQL测试库时使用临时SQLite文件运行通用业务测试。
