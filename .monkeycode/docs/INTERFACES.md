# StoneVault（磐石 Vault）接口文档

本文件记录当前已实现的接口。规划中的接口随开发进度逐步补充。

## HTTP API（后端）

### 认证机制

除公开端点外，`/api/*` 接口均需在请求头携带 `Authorization: Bearer <token>`。令牌为 HMAC-SHA256 签名（含过期时间），未认证或过期返回 401。公开端点：`GET /api/health`、`POST /api/auth/login`。

### GET /api/health

健康检查端点，验证服务可用性。

**响应 200**

```json
{
  "status": "ok",
  "service": "stonevault",
  "hdd_mounted": true
}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | 服务状态，固定为 `ok` |
| `service` | string | 服务标识，固定为 `stonevault` |
| `hdd_mounted` | boolean | 冷区挂载路径是否为绝对路径（占位判断） |

### POST /api/auth/login

管理员登录，签发会话令牌。

**请求体**

```json
{ "username": "admin", "password": "secret" }
```

**响应 200**

```json
{ "token": "<jwt-like-token>", "username": "admin" }
```

**错误响应**：401（凭据无效）。

### POST /api/auth/logout

注销当前会话（需认证）。返回 `{"ok": true}`。

## 前端配置接口

### Vite 开发代理

`frontend/vite.config.js` 将 `/api` 前缀请求代理至后端 `http://localhost:8000`，前端通过相对路径 `/api/...` 调用后端。

### 允许主机

开发服务器 `allowedHosts` 包含 `.monkeycode-ai.online`，支持该域名的在线预览访问。

## 数据库 Schema

数据库初始化见 `backend/app/schema.py`（版本化，`PRAGMA user_version` 控制迁移），连接管理见 `backend/app/database.py`（WAL 模式、外键约束）。

| 表 | 用途 |
|----|------|
| `tasks` | 备份任务配置（源路径、冷区相对路径、Cron、过滤规则、备份模式） |
| `snapshots` | 备份执行快照（状态、文件数、总字节） |
| `file_index` | 文件索引与双路径映射，含 FTS 内容源列（filename/body/ai_text） |
| `file_fts` | FTS5 全文检索虚拟表（外部内容表，`trigram` 分词器） |
| `metadata` | 扩展元数据（EXIF、视频时长等） |
| `admin_user` | 管理员账号（username + password_hash） |
| `ai_jobs` | AI 深度索引队列（类型、状态、优先级） |

数据访问层为 `backend/app/repositories.py` 中的仓储类：`TaskRepository`、`SnapshotRepository`、`FileIndexRepository`（含 FTS5 同步写入/更新/删除）、`MetadataRepository`、`AdminUserRepository`、`AiJobRepository`。

## 规划中的接口

见 `.monkeycode/specs/rk3566-intranet-backup/design.md` REST 接口清单，包括任务 CRUD、文件查询、在线预览、源文件下载、深度索引触发与系统状态等端点。
