<template>
  <div class="shell-read-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>📖 Read Output</span>
            &nbsp;
            <code v-if="args.session_id">({{ args.session_id }})</code>
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
            <div v-if="args.wait_ms !== undefined">
              Wait (ms): <code>{{ args.wait_ms }}</code>
            </div>
            <div v-if="args.max_chars !== undefined">
              Maximum Characters: <code>{{ args.max_chars }}</code>
            </div>
            <template v-if="result">
              <div v-if="result.stdout">
                <pre>{{ result.stdout }}</pre>
              </div>
              <div v-if="result.stderr">
                <pre class="stderr">{{ result.stderr }}</pre>
              </div>
              <div v-if="!result.stdout && !result.stderr && result.success">
                <div>
                  <span>(No output)</span>
                </div>
              </div>
              <div v-if="!result.success && result.error">
                <t-alert theme="error">
                  <pre>{{ result.error }}</pre>
                </t-alert>
              </div>
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

.stderr {
  color: #e34d59;
}
</style>
