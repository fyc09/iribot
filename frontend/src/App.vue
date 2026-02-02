<template>
  <t-layout class="chat-layout">
    <ChatSidebar
      :sessions="sessions"
      :current-session-id="currentSessionId"
      @create-session="createSession"
      @select-session="selectSession"
      @delete-session="deleteSession"
    />
    <ChatContainer
      :messages="messages"
      :loading="loading"
      :tool-statuses="toolStatuses"
      @send="sendMessage"
      @stop="stopMessage"
      @refresh-tools="loadToolStatuses"
    />
  </t-layout>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useChat } from "@tdesign-vue-next/chat";
import { MessagePlugin } from "tdesign-vue-next";
import ChatSidebar from "./components/ChatSidebar.vue";
import ChatContainer from "./components/ChatContainer.vue";

const API_BASE = "http://localhost:8000/api";

// 状态管理
const sessions = ref([]);
const currentSessionId = ref(null);
const inputMessage = ref("");
const toolStatuses = ref([]);

// useChat Hook - 仅用于消息显示管理
const { chatEngine, messages, status } = useChat({
  defaultMessages: [],
});

const loading = ref(false);

async function loadSessions() {
  try {
    const response = await fetch(`${API_BASE}/sessions`);
    if (!response.ok) throw new Error("Failed to load sessions");
    sessions.value = await response.json();
    if (sessions.value.length > 0 && !currentSessionId.value) {
      await selectSession(sessions.value[0].id);
    }
  } catch (error) {
    MessagePlugin.error(`Failed to load sessions: ${error.message}`);
  }
}

async function loadToolStatuses() {
  try {
    const response = await fetch(`${API_BASE}/tools/status`);
    if (!response.ok) throw new Error("Failed to load tool status");
    toolStatuses.value = await response.json();
  } catch (error) {
    MessagePlugin.error(`Failed to load tool status: ${error.message}`);
  }
}

async function createSession() {
  try {
    const title = `Conversation ${new Date().toLocaleString("en-US", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })}`;
    const response = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) throw new Error("Failed to create session");
    const session = await response.json();
    sessions.value.unshift(session);
    await selectSession(session.id);
    MessagePlugin.success("Session created successfully");
  } catch (error) {
    MessagePlugin.error(`Failed to create session: ${error.message}`);
  }
}

async function selectSession(sessionId) {
  try {
    currentSessionId.value = sessionId;
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!response.ok) throw new Error("Failed to load session");
    const session = await response.json();

    // 将records转换为UI消息
    const convertedMessages = convertRecordsToMessages(session.records || []);

    await chatEngine.value?.setMessages(convertedMessages, "replace");
  } catch (error) {
    MessagePlugin.error(`Failed to load session: ${error.message}`);
  }
}

async function deleteSession(sessionId) {
  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete session");
    
    // 从列表中移除
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    
    // 如果删除的是当前会话，选择其他会话
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id);
      } else {
        currentSessionId.value = null;
        await chatEngine.value?.setMessages([], "replace");
      }
    }
    
    MessagePlugin.success("Session deleted successfully");
  } catch (error) {
    MessagePlugin.error(`Failed to delete session: ${error.message}`);
  }
}

// 将session records转换为UI消息格式 - 每个工具调用独立显示
function convertRecordsToMessages(records) {
  const messages = [];

  for (let i = 0; i < records.length; i++) {
    const record = records[i];

    if (record.type === "message") {
      if (record.role === "system") {
        // 跳过系统消息，不显示在UI
        continue;
      } else if (record.role === "user") {
        messages.push({
          id: `user_${i}`,
          role: "user",
          content: [{ type: "markdown", data: (record.content || "").trim() }],
          datetime: record.timestamp,
          status: "complete",
        });
      } else if (record.role === "assistant") {
        // assistant消息直接显示
        if (record.content) {
          messages.push({
            id: `assistant_${i}`,
            role: "assistant",
            content: [{ type: "markdown", data: record.content.trim() }],
            datetime: record.timestamp,
            status: "complete",
          });
        }
      }
    } else if (record.type === "tool_call") {
      // 每个工具调用作为独立的assistant消息
      messages.push({
        id: `tool_${i}`,
        role: "assistant",
        content: formatToolCallContent(record),
        datetime: record.timestamp,
        status: "complete",
      });
    }
  }

  return messages;
}

// 当前流式响应的 AbortController
let currentAbortController = null;

async function sendMessage(userInput) {
  if (!userInput?.trim() || loading.value) return;
  if (!currentSessionId.value) await createSession();

  loading.value = true;
  inputMessage.value = "";

  // 创建新的 AbortController
  currentAbortController = new AbortController();

  try {
    // 获取当前消息列表，添加用户消息
    let currentMessages = [...(messages.value || [])];
    const userMsg = {
      id: `user_${Date.now()}`,
      role: "user",
      content: [{ type: "markdown", data: userInput.trim() }],
      status: "complete",
    };
    currentMessages.push(userMsg);
    await chatEngine.value?.setMessages(currentMessages, "replace");

    // 使用流式 API
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId.value,
        message: userInput,
      }),
      signal: currentAbortController.signal,
    });

    if (!response.ok) throw new Error("Failed to send message");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let sseBuffer = "";

    let currentAssistantMsg = null; // 当前正在流式输出的助手消息
    let streamingContent = ""; // 累积的流式内容

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      sseBuffer += chunk;
      const lines = sseBuffer.split("\n");
      sseBuffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;

        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        if (jsonStr === "[DONE]") {
          break;
        }

        try {
          const event = JSON.parse(jsonStr);

          if (event.type === "content") {
            // 流式内容
            streamingContent += event.content;

            if (!currentAssistantMsg) {
              // 创建新的助手消息
              currentAssistantMsg = {
                id: `assistant_${Date.now()}`,
                role: "assistant",
                content: [{ type: "markdown", data: streamingContent }],
                status: "streaming",
              };
              currentMessages = [...(messages.value || [])];
              currentMessages.push(currentAssistantMsg);
            } else {
              // 更新现有消息 - 创建新对象避免修改只读属性
              currentAssistantMsg = {
                ...currentAssistantMsg,
                content: [{ type: "markdown", data: streamingContent }],
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
            }

            await chatEngine.value?.setMessages(currentMessages, "replace");
          } else if (event.type === "record") {
            // 完成的记录（assistant消息或其他）
            if (
              event.record.type === "message" &&
              event.record.role === "assistant"
            ) {
              if (currentAssistantMsg) {
                // 如果有流式消息，更新为完成状态 - 创建新对象
                currentAssistantMsg = {
                  ...currentAssistantMsg,
                  content: [{ type: "markdown", data: event.record.content.trim() }],
                  status: "complete",
                };
                currentMessages = [...(messages.value || [])];
                currentMessages[currentMessages.length - 1] =
                  currentAssistantMsg;
                await chatEngine.value?.setMessages(currentMessages, "replace");
                currentAssistantMsg = null;
                streamingContent = "";
              } else if (event.record.content) {
                // 没有流式消息，但有新的 assistant 记录（如工具调用后的思考过程）
                const newAssistantMsg = {
                  id: `assistant_${Date.now()}_${Math.random()}`,
                  role: "assistant",
                  content: [{ type: "markdown", data: event.record.content.trim() }],
                  status: "complete",
                };
                currentMessages = [...(messages.value || [])];
                currentMessages.push(newAssistantMsg);
                await chatEngine.value?.setMessages(currentMessages, "replace");
              }
            }
          } else if (event.type === "tool_start") {
            // 工具开始执行 - 先完成当前流式消息
            if (currentAssistantMsg && streamingContent) {
              currentAssistantMsg = {
                ...currentAssistantMsg,
                status: "complete",
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
              await chatEngine.value?.setMessages(currentMessages, "replace");
              currentAssistantMsg = null;
              streamingContent = "";
            }

            // 为每个工具创建唯一ID，使用 tool_call_id 如果有的话
            const toolMsgId = `tool_${event.tool_call_id || Date.now()}_${Math.random()}`;

            // 格式化参数
            let argsStr = "";
            try {
              argsStr = JSON.stringify(event.arguments, null, 2);
            } catch {
              argsStr = String(event.arguments);
            }

            // 添加工具执行中的消息
            const toolStartMsg = {
              id: toolMsgId,
              role: "assistant",
              content: [
                {
                  type: "custom",
                  data: {
                    componentType: "tool-call",
                    funcName: event.tool_name,
                    args: event.arguments,
                    result: "⏳ 执行中...",
                    success: null, // null 表示执行中
                  },
                },
              ],
              status: "streaming",
              _toolCallId: event.tool_call_id, // 保存tool_call_id用于后续匹配
            };
            currentMessages = [...(messages.value || [])];
            currentMessages.push(toolStartMsg);
            await chatEngine.value?.setMessages(currentMessages, "replace");
          } else if (event.type === "tool_result") {
            // 工具执行完成 - 找到对应的工具消息并更新
            const toolRecord = event.record;
            currentMessages = [...(messages.value || [])];

            // 查找对应的工具消息（通过 tool_call_id 匹配）
            const toolMsgIndex = currentMessages.findIndex(
              (msg) => msg._toolCallId === toolRecord.tool_call_id,
            );

            if (toolMsgIndex !== -1) {
              // 更新对应的工具消息
              currentMessages[toolMsgIndex] = {
                ...currentMessages[toolMsgIndex],
                content: formatToolCallContent(toolRecord),
                status: "complete",
              };
            } else {
              // 如果找不到，添加为新消息
              currentMessages.push({
                id: `tool_${Date.now()}_${Math.random()}`,
                role: "assistant",
                content: formatToolCallContent(toolRecord),
                status: "complete",
              });
            }
            await chatEngine.value?.setMessages(currentMessages, "replace");
          } else if (event.type === "done") {
            // 完成
            break;
          } else if (event.type === "error") {
            // 错误
            const errorMsg = {
              id: `error_${Date.now()}`,
              role: "assistant",
              content: [{ type: "markdown", data: `❌ ${event.content.trim()}` }],
              status: "complete",
            };
            currentMessages = [...(messages.value || [])];
            currentMessages.push(errorMsg);
            await chatEngine.value?.setMessages(currentMessages, "replace");
          }
        } catch (e) {
          console.error("Parse SSE error:", e, jsonStr);
        }
      }
    }

    await loadSessions();
  } catch (error) {
    if (error.name === "AbortError") {
      // 用户中止
      const currentMessages = [...(messages.value || [])];
      const lastMsg = currentMessages[currentMessages.length - 1];
      if (lastMsg && lastMsg.status === "streaming") {
        currentMessages[currentMessages.length - 1] = {
          ...lastMsg,
          status: "complete",
          content: [
            ...lastMsg.content,
            { type: "markdown", data: "\n\n*[已停止]*" },
          ],
        };
        await chatEngine.value?.setMessages(currentMessages, "replace");
      }
    } else {
      MessagePlugin.error(`Failed to send message: ${error.message}`);
      const errorMessages = [...(messages.value || [])];
      errorMessages.push({
        id: `error_${Date.now()}`,
        role: "assistant",
        content: [
          {
            type: "markdown",
            data: `❌ Failed to send message: ${error.message}`,
          },
        ],
        status: "complete",
      });
      await chatEngine.value?.setMessages(errorMessages, "replace");
    }
  } finally {
    loading.value = false;
    currentAbortController = null;
  }
}

// 停止生成
function stopMessage() {
  if (currentAbortController) {
    currentAbortController.abort();
  }
  chatEngine.value?.abortChat();
}

// 格式化单个工具调用 - 返回 content 数组
function formatToolCallContent(tc) {
  const funcName = tc.tool_name || "未知工具";
  const args = tc.arguments || {};
  const result = tc.result;
  const success = tc.success;

  return [
    {
      type: "custom",
      data: {
        componentType: "tool-call",
        funcName,
        success,
        args,
        result,
      },
    },
  ];
}

// 时间格式化
function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return "Right now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;

  return date.toLocaleDateString("en-US", {
    month: "2-digit",
    day: "2-digit",
  });
}

// 初始化
onMounted(() => {
  loadSessions();
  loadToolStatuses();
});
</script>

<style scoped lang="less">
.chat-layout {
  height: 100vh;
  background: var(--td-bg-color-page);

  :deep(.t-layout) {
    height: 100%;
  }

  :deep(.t-aside) {
    border-right: 1px solid var(--td-border-level-1-color);
  }
}
</style>
