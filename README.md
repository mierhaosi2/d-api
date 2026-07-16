# d-api

基于 FastAPI + SQLAlchemy (async) + MySQL 的后端服务。

## 技术栈

- **FastAPI** — Web 框架
- **SQLAlchemy 2.0** — ORM（异步）
- **aiomysql** — MySQL 异步驱动
- **Alembic** — 数据库迁移
- **Pydantic Settings** — 配置管理
- **Loguru** — 日志
- **uv** — 包管理

## 快速启动

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env 填写数据库连接信息

# 2. 激活虚拟环境
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# 3. 启动服务
uvicorn main:app --reload --port 8080
```

访问 `http://localhost:8080/docs` 查看 Swagger UI。

## 目录结构

```
d-api/
├── .env                        # 环境变量（不提交 git）
├── .env.example                # 示例配置
├── main.py                     # 入口
└── app/
    ├── core/
    │   └── config.py           # 读取 .env 配置
    ├── db/
    │   ├── base_class.py       # ORM 基类
    │   ├── session.py          # 数据库引擎 & Session
    │   └── dependencies.py     # FastAPI 依赖注入
    ├── api/
    │   ├── router.py           # 路由汇总
    │   └── endpoints/          # 各业务路由
    ├── models/                 # SQLAlchemy 模型
    ├── schemas/                # Pydantic 请求/响应模型
    ├── repositories/           # 数据库操作层
    └── services/               # 业务逻辑层
```

## 数据库迁移（Alembic）

```bash
# 初始化（首次）
alembic init alembic

# 生成迁移文件
alembic revision --autogenerate -m "init"

# 执行迁移
alembic upgrade head
```
