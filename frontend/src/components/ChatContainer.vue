<template>
  <t-layout class="chat-main">
    <div class="chat-toolbar">
      <t-button theme="primary" variant="text" @click="openToolStatus">
        查看工具状态
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
      header="工具状态"
      width="1920px"
      :footer="false"
      @open="handleRefreshTools"
    >
      <ToolStatusPanel :tool-statuses="toolStatuses" @refresh="handleRefreshTools" />
    </t-dialog>
  </t-layout>
</template>

<script setup>
import { ref } from "vue";
import ChatMessages from "./ChatMessages.vue";
import ToolStatusPanel from "./ToolStatusPanel.vue";

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
  justify-content: flex-end;
  margin-bottom: 8px;
}
</style>
