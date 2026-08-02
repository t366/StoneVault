# StoneVault（磐石 Vault）文档

本仓库实现基于 RK3566 的内网智能备份中枢，采用"SSD 热区 + HDD 冷区"双存储架构，提供多终端自动备份、在线预览、多维度查询与源文件按需恢复。本文档面向维护与开发人员，描述当前代码实现与开发流程。

**快速链接**: [架构](./ARCHITECTURE.md) | [接口](./INTERFACES.md) | [开发者指南](./DEVELOPER_GUIDE.md)

---

## 核心文档

### [架构](./ARCHITECTURE.md)
系统设计、技术栈、目录结构与当前开发状态。从这里开始了解系统如何运作。

### [接口](./INTERFACES.md)
已实现的 HTTP 接口、前端代理配置与规划中的数据库 Schema。

### [开发者指南](./DEVELOPER_GUIDE.md)
环境搭建、开发工作流、编码规范与常见任务。贡献者必读。

---

## 模块

| 模块 | 描述 | README |
|------|------|--------|
| `backend/app/` | Sanic 后端服务（配置、入口与业务模块） | [README](./模块/backend-app.md) |
| `frontend/` | Vue3 + Element Plus 管理界面 | [README](./模块/frontend.md) |

---

## 核心概念

理解这些领域概念有助于导航代码库：

| 概念 | 描述 |
|------|------|
| [双存储引擎](./专有概念/双存储引擎.md) | SSD 热区与 HDD 冷区的分层存储模型 |
| [备份任务](./专有概念/备份任务.md) | 备份配置、快照与索引的记录模型 |

---

## 入门指南

### 项目新人？

按此路径学习：
1. **[架构](./ARCHITECTURE.md)** - 了解全局
2. **[核心概念](#核心概念)** - 学习领域术语
3. **[开发者指南](./DEVELOPER_GUIDE.md)** - 搭建环境
4. **[接口](./INTERFACES.md)** - 探索公开 API

---

## 快速参考

### 命令

```bash
./start.sh                    # 一键启动前后端
cd backend && python3 -m pytest   # 运行后端测试
cd frontend && npm run build      # 前端构建
```

### 重要文件

| 文件 | 目的 |
|------|------|
| `backend/app/config.py` | 后端配置（路径、端口、并发上限） |
| `backend/app/server.py` | Sanic 应用入口 |
| `frontend/vite.config.js` | Vite 配置（代理与 allowedHosts） |
| `start.sh` | 前后端启动脚本 |
| `.monkeycode/specs/rk3566-intranet-backup/` | 需求/设计/实施计划 |
