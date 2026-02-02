<template>
  <div class="list-directory-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>📁 列举目录 </span>
            <code>{{ args.path }}</code>
            &nbsp;
            <t-tag v-if="result === null" theme="warning" variant="light">列举中</t-tag>
            <t-tag v-else-if="result?.success" theme="success" variant="light">成功</t-tag>
            <t-tag v-else theme="danger" variant="light">失败</t-tag>
          </div>
        </template>
        <div class="content-area">
          <t-space direction="vertical">
            <div v-if="result">
              <div v-if="result.success && displayItems.length > 0">
                <t-typography>
                  <t-typography-paragraph>
                    <span>{{ displayItems.length }} 项</span>
                  </t-typography-paragraph>
                </t-typography>
                <t-table 
                  :data="displayItems" 
                  :columns="columns"
                  :bordered="true"
                  row-key="name"
                  size="small"
                >
                  <template #type="{ row }">
                    <span v-if="row.type === 'directory'">📁</span>
                    <span v-else>📄</span>
                  </template>
                  <template #name="{ row }">
                    <code>{{ row.name }}</code>
                  </template>
                </t-table>
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
import { computed } from 'vue';

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

const columns = [
  { colKey: 'type', title: '类型', width: '60px' },
  { colKey: 'name', title: '文件名', ellipsis: true },
];

const displayItems = computed(() => {
  if (!Array.isArray(props.result?.items)) return [];
  
  const items = props.result.items;
  if (items.length === 0) return [];
  
  const firstItem = items[0];
  if (typeof firstItem === 'object') {
    return items;
  } else if (typeof firstItem === 'string') {
    return items.map(item => ({
      name: item.replace(/\/$/, ''),
      type: item.endsWith('/') ? 'directory' : 'file',
      path: props.args.path ? `${props.args.path}/${item}` : item
    }));
  }
  return [];
});
</script>

<style scoped>
.content-area {
  max-height: var(--tool-call-max-height);
  overflow: auto;
}
</style>
