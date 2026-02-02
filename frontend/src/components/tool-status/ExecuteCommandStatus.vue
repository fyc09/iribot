<template>
  <div class="execute-command-status">
    <div v-if="sessions.length > 0" class="sessions-container">
      <div v-for="session in sessions" :key="session.session_id" class="session-item">
        <t-card :bordered="false">
          <template #header>
            <div class="session-title">
              <span>Session: <code>{{ session.session_id }}</code></span>
              <t-tag v-if="session.alive" theme="success" variant="light">🟢 运行中</t-tag>
              <t-tag v-else theme="default" variant="light">⚫ 已停止</t-tag>
            </div>
          </template>

          <div class="content-area">
            <t-space direction="vertical">
              <!-- Session Info -->
              <div>
                <t-typography>
                  <t-typography-paragraph>
                    <span>Shell 类型: <code>{{ session.shell_type }}</code></span>
                  </t-typography-paragraph>
                  <t-typography-paragraph v-if="session.working_dir">
                    <span>工作目录: <code>{{ session.working_dir }}</code></span>
                  </t-typography-paragraph>
                  <t-typography-paragraph>
                    <span>进程 ID: <code>{{ session.pid || 'N/A' }}</code></span>
                  </t-typography-paragraph>
                </t-typography>
              </div>

              <!-- Logs -->
              <div v-if="session.log && session.log.length > 0">
                <t-typography>
                  <t-typography-paragraph>
                    <span>📋 日志 ({{ session.log.length }} 条)</span>
                  </t-typography-paragraph>
                </t-typography>
                <div class="logs-list">
                  <div v-for="(log, idx) in session.log" :key="idx" class="log-entry">
                    <pre :class="logClass(log.stream)">{{ log.data }}</pre>
                  </div>
                </div>
              </div>
              <div v-else>
                <t-typography>
                  <t-typography-paragraph>
                    无日志
                  </t-typography-paragraph>
                </t-typography>
              </div>
            </t-space>
          </div>
        </t-card>
      </div>
    </div>
    <div v-else>
      <t-alert title="无活跃会话" description="没有活跃的命令行会话" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: Object,
    default: () => ({}),
  },
});

const sessions = computed(() => {
  return props.status?.sessions || [];
});

function logClass(stream) {
  switch (stream) {
    case 'stdout': return 'stream-stdout';
    case 'stderr': return 'stream-stderr';
    case 'stdin': return 'stream-stdin';
    default: return 'stream-default';
  }
}
</script>

<style scoped>
.content-area {
  max-height: var(--tool-status-max-height);
  overflow: auto;
}

.stream-stdout {
  color: #00a870;
}

.stream-stderr {
  color: #e34d59;
}

.stream-stdin {
  color: #0052d9;
}

.stream-default {
  color: #666;
}
</style>