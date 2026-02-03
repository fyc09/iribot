<template>
  <div class="shell-write-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>✍️ Write Input</span>
            &nbsp;
            <code v-if="args.input">{{ args.input }}</code>
            <code v-else-if="args.session_id">({{ args.session_id }})</code>
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
            <div v-if="args.session_id">
              Session ID: <code>{{ args.session_id }}</code>
            </div>
            <div v-if="args.working_dir">
              Working Directory: <code>{{ args.working_dir }}</code>
            </div>
            <template v-if="result">
              <t-alert v-if="!result.success" theme="error">
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
defineProps({
  args: {
    type: Object,
    default: () => ({}),
  },
  result: {
    type: Object,
    default: null,
  },
  success: {
    type: [Boolean, null],
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
