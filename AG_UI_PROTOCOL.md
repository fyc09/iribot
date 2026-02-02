# AG-UI Protocol Integration

This application now uses the **AG-UI (Agent-User Interaction) Protocol** for handling chat messages.

## 架构

### 后端 (Backend)

**文件**: `backend/ag_ui_protocol.py`

后端实现了 AG-UI 协议的数据结构和转换工具：

```python
# 核心类
- AGUIMessage: 符合 AG-UI 协议的消息类
- ToolCall: 工具函数调用
- BinaryContent: 二进制内容（图片、文件等）
- AGUIEventEncoder: 编码/解码 AG-UI 事件
```

**API 端点**:
- `GET /api/sessions/{session_id}` - 返回 AG-UI 格式的会话和消息

### 前端 (Frontend)

**核心文件**:
- `src/types.ts` - AG-UI 协议兼容的类型定义
- `src/components/ChatMessagesAGUI.vue` - 使用 TDesign Chat 和 AG-UI 协议的消息显示组件
- `src/components/ChatWindow.vue` - 更新为使用 ChatMessagesAGUI

## AG-UI 协议消息格式

```typescript
interface AGUIMessage {
  id: string                      // 消息唯一标识
  role: string                    // "user" | "assistant" | "system"
  content?: string                // 消息内容（支持 Markdown）
  name?: string                   // 发送者名称
  tool_calls?: ToolCall[]         // 工具调用列表
  tool_results?: ToolResult[]     // 工具执行结果
  binary_content?: BinaryContent[] // 二进制内容（图片、文件等）
  metadata?: {
    timestamp?: string | Date     // 消息时间戳
    [key: string]: any            // 其他自定义元数据
  }
}
```

## 功能

### 已实现
✅ AG-UI 协议消息格式化
✅ Markdown 渲染
✅ 二进制内容支持（图片、文件）
✅ 工具调用显示
✅ 工具结果显示
✅ TDesign Chat 集成
✅ 暗色主题

### 可扩展
- 添加新的消息类型
- 扩展 binary_content 支持
- 自定义 metadata 字段
- 工具调用的动态执行

## 使用示例

### 后端：创建 AG-UI 消息

```python
from ag_ui_protocol import AGUIMessage, BinaryContent

# 创建文本消息
message = AGUIMessage(
    id="msg_123",
    role="user",
    content="Hello, assistant!"
)

# 创建带图片的消息
binary_content = BinaryContent(
    type="binary",
    mimeType="image/jpeg",
    data=base64_image_data
)

message_with_image = AGUIMessage(
    id="msg_124",
    role="user",
    content="Here's an image",
    binary_content=[binary_content]
)

# 转换为 dict 发送给前端
response_data = message_with_image.to_dict()
```

### 前端：处理 AG-UI 消息

```typescript
// 在 ChatMessagesAGUI 组件中自动处理
// 支持：
// - Markdown 渲染
// - 图片显示
// - 工具调用和结果
// - 自定义 metadata
```

## 集成步骤

### 1. 后端集成
```bash
cd backend
# ag_ui_protocol.py 已包含在项目中
```

### 2. 前端依赖
```bash
cd frontend
npm install @ag-ui/core @ag-ui/client @ag-ui/encoder marked
```

### 3. 更新 API 响应
修改后端的获取会话端点以返回 AG-UI 格式的消息。

### 4. 更新前端组件
使用 ChatMessagesAGUI 替代原来的 ChatMessages。

## 工具集成

工具调用通过 AG-UI 的 `tool_calls` 字段传递：

```typescript
interface ToolCall {
  id: string  // 唯一调用 ID
  type: "function"
  function: {
    name: string      // 工具名称
    arguments: string // JSON 字符串参数
  }
}
```

工具结果通过 `tool_results` 返回。

## 扩展指南

### 添加新的内容类型

修改 `ag_ui_protocol.py`：

```python
@dataclass
class CustomContent:
    type: Literal["custom"] = "custom"
    # 自定义字段...
    
    def to_dict(self):
        return asdict(self)
```

### 自定义 metadata

在消息中添加 metadata：

```python
message = AGUIMessage(
    ...
    metadata={
        "timestamp": datetime.now().isoformat(),
        "custom_field": "custom_value",
        "user_id": "user_123"
    }
)
```

## 参考资源

- [AG-UI Core 文档](https://www.npmjs.com/package/@ag-ui/core)
- [TDesign Chat 组件](https://tdesign.tencent.com/)
- [Marked.js Markdown 渲染](https://marked.js.org/)
