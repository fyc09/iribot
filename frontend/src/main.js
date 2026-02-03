import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'
import { ChatList, ChatMessage, ChatSender } from '@tdesign-vue-next/chat'

const app = createApp(App)

document.documentElement.setAttribute('theme-mode', 'dark');

app.use(TDesign)
app.component('t-chat-list', ChatList)
app.component('t-chat-message', ChatMessage)
app.component('t-chat-sender', ChatSender)

app.mount('#app')
