<template>
  <t-layout class="chat-main">
    <div class="chat-toolbar">
      <t-button theme="primary" variant="text" @click="configVisible = true">
        Config
      </t-button>
      <t-button theme="primary" variant="text" @click="toolStatusVisible = true">
        View tool status
      </t-button>
      <t-button theme="primary" variant="text" @click="systemPromptVisible = true">
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
    <ToolStatusDialog
      v-model:visible="toolStatusVisible"
      :tool-statuses="toolStatuses"
      @refresh-tools="handleRefreshTools"
    />
    <SystemPromptDialog v-model:visible="systemPromptVisible" />
    <ConfigDialog v-model:visible="configVisible" />
  </t-layout>
</template>

<script setup>
import { ref } from "vue";
import ChatMessages from "./ChatMessages.vue";
import ToolStatusDialog from "./dialogs/ToolStatusDialog.vue";
import SystemPromptDialog from "./dialogs/SystemPromptDialog.vue";
import ConfigDialog from "./dialogs/ConfigDialog.vue";

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
const configVisible = ref(false);
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
</style>
