<template>
  <t-chat-list :clear-history="false">
    <template v-for="message in messages" :key="message.id">
      <t-chat-message
        v-if="message.role === 'user'"
        variant="base"
        placement="right"
        :message="message"
      />
      <t-chat-message v-else variant="text">
        <template #content>
          <template
            v-for="(item, idx) in message.content"
            :key="idx"
            class="content-item"
          >
            <ToolCallMessage
              v-if="
                item.type === 'custom' &&
                item.data.componentType === 'tool-call'
              "
              :tool-data="item.data"
            />
            <t-chat-markdown
              v-else-if="item.type === 'markdown'"
              :content="item.data"
              :options="markdownOptions"
            />
            <t-chat-thinking
              v-else-if="item.type === 'reasoning'"
              :content="{ title: '推理过程', text: item.data }"
              :status="item.status === 'streaming' ? 'pending' : 'complete'"
              layout="border"
              :collapsed="item.collapsed"
              @collapsed-change="item.collapsed = $event.detail"
            />
            <template v-else class="plain-content">{{ item.data }}</template>
          </template>
        </template>
      </t-chat-message>
    </template>
  </t-chat-list>
</template>

<script setup>
import ToolCallMessage from "./ToolCallMessage.vue";
import katex from "katex";

window.katex = katex;

const markdownOptions = {
  themeSettings: {
    codeBlockTheme: "dark",
  },
  engine: {
    syntax: {
      mathBlock: {
        engine: "katex",
      },
      inlineMath: {
        engine: "katex",
      },
    },
  },
};

defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
});
</script>

<style scoped>
.messages-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.user-message .message-content {
  text-align: right;
}

.assistant-message .message-content {
  text-align: left;
  line-height: 2;
}
</style>
