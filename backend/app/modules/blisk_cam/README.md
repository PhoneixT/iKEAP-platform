# 叶盘CAM工作流

工艺规划、元算法调用、刀路生成、仿真验证、程序审核、分发与加工反馈。

此目录包含该模块的接口、数据模型和应用服务；外部集成通过adapters隔离。当前能力与接入边界见项目docs/运行与接口接入说明.md。

- api：路由入口。
- schemas：请求响应结构。
- models：持久化模型。
- repositories：数据访问。
- services：应用服务。
- domain：领域规则。
- adapters：外部集成。
- tasks：异步任务。

完整范围见项目 docs/软件功能模块大纲.md。
