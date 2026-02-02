<template>
  <div class="tool-status-wrapper">
    <div class="tool-status-toolbar">
      <t-button variant="text" @click="handleRefresh" :loading="refreshing">
        <template #icon>
          <t-icon name="refresh" />
        </template>
        刷新
      </t-button>
    </div>
    <t-collapse :default-value="[]" class="tools-collapse">
      <t-collapse-panel
        v-for="tool in toolStatuses"
        :key="tool.name"
        :value="tool.name"
        :header="`${tool.name} - ${tool.status === 'ok' ? '✅' : '❌'}`"
      >
        <ExecuteCommandStatus
          v-if="tool.name === 'execute_command'"
          :status="tool"
        />
        <DefaultToolStatus v-else :status="tool" />
      </t-collapse-panel>
    </t-collapse>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ExecuteCommandStatus from "./tool-status/ExecuteCommandStatus.vue";
import DefaultToolStatus from "./tool-status/DefaultToolStatus.vue";

defineProps({
  toolStatuses: {
    type: Array,
    default: () => [],
  },
});

const refreshing = ref(false);
const emits = defineEmits(["refresh"]);

async function handleRefresh() {
  refreshing.value = true;
  emits("refresh");
  refreshing.value = false;
}
</script>

<style scoped lang="less">
.tool-status-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tool-status-toolbar {
  display: flex;
  justify-content: flex-end;
}

:deep(.tools-collapse) {
  .t-collapse-panel {
    .t-collapse-header {
      font-weight: 600;
    }
  }
}
</style>
