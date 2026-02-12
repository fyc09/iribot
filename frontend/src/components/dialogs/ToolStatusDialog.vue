<template>
  <t-dialog
    :visible="visible"
    header="Tool Status"
    width="1920px"
    :footer="false"
    @update:visible="handleVisibleChange"
    @open="handleOpen"
  >
    <ToolStatusPanel :tool-statuses="toolStatuses" @refresh="handleOpen" />
  </t-dialog>
</template>

<script setup>
import ToolStatusPanel from "../ToolStatusPanel.vue";

defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  toolStatuses: {
    type: Array,
    default: () => [],
  },
});

const emits = defineEmits(["update:visible", "refresh-tools"]);

function handleVisibleChange(nextVisible) {
  emits("update:visible", nextVisible);
}

function handleOpen() {
  emits("refresh-tools");
}
</script>
