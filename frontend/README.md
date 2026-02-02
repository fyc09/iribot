# Frontend

简洁的 AI Agent 聊天界面，使用 Vite + Vue 3 构建，暗色主题。

## 技术栈

- **Vue 3** - Composition API
- **Vite** - 极速构建工具
- **Marked.js** - Markdown 渲染
- **TDesign** - UI 设计风格

## 快速启动

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 启动开发服务器
```bash
npm run dev
```

访问：http://localhost:5173

### 3. 构建生产版本
```bash
npm run build
npm run preview  # 预览构建结果
```

## 项目结构

```
frontend/
├── index.html          # 入口 HTML
├── package.json        # 依赖配置
├── vite.config.js      # Vite 配置（含代理）
└── src/
    ├── main.js         # 应用入口
    ├── App.vue         # 主组件
    └── style.css       # 暗色主题样式
```

## 功能特性

✅ **会话管理**
- 创建新会话
- 切换历史会话
- 自动保存对话

✅ **消息显示**
- Markdown 渲染
- 代码高亮
- 图片显示（binary_content）
- 工具调用显示

✅ **开发体验**
- 热模块替换（HMR）
- TypeScript 支持（可选）
- 暗色主题
- 响应式布局

## API 代理

Vite 配置了 API 代理，自动转发 `/api` 请求到后端：
```javascript
// vite.config.js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

前端代码中只需使用相对路径：
```javascript
fetch('/api/sessions')  // 自动代理到 http://localhost:8000/api/sessions
```

## 自定义

### 修改后端地址
编辑 `vite.config.js` 的 proxy.target。

### 修改主题色
编辑 `src/style.css` 的 `:root` 变量。

## 浏览器支持

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

