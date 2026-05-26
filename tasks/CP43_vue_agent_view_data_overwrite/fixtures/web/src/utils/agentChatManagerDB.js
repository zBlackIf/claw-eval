/**
 * agentChatManagerDB.js
 *
 * Database layer for agent chat management.
 * Uses IndexedDB via idb-keyval for client-side persistence,
 * with REST API sync to the server.
 */

const API_BASE = '/api/agent-chats'

export async function getAgentChats() {
  const res = await fetch(API_BASE)
  if (!res.ok) throw new Error(`Failed to fetch chats: ${res.status}`)
  return res.json()
}

export async function getAgentChatContext(chatId) {
  const res = await fetch(`${API_BASE}/${chatId}/context`)
  if (!res.ok) throw new Error(`Failed to fetch context: ${res.status}`)
  return res.json()
}

export async function updateAgentChatContext(chatId, context) {
  const res = await fetch(`${API_BASE}/${chatId}/context`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(context),
  })
  if (!res.ok) throw new Error(`Failed to update context: ${res.status}`)
  return res.json()
}

export async function createAgentChat(chatData) {
  const res = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chatData),
  })
  if (!res.ok) throw new Error(`Failed to create chat: ${res.status}`)
  return res.json()
}

export async function deleteAgentChat(chatId) {
  const res = await fetch(`${API_BASE}/${chatId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete chat: ${res.status}`)
  return res.json()
}

export async function updateLastMessageToDB(chatId, lastIdx) {
  const res = await fetch(`${API_BASE}/${chatId}/last-message`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ last_message_idx: lastIdx }),
  })
  if (!res.ok) throw new Error(`Failed to update last message: ${res.status}`)
  return res.json()
}
