<template>
  <t-dialog
    :visible="visible"
    header="System Prompt"
    width="800px"
    :footer="false"
    @update:visible="handleVisibleChange"
  >
    <t-loading :loading="loading">
      <pre class="system-prompt-content">{{ content }}</pre>
    </t-loading>
  </t-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { MessagePlugin } from "tdesign-vue-next";

const API_BASE = "/api";

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
});

const emits = defineEmits(["update:visible"]);
const loading = ref(false);
const content = ref("");

function handleVisibleChange(nextVisible) {
  emits("update:visible", nextVisible);
}

async function loadSystemPrompt() {
  loading.value = true;
  try {
    const response = await fetch(`${API_BASE}/prompt/current`);
    if (!response.ok) throw new Error("Failed to load system prompt");
    content.value = await response.text();
  } catch (error) {
    MessagePlugin.error(`Failed to load system prompt: ${error.message}`);
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  (nextVisible) => {
    if (nextVisible) {
      loadSystemPrompt();
    }
  },
);
</script>

<style scoped lang="less">
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
