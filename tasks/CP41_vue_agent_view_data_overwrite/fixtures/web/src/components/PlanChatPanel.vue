<template>
  <div class="plan-chat-panel">
    <div class="plan-header">
      <h3>{{ chat?.title || 'Plan Chat' }}</h3>
      <button @click="handleSave">Save</button>
    </div>
    <div class="context-editor">
      <div class="field-group">
        <label>System Prompt</label>
        <textarea
          v-model="localContext.system_prompt"
          @input="onContextChange"
          rows="4"
        />
      </div>
      <div class="field-group">
        <label>Plan Notes</label>
        <textarea
          v-model="localContext.plan_notes"
          @input="onContextChange"
          rows="6"
        />
      </div>
      <div class="field-group">
        <label>Temperature</label>
        <input
          type="number"
          v-model.number="localContext.temperature"
          @input="onContextChange"
          min="0" max="2" step="0.1"
        />
      </div>
    </div>
    <div class="chat-messages">
      <div v-for="msg in chat?.messages" :key="msg.id" class="message">
        <span class="role">{{ msg.role }}</span>
        <span class="content">{{ msg.content }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, toRaw } from 'vue'
import { debounce } from 'lodash-es'
import { updateAgentChatContext } from '@/utils/agentChatManagerDB'

const props = defineProps({
  chat: Object,
  context: Object,
})

const emit = defineEmits(['update:context', 'save'])

const isLoadingChat = ref(false)
const localContext = ref({})

// BUG: This watcher copies context into localContext on every change,
// but if the parent's context updates asynchronously (e.g. from a
// chat switch), it overwrites localContext with the NEW chat's data
// while autoSaveContext might still be saving the OLD chat's data
watch(() => props.context, (newCtx) => {
  localContext.value = { ...newCtx }
}, { immediate: true, deep: true })

function onContextChange() {
  emit('update:context', { ...localContext.value })
  autoSaveContext()
}

// BUG: autoSaveContext captures currentAgentChatId at call time,
// but by the time the debounced function executes, the user may
// have switched to a different chat. This saves the WRONG context
// to the WRONG chat record.
const autoSaveContext = debounce(async () => {
  if (isLoadingChat.value) return
  const chatId = props.chat?.id
  if (!chatId) return
  try {
    await saveChatContext()
  } catch (e) {
    console.error('Auto-save failed:', e)
  }
}, 1000)

async function saveChatContext() {
  if (!props.chat?.id) return
  // BUG: uses props.chat.id which may have changed due to
  // parent re-render from chat switch
  await updateAgentChatContext(props.chat.id, toRaw(localContext.value))
}

function handleSave() {
  autoSaveContext.cancel()
  emit('save')
}
</script>

<style scoped>
.plan-chat-panel {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.context-editor {
  flex: 0 0 auto;
}
.field-group {
  margin-bottom: 12px;
}
.field-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 4px;
}
.field-group textarea, .field-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  margin-top: 16px;
}
.message {
  padding: 8px;
  border-bottom: 1px solid #f0f0f0;
}
.role {
  font-weight: bold;
  margin-right: 8px;
}
</style>
