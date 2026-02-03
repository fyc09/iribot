<template>
  <div class="write-file-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>✍️ Write File</span>
            &nbsp;
            <code>{{ args.file_path }}</code>
            &nbsp;
            <t-tag
              v-if="result?.success === true"
              theme="success"
              variant="light"
              >Success</t-tag
            >
            <t-tag
              v-else-if="result?.success === false"
              theme="danger"
              variant="light"
              >Failed</t-tag
            >
            <t-tag v-else theme="warning" variant="light">Running</t-tag>
          </div>
        </template>
        <div class="content-area">
          <t-space direction="vertical">
            <div>
              <pre>{{ args.content }}</pre>
            </div>
            <template v-if="result">
              <div v-if="result.success">
                <span>{{ result.message }}</span>
              </div>
              <t-alert v-else theme="error">
                <pre>{{ result.error }}</pre>
              </t-alert>
            </template>
          </t-space>
        </div>
      </t-collapse-panel>
    </t-collapse>
  </div>
</template>

<script setup>
const props = defineProps({
  args: {
    type: Object,
    default: () => ({}),
  },
  result: {
    type: Object,
    default: null,
  },
});
</script>

<style scoped>
.content-area {
  max-height: var(--tool-call-max-height);
  overflow: auto;
}
</style>
