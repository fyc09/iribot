<template>
  <t-layout class="chat-main">
    <div class="chat-toolbar">
      <t-button theme="primary" variant="text" @click="openToolStatus">
        View tool status
      </t-button>
      <t-button theme="primary" variant="text" @click="openSystemPrompt">
        View system prompt
      </t-button>
    </div>
    <ChatMessages :messages="messages" />
    <t-chat-sender
      v-model="inputMessage"
      :loading="loading"
      @send="handleSend"
      @stop="handleStop"
    />
    <t-dialog
      v-model:visible="toolStatusVisible"
      header="Tool Status"
      width="1920px"
      :footer="false"
      @open="handleRefreshTools"
    >
      <ToolStatusPanel :tool-statuses="toolStatuses" @refresh="handleRefreshTools" />
    </t-dialog>
    <t-dialog
      v-model:visible="systemPromptVisible"
      header="System Prompt"
      width="800px"
      :footer="false"
    >
      <pre class="system-prompt-content">{{ systemPromptContent }}</pre>
    </t-dialog>
  </t-layout>
</template>

<script setup>
import { ref } from "vue";
import { MessagePlugin } from "tdesign-vue-next";
import ChatMessages from "./ChatMessages.vue";
import ToolStatusPanel from "./ToolStatusPanel.vue";

const API_BASE = "/api";

const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  toolStatuses: {
    type: Array,
    default: () => [],
  },
});

const inputMessage = ref("");
const toolStatusVisible = ref(false);
const systemPromptVisible = ref(false);
const systemPromptContent = ref("");
const emits = defineEmits(["send", "stop", "refresh-tools"]);

function handleSend(text) {
  if (text.trim()) {
    emits("send", text);
    inputMessage.value = "";
  }
}

function handleStop() {
  emits("stop");
}

function openToolStatus() {
  toolStatusVisible.value = true;
}

async function openSystemPrompt() {
  try {
    const response = await fetch(`${API_BASE}/prompt/current`);
    if (!response.ok) throw new Error("Failed to load system prompt");
    systemPromptContent.value = await response.text();
    systemPromptVisible.value = true;
  } catch (error) {
    MessagePlugin.error(`Failed to load system prompt: ${error.message}`);
  }
}

function handleRefreshTools() {
  emits("refresh-tools");
}
</script>

<style scoped lang="less">
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--td-bg-color-page);
  padding: 24px;
  overflow: hidden;

  :deep(.t-content) {
    display: flex;
    flex-direction: column;
  }
}

.chat-toolbar {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.system-prompt-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.5;
  max-height: 600px;
  overflow-y: auto;
  background: var(--td-bg-color-container);
  padding: 16px;
  border-radius: 4px;
}
</style>
