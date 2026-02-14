<template>
  <t-aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>Sessions</h2>
      <t-button
        theme="primary"
        variant="text"
        @click="handleCreateSession"
        class="new-chat-btn"
      >
        <template #icon>
          <add-icon />
        </template>
      </t-button>
    </div>

    <t-list :split="false" class="session-list">
      <t-list-item
        v-for="session in sessions"
        :key="session.id"
        @click="handleSelectSession(session.id)"
      >
        <template #content>
          <div class="session-content" :class="{ active: currentSessionId === session.id }">
            <div class="session-info">
              <div class="session-title">{{ session.title }}</div>
              <div class="session-time">{{ formatTime(session.updated_at) }}</div>
            </div>
            <div class="session-actions">
              <t-dropdown
                trigger="click"
                :options="sessionActions"
                @click="(item, context) => handleSessionAction(session.id, item, context.e)"
              >
                <t-button
                  theme="primary"
                  variant="text"
                  size="small"
                  @click.stop
                  class="menu-btn"
                >
                  <template #icon>
                    <more-icon />
                  </template>
                </t-button>
              </t-dropdown>
            </div>
          </div>
        </template>
      </t-list-item>
    </t-list>

    <t-dialog
      :visible="renameDialogVisible"
      header="Rename Session"
      width="420px"
      :confirm-on-enter="false"
      @confirm="confirmRename"
      @update:visible="handleRenameDialogVisibleChange"
    >
      <t-input
        ref="renameInputRef"
        v-model="renameTitle"
        placeholder="Enter a new session name"
        @enter="confirmRename"
      />
    </t-dialog>

  </t-aside>
</template>

<script setup>
import { ref } from "vue";
import { AddIcon, MoreIcon } from "tdesign-icons-vue-next";

const props = defineProps({
  sessions: {
    type: Array,
    required: true,
  },
  currentSessionId: {
    type: [String, Number],
    default: null,
  },
});

const emits = defineEmits([
  "create-session",
  "select-session",
  "delete-session",
  "rename-session",
]);

const sessionActions = [
  { content: "Rename", value: "rename" },
  { content: "Delete", value: "delete", theme: "error" },
];
const renameDialogVisible = ref(false);
const renameSessionId = ref(null);
const renameTitle = ref("");
const renameInputRef = ref(null);

function handleCreateSession() {
  emits("create-session");
}

function handleSelectSession(sessionId) {
  emits("select-session", sessionId);
}

function handleDeleteSession(sessionId, event) {
  event.stopPropagation();
  emits("delete-session", sessionId);
}

function handleRenameSession(sessionId, event) {
  event.stopPropagation();
  renameSessionId.value = sessionId;
  renameTitle.value = props.sessions.find((session) => session.id === sessionId)?.title || "";
  renameDialogVisible.value = true;
  requestAnimationFrame(() => renameInputRef.value?.focus?.());
}

function handleRenameDialogVisibleChange(visible) {
  renameDialogVisible.value = visible;
  if (!visible) {
    renameSessionId.value = null;
    renameTitle.value = "";
  }
}

function confirmRename() {
  const trimmed = renameTitle.value.trim();
  if (!trimmed || renameSessionId.value == null) return;
  emits("rename-session", renameSessionId.value, trimmed);
  handleRenameDialogVisibleChange(false);
}

function handleSessionAction(sessionId, item, event) {
  if (!item?.value) return;
  if (item.value === "delete") {
    handleDeleteSession(sessionId, event);
    return;
  }
  if (item.value === "rename") {
    handleRenameSession(sessionId, event);
  }
}


function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return "Right now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;

  return date.toLocaleDateString("en-US", {
    month: "2-digit",
    day: "2-digit",
  });
}
</script>

<style scoped lang="less">
.chat-sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  background: var(--td-bg-color-container);

  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid var(--td-border-level-1-color);

    h2 {
      margin: 0;
      font-size: 16px;
    }
  }

  .session-list {
    flex: 1;
    overflow-y: auto;

    :deep(.t-list-item) {
      padding: 0;
      cursor: pointer;

      &:hover {
        background-color: var(--td-bg-color-secondarycontainer);
      }
    }

    :deep(.t-list-item__content) {
      width: 100%;
      min-width: 0;
    }

    .session-content {
      padding: 12px 16px;
      width: 100%;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      transition: all 0.3s ease;
      gap: 8px;
      color: var(--td-text-color-primary);

      &.active {
        background: linear-gradient(90deg, var(--td-brand-color-foil), transparent);
        color: var(--td-brand-color);

        .session-info {
          .session-title {
            color: var(--td-brand-color);
            font-weight: 600;
          }

          .session-time {
            color: var(--td-brand-color);
          }
        }
      }

      .session-info {
        flex: 1;
        min-width: 0;

        .session-title {
          font-size: 14px;
          margin-bottom: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .session-time {
          font-size: 12px;
          color: var(--td-text-color-placeholder);
        }
      }

      .session-actions {
        margin-left: auto;
        width: 28px;
        flex-shrink: 0;
        color: inherit;
      }

      .menu-btn {
        flex-shrink: 0;
        color: inherit;
      }
    }
  }

}
</style>
