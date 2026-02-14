<template>
  <t-layout class="chat-layout">
    <ChatSidebar
      :sessions="sessions"
      :current-session-id="currentSessionId"
      @create-session="createSession"
      @select-session="selectSession"
      @delete-session="deleteSession"
      @rename-session="renameSession"
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
import { MessagePlugin } from "tdesign-vue-next";
import ChatSidebar from "./components/ChatSidebar.vue";
import ChatContainer from "./components/ChatContainer.vue";

const API_BASE = "/api";

// State management
const sessions = ref([]);
const currentSessionId = ref(null);
const inputMessage = ref("");
const toolStatuses = ref([]);
const messages = ref([]);
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

    // Convert records to UI messages
    const convertedMessages = convertRecordsToMessages(session.records || []);

    messages.value = convertedMessages;
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
    
    // Remove from list
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    
    // If the current session is deleted, select another one
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id);
      } else {
        currentSessionId.value = null;
        messages.value = [];
      }
    }
    
    MessagePlugin.success("Session deleted successfully");
  } catch (error) {
    MessagePlugin.error(`Failed to delete session: ${error.message}`);
  }
}

// Convert session records to UI message format - each tool call is shown separately
function convertRecordsToMessages(records) {
  const messages = [];

  for (let i = 0; i < records.length; i++) {
    const record = records[i];

    if (record.type === "message") {
      if (record.role === "system") {
        // Skip system messages in the UI
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
        // Assistant messages are shown directly
        // First add reasoning content if exists
        if (record.reasoning_content) {
          messages.push({
            id: `reasoning_${i}`,
            role: "assistant",
            content: [{ type: "reasoning", data: record.reasoning_content.trim() }],
            datetime: record.timestamp,
            status: "complete",
            collapsed: true,
          });
        }
        // Then add main content if exists
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
      // Each tool call is a separate assistant message
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

// AbortController for the current streaming response
let currentAbortController = null;

async function sendMessage(userInput) {
  if (!userInput?.trim() || loading.value) return;
  if (!currentSessionId.value) await createSession();

  loading.value = true;
  inputMessage.value = "";

  // Create a new AbortController
  currentAbortController = new AbortController();

  try {
    // Get current message list and add the user message
    let currentMessages = [...(messages.value || [])];
    const userMsg = {
      id: `user_${Date.now()}`,
      role: "user",
      content: [{ type: "markdown", data: userInput.trim() }],
      status: "complete",
    };
    currentMessages.push(userMsg);
    messages.value = currentMessages;

    // Use streaming API
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

    let currentAssistantMsg = null; // Assistant message currently streaming
    let streamingContent = ""; // Accumulated streaming content
    let streamingReasoningContent = ""; // Accumulated reasoning content

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

          // --- Reasoning streaming logic ---
          if (event.type === "reasoning_start") {
            // New reasoning message
            if (!currentAssistantMsg) {
              currentAssistantMsg = {
                id: `reasoning_${Date.now()}`,
                role: "assistant",
                content: [{ type: "reasoning", data: "" }],
                status: "streaming",
                collapsed: false,
                _reasoning: true,
              };
              streamingReasoningContent = "";
              currentMessages = [...(messages.value || [])];
              currentMessages.push(currentAssistantMsg);
              messages.value = currentMessages;
            }
          } else if (event.type === "reasoning") {
            // Update reasoning content
            if (currentAssistantMsg && currentAssistantMsg._reasoning) {
              streamingReasoningContent += event.content;
              currentAssistantMsg = {
                ...currentAssistantMsg,
                content: [{ type: "reasoning", data: streamingReasoningContent }],
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
              messages.value = currentMessages;
            }
          } else if (event.type === "reasoning_end") {
            // End reasoning
            if (currentAssistantMsg && currentAssistantMsg._reasoning) {
              currentAssistantMsg = {
                ...currentAssistantMsg,
                status: "complete",
                collapsed: true,
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
              messages.value = currentMessages;
              currentAssistantMsg = null;
            }
          } else if (event.type === "content") {
            // Streaming content
            streamingContent += event.content;

            if (!currentAssistantMsg) {
              // Create a new assistant message
              currentAssistantMsg = {
                id: `assistant_${Date.now()}`,
                role: "assistant",
                content: [{ type: "markdown", data: streamingContent }],
                status: "streaming",
              };
              currentMessages = [...(messages.value || [])];
              currentMessages.push(currentAssistantMsg);
            } else {
              // Update existing message - create new object to avoid mutating read-only props
              currentAssistantMsg = {
                ...currentAssistantMsg,
                content: [{ type: "markdown", data: streamingContent }],
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
            }

            messages.value = currentMessages;
          } else if (event.type === "record") {
            // Completed record (assistant message or other)
            if (
              event.record.type === "message" &&
              event.record.role === "assistant"
            ) {
              if (currentAssistantMsg) {
                // If there is a streaming message, update it to complete - create new object
                currentAssistantMsg = {
                  ...currentAssistantMsg,
                  content: [{ type: "markdown", data: event.record.content.trim() }],
                  status: "complete",
                };
                currentMessages = [...(messages.value || [])];
                currentMessages[currentMessages.length - 1] =
                  currentAssistantMsg;
                messages.value = currentMessages;
                currentAssistantMsg = null;
                streamingContent = "";
              } else if (event.record.content) {
                // No streaming message, but a new assistant record (e.g. tool-call reasoning)
                const newAssistantMsg = {
                  id: `assistant_${Date.now()}_${Math.random()}`,
                  role: "assistant",
                  content: [{ type: "markdown", data: event.record.content.trim() }],
                  status: "complete",
                };
                currentMessages = [...(messages.value || [])];
                currentMessages.push(newAssistantMsg);
                messages.value = currentMessages;
              }
            }
          } else if (event.type === "tool_start") {
            // Tool execution starts - finish current streaming message first
            if (currentAssistantMsg && streamingContent) {
              currentAssistantMsg = {
                ...currentAssistantMsg,
                status: "complete",
              };
              currentMessages = [...(messages.value || [])];
              currentMessages[currentMessages.length - 1] = currentAssistantMsg;
              messages.value = currentMessages;
              currentAssistantMsg = null;
              streamingContent = "";
            }

            // Create a unique ID for each tool, use tool_call_id if available
            const toolMsgId = `tool_${event.tool_call_id || Date.now()}_${Math.random()}`;

            // Format arguments
            let argsStr = "";
            try {
              argsStr = JSON.stringify(event.arguments, null, 2);
            } catch {
              argsStr = String(event.arguments);
            }

            // Add a message for tool execution
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
                    result: null,
                    success: null, // null means in progress
                  },
                },
              ],
              status: "streaming",
              _toolCallId: event.tool_call_id, // Store tool_call_id for later matching
            };
            currentMessages = [...(messages.value || [])];
            currentMessages.push(toolStartMsg);
            messages.value = currentMessages;
          } else if (event.type === "tool_result") {
            // Tool execution completed - find and update the matching tool message
            const toolRecord = event.record;
            currentMessages = [...(messages.value || [])];

            // Find the matching tool message (by tool_call_id)
            const toolMsgIndex = currentMessages.findIndex(
              (msg) => msg._toolCallId === toolRecord.tool_call_id,
            );

            if (toolMsgIndex !== -1) {
              // Update matching tool message
              currentMessages[toolMsgIndex] = {
                ...currentMessages[toolMsgIndex],
                content: formatToolCallContent(toolRecord),
                status: "complete",
              };
            } else {
              // If not found, add a new message
              currentMessages.push({
                id: `tool_${Date.now()}_${Math.random()}`,
                role: "assistant",
                content: formatToolCallContent(toolRecord),
                status: "complete",
              });
            }
            messages.value = currentMessages;
          } else if (event.type === "done") {
            // Done
            break;
          } else if (event.type === "error") {
            // Error
            const errorMsg = {
              id: `error_${Date.now()}`,
              role: "assistant",
              content: [{ type: "markdown", data: `❌ ${event.content.trim()}` }],
              status: "complete",
            };
            currentMessages = [...(messages.value || [])];
            currentMessages.push(errorMsg);
            messages.value = currentMessages;
          }
        } catch (e) {
          console.error("Parse SSE error:", e, jsonStr);
        }
      }
    }

    await loadSessions();
  } catch (error) {
    if (error.name === "AbortError") {
      // User aborted
      const currentMessages = [...(messages.value || [])];
      const lastMsg = currentMessages[currentMessages.length - 1];
      if (lastMsg && lastMsg.status === "streaming") {
        currentMessages[currentMessages.length - 1] = {
          ...lastMsg,
          status: "complete",
          content: [
            ...lastMsg.content,
            { type: "markdown", data: "\n\n*[Stopped]*" },
          ],
        };
        messages.value = currentMessages;
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
      messages.value = errorMessages;
    }
  } finally {
    loading.value = false;
    currentAbortController = null;
  }
}

// Stop generation
function stopMessage() {
  if (currentAbortController) {
    currentAbortController.abort();
  }
}

async function renameSession(sessionId, title) {
  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) throw new Error("Failed to rename session");

    const updated = await response.json();
    sessions.value = sessions.value.map((session) =>
      session.id === sessionId ? updated : session,
    );
    MessagePlugin.success("Session renamed successfully");
  } catch (error) {
    MessagePlugin.error(`Failed to rename session: ${error.message}`);
  }
}

// Format a single tool call - returns content array
function formatToolCallContent(tc) {
  const funcName = tc.tool_name || "Unknown tool";
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

// Time formatting
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

// Initialize
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
