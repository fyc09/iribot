<template>
  <t-aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>会话</h2>
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
            <t-button
              theme="primary"
              variant="text"
              size="small"
              @click="handleDeleteSession(session.id, $event)"
              class="delete-btn"
            >
              <template #icon>
                <delete-icon />
              </template>
            </t-button>
          </div>
        </template>
      </t-list-item>
    </t-list>

  </t-aside>
</template>

<script setup>
import { AddIcon, DeleteIcon } from "tdesign-icons-vue-next";

defineProps({
  sessions: {
    type: Array,
    required: true,
  },
  currentSessionId: {
    type: [String, Number],
    default: null,
  },
});

const emits = defineEmits(["create-session", "select-session", "delete-session"]);

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

    .session-content {
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.3s ease;
      gap: 8px;

      &.active {
        background: linear-gradient(90deg, var(--td-brand-color-foil), transparent);

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

      .delete-btn {
        flex-shrink: 0;
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      &:hover .delete-btn {
        opacity: 1;
      }
    }
  }

}
</style>
