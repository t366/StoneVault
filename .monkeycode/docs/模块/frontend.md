# frontend 模块

Vue 3 + Element Plus 前端管理界面骨架，通过 Vite 开发服务器访问，`/api` 请求反向代理至后端。

## 结构

```
frontend/
├── index.html           # 页面入口
├── package.json         # 依赖与脚本
├── vite.config.js       # Vite 配置（/api 代理、allowedHosts）
├── public/
└── src/
    ├── main.js          # 应用挂载（Element Plus 注册）
    └── App.vue          # 根组件（布局骨架）
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `vite.config.js` | 开发代理（`/api` → `http://localhost:8000`）与 `.monkeycode-ai.online` 允许主机 |
| `src/main.js` | 注册 Element Plus 并挂载应用 |
| `src/App.vue` | 顶部品牌栏与主内容区骨架 |

## 依赖

**本模块依赖**:
- 外部包：vue、element-plus、@element-plus/icons-vue、vue-router、vite、@vitejs/plugin-vue
- 后端服务：通过 `/api` 代理访问

## 脚本

```bash
npm run dev      # 启动开发服务器（5173）
npm run build    # 生产构建
```
