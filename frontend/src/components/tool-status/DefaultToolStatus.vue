<template>
  <div class="default-tool-status">
    <t-card>
      <template #header>
        <div class="status-title">
          <span>{{ status.name }}</span>
          <t-tag v-if="status.status === 'ok'" theme="success" variant="light">✅ 正常</t-tag>
          <t-tag v-else theme="danger" variant="light">❌ 异常</t-tag>
        </div>
      </template>

      <t-typography>
        <t-typography-paragraph>
          <span>状态信息:</span>
        </t-typography-paragraph>
      </t-typography>
      <t-typography-text>{{ JSON.stringify(status, null, 2) }}</t-typography-text>
    </t-card>
  </div>
</template>

<script setup>
defineProps({
  status: {
    type: Object,
    default: () => ({}),
  },
});
</script>
