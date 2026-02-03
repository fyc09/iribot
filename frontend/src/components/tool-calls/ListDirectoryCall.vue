<template>
  <div class="list-directory-call">
    <t-collapse>
      <t-collapse-panel :value="1" destroy-on-close>
        <template #header>
          <div>
            <span>📁 List Directory</span>
            &nbsp;
            <code>{{ args.path }}</code>
            &nbsp;
            <t-tag v-if="result?.success === true" theme="success" variant="light">Success</t-tag>
            <t-tag v-else-if="result?.success === false" theme="danger" variant="light">Failed</t-tag>
            <t-tag v-else theme="warning" variant="light">Running</t-tag>
          </div>
        </template>
        <div class="content-area">
          <t-space direction="vertical">
            <template v-if="result">
              <div v-if="result.success && displayItems.length > 0">
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
  { colKey: 'type', title: 'Type', width: '50px' },
  { colKey: 'name', title: 'Name', ellipsis: true },
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
