<template>
  <div class="execute-command-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span v-if="args.action === 'start'">💻 启动Shell会话</span>
            <span v-else-if="args.action === 'run'">💻 执行命令 </span>
            <span v-else-if="args.action === 'write'">✍️ 写入输入 </span>
            <span v-else-if="args.action === 'read'">📖 读取输出</span>
            <span v-else-if="args.action === 'stop'">🛑 停止会话</span>
            <span v-else>💻 Shell操作</span>
            
            <code v-if="args.action === 'run' && args.command">{{ args.command }}</code>
            <code v-else-if="args.action === 'write' && args.input">{{ args.input }}</code>
            <code v-else-if="args.session_id"> ({{ args.session_id }})</code>
            &nbsp;
            <t-tag v-if="result.success === null" theme="warning" variant="light"
              >执行中</t-tag
            >
            <t-tag v-else-if="result.success === true" theme="success" variant="light"
              >成功</t-tag
            >
            <t-tag v-else-if="result.success === false" theme="danger" variant="light"
              >失败</t-tag
            >
            <t-tag v-else theme="default" variant="light"
              >未知</t-tag>
          </div>
        </template>
        <div class="content-area">
          <t-space direction="vertical">
            <!-- action: start -->
            <template v-if="args.action === 'start'">
              <div v-if="result">
                <div v-if="result.success">
                  <t-typography>
                    <t-typography-paragraph>Shell类型: <code>{{ result.shell_type }}</code></t-typography-paragraph>
                  </t-typography>
                </div>
                <t-alert v-else theme="error">
                  <t-typography-text>{{ result.error }}</t-typography-text>
                </t-alert>
              </div>
            </template>

            <!-- action: run -->
            <template v-else-if="args.action === 'run'">
              <div v-if="result">
                <div v-if="result.stdout">
                  <pre>{{ result.stdout }}</pre>
                </div>
                <div v-if="result.stderr">
                  <pre class="stderr">{{ result.stderr }}</pre>
                </div>
                <div v-if="!result.success && result.error">
                  <t-alert theme="error">
                    <t-typography-text>{{ result.error }}</t-typography-text>
                  </t-alert>
                </div>
              </div>
            </template>

            <!-- action: write -->
            <template v-else-if="args.action === 'write'">
              <div v-if="result">
                <div v-if="result.success">
                  <t-typography>
                    <t-typography-paragraph>Shell类型: <code>{{ result.shell_type }}</code></t-typography-paragraph>
                  </t-typography>
                </div>
                <t-alert v-else theme="error">
                  <t-typography-text>{{ result.error }}</t-typography-text>
                </t-alert>
              </div>
            </template>

            <!-- action: read -->
            <template v-else-if="args.action === 'read'">
              <div v-if="result">
                <div v-if="result.stdout">
                  <pre>{{ result.stdout }}</pre>
                </div>
                <div v-if="result.stderr">
                  <pre class="stderr">{{ result.stderr }}</pre>
                </div>
                <div v-if="!result.stdout && !result.stderr && result.success">
                  <t-typography>
                    <t-typography-paragraph>
                      <span>(无输出)</span>
                    </t-typography-paragraph>
                  </t-typography>
                </div>
                <div v-if="!result.success && result.error">
                  <t-alert theme="error">
                    <t-typography-text>{{ result.error }}</t-typography-text>
                  </t-alert>
                </div>
              </div>
            </template>

            <!-- action: stop -->
            <template v-else-if="args.action === 'stop'">
              <div v-if="result">
                <div v-if="result.success">
                  <t-typography>
                    <t-typography-paragraph>Shell类型: <code>{{ result.shell_type }}</code></t-typography-paragraph>
                  </t-typography>
                </div>
                <t-alert v-else theme="error">
                  <t-typography-text>{{ result.error }}</t-typography-text>
                </t-alert>
              </div>
            </template>

            <!-- fallback: 未知action -->
            <template v-else>
              <div v-if="result">
                <div v-if="result.success">
                  <t-typography>
                    <t-typography-paragraph>{{ JSON.stringify(result) }}</t-typography-paragraph>
                  </t-typography>
                </div>
                <t-alert v-else theme="error">
                  <t-typography-text>{{ result.error || JSON.stringify(result) }}</t-typography-text>
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

.stderr {
  color: #e34d59;
}
</style>
