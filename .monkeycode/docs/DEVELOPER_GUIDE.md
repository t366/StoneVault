# StoneVault（磐石 Vault）开发者指南

## 项目目的

StoneVault 是一个运行于 RK3566 嵌入式设备的内网智能备份中枢，将多终端文件自动备份至外接机械硬盘（冷区），并在固态存储（热区）维护索引与缓存副本，提供在线预览、多维查询与按需恢复能力。

**核心职责**:
- 多任务自动备份（全量/增量）与定时调度
- 双存储（SSD 热区 + HDD 冷区）分层写入
- 在线预览、全文检索与 AI 内容识别（规划）
- 管理员认证与系统状态可观测

## 环境搭建

### 前置条件

- Python >= 3.11
- Node.js >= 22
- npm >= 10

### 安装

```bash
git clone https://github.com/t366/StoneVault.git
cd StoneVault

# 后端依赖
pip install --break-system-packages -r backend/requirements.txt

# 前端依赖
cd frontend
npm install
```

### 环境变量

后端配置通过环境变量覆盖（前缀 `STONEVAULT_`），默认值见 `backend/app/config.py`：

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `STONEVAULT_HOST` | `0.0.0.0` | 后端监听地址 |
| `STONEVAULT_PORT` | `8000` | 后端监听端口 |
| `STONEVAULT_DATA_DIR` | `/var/lib/stonevault` | 热区数据目录（数据库/缓存/缩略图） |
| `STONEVAULT_HDD_MOUNT` | `/mnt/backup` | 冷区机械硬盘挂载路径 |
| `STONEVAULT_SESSION_TTL` | `86400` | 会话有效期（秒） |
| `STONEVAULT_AI_CONCURRENCY` | `2` | AI 任务并发进程数上限 |
| `STONEVAULT_TRANSCODE_CONCURRENCY` | `1` | 转码进程并发上限 |
| `STONEVAULT_WAKE_TIMEOUT` | `30` | HDD 唤醒超时（秒） |
| `STONEVAULT_WAKE_DEBOUNCE` | `10` | 唤醒防抖窗口（秒） |

### 运行

```bash
# 一键启动前后端
./start.sh

# 或分别启动
cd backend && python3 -m app.server
cd frontend && npm run dev
```

### 测试

```bash
cd backend
python3 -m pytest
```

## 开发工作流

### 质量工具

| 工具 | 命令 | 目的 |
|------|------|------|
| pytest | `python3 -m pytest`（backend/ 下） | 后端单元/集成测试 |
| vite build | `npm run build`（frontend/ 下） | 前端编译验证 |

### 分支策略

- `master` - 主干分支，直接推送开发成果
- 规格文档位于 `.monkeycode/specs/rk3566-intranet-backup/`，开发以 `tasklist.md` 为准

### 任务执行规则

1. 实现任务前阅读 `design.md` 与 `tasklist.md`
2. 每完成一个任务在 `tasklist.md` 中标记 `[x]`
3. 核心功能先实现，测试类任务按 `*` 标记可选执行

## 常见任务

### 运行后端测试

```bash
cd backend
python3 -m pytest -q
```

### 新增后端模块

1. 在 `backend/app/` 下创建模块目录与 `__init__.py`
2. 实现功能并在 `server.py` 中注册蓝图
3. 在 `backend/tests/` 添加对应测试

### 新增前端页面

1. 在 `frontend/src/` 创建 Vue 组件
2. 配置 Vue Router 路由
3. 通过 `/api` 相对路径调用后端接口（Vite 已配置代理）

## 编码规范

### 文件组织

- 后端按模块分目录，每个模块包含 `__init__.py`
- 测试位于 `backend/tests/`，与源码目录对应

### 命名

| 类型 | 约定 | 示例 |
|------|------|------|
| Python 模块 | snake_case | `backup_engine/` |
| Python 函数/变量 | snake_case | `create_app` |
| Python 类 | PascalCase | `Config` |
| 前端文件 | kebab-case | `vite.config.js` |
| 前端组件 | PascalCase | `App.vue` |

### 错误处理

- 数据库与业务层使用自定义异常并统一在 API 层转换为 HTTP 响应
- 冷区离线、磁盘空间不足等场景返回友好提示而非静默失败

### 安全

- 管理员密码使用 PBKDF2-SHA256 带盐单向散列存储（`backend/app/auth/passwords.py`）
- 会话令牌为 HMAC-SHA256 签名，含过期时间（`backend/app/auth/sessions.py`）
- 除 `GET /api/health` 与 `POST /api/auth/login` 外，`/api/*` 接口均需 `Bearer` 令牌认证
- 禁止在代码与配置中提交密钥，API token 使用占位符
