<template>
  <div class="agent-view">
    <div class="sidebar">
      <ChatList
        :chats="agentChats"
        :current-chat-id="currentChatId"
        @select="handleSelectChat"
        @new-chat="handleNewChat"
      />
    </div>
    <div class="main-panel">
      <PlanChatPanel
        v-if="currentChat?.type === 'plan'"
        :chat="currentChat"
        :context="chatContext"
        @update:context="handleContextUpdate"
        @save="handleSave"
      />
      <ChatPanel
        v-else
        :chat="currentChat"
        :messages="chatMessages"
        @send="handleSend"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import ChatList from '@/components/ChatList.vue'
import PlanChatPanel from '@/components/PlanChatPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import { getAgentChats, getAgentChatContext, updateAgentChatContext } from '@/utils/agentChatManagerDB'

const agentChats = ref([])
const currentChatId = ref(null)
const chatContext = ref({})
const chatMessages = ref([])

const currentChat = computed(() =>
  agentChats.value.find(c => c.id === currentChatId.value)
)

// BUG: This watcher fires on every chat selection and overwrites
// the context state before the previous save completes
watch(currentChatId, async (newId) => {
  if (!newId) return
  // No cancellation of pending saves - causes race condition
  const ctx = await getAgentChatContext(newId)
  chatContext.value = ctx
  const chat = agentChats.value.find(c => c.id === newId)
  if (chat) {
    chatMessages.value = chat.messages || []
  }
})

// BUG: loadChats overwrites agentChats.value without merging,
// losing any unsaved edits in child components
async function loadChats() {
  const chats = await getAgentChats()
  agentChats.value = chats
  if (chats.length > 0 && !currentChatId.value) {
    currentChatId.value = chats[0].id
  }
}

function handleSelectChat(chatId) {
  // BUG: No dirty-check before switching - unsaved context is lost
  currentChatId.value = chatId
}

async function handleNewChat() {
  await loadChats()
}

// BUG: handleContextUpdate mutates chatContext directly,
// and the debounced auto-save in PlanChatPanel may fire
// with stale data after a chat switch
function handleContextUpdate(newContext) {
  chatContext.value = newContext
}

async function handleSave() {
  if (!currentChatId.value) return
  await updateAgentChatContext(currentChatId.value, chatContext.value)
  await loadChats()
}

async function handleSend(message) {
  if (!currentChatId.value) return
  chatMessages.value.push(message)
  // BUG: directly pushes to local array but doesn't sync to DB
  // until next loadChats() call - another chat switch will lose it
}

onMounted(() => {
  loadChats()
})
</script>

<style scoped>
.agent-view {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: 280px;
  border-right: 1px solid #e0e0e0;
}
.main-panel {
  flex: 1;
  overflow: hidden;
}
</style>
