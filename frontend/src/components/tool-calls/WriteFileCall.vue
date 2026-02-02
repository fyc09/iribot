<template>
  <div class="write-file-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>✍️ 写入文件 </span>
            <code>{{ args.file_path }}</code>
            &nbsp;
            <t-tag v-if="result === null" theme="warning" variant="light">写入中</t-tag>
            <t-tag v-else-if="result?.success" theme="success" variant="light">成功</t-tag>
            <t-tag v-else theme="danger" variant="light">失败</t-tag>
          </div>
        </template>
        <div class="content-area">
          <t-space direction="vertical">
            <div>
              <t-typography>
                <t-typography-paragraph>
                  内容大小: <code>{{ (args.content || '').length }} 字节</code>
                </t-typography-paragraph>
              </t-typography>
            </div>

            <div v-if="result">
              <div v-if="result.success">
                <t-typography>
                  <t-typography-paragraph>
                    <code>{{ result.message }}</code>
                  </t-typography-paragraph>
                </t-typography>
              </div>
              <t-alert v-else theme="error">
                <t-typography-text>{{ result.message || JSON.stringify(result) }}</t-typography-text>
              </t-alert>
            </div>
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
