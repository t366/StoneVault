# backend/app 模块

后端 Sanic 服务，包含配置加载、应用入口与各业务模块。当前已实现配置与应用骨架，业务模块为规划占位。

## 结构

```
app/
├── __init__.py
├── config.py           # 配置加载（热区/冷区路径、端口、并发上限）
├── database.py         # SQLite 连接管理（WAL、外键）
├── schema.py           # 表结构与版本化 DDL
├── repositories.py     # 各表 CRUD 仓储类
├── server.py           # Sanic 应用创建与健康检查端点
├── backup_engine/      # 备份引擎（规划）
├── scheduler/          # 任务调度器（规划）
├── indexer/            # 文件索引（规划）
├── query_service/      # 查询服务（规划）
├── preview_service/    # 在线预览（规划）
├── transcode_worker/   # 音视频转码（规划）
├── ai_indexer/         # AI 深度索引（规划）
├── wake_manager/       # HDD 唤醒管理（规划）
├── auth/               # 管理员认证（规划）
└── api/                # REST API 蓝图（规划）
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `config.py` | 集中配置，支持 `STONEVAULT_*` 环境变量覆盖 |
| `database.py` | `Database` 类，WAL 模式与版本化初始化 |
| `schema.py` | `SCHEMA_SQL` 与 `SCHEMA_VERSION`，含 FTS5 外部内容表 |
| `repositories.py` | `TaskRepository` 等 6 个仓储类，`FileIndexRepository` 负责 FTS5 同步 |
| `server.py` | `create_app()` 工厂函数与 `GET /api/health` |

## 依赖

**本模块依赖**:
- 外部包：sanic、sanic-ext

**依赖本模块的**:
- `../tests/` - 冒烟测试
- `start.sh` - 启动入口

## 测试

`backend/tests/` 使用 pytest 与 sanic-testing，运行方式：

```bash
cd backend && python3 -m pytest
```
