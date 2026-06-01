/**
 * agentChatManagerDB.js
 *
 * Database layer for agent chat management.
 * Uses IndexedDB via idb-keyval for client-side persistence,
 * with REST API sync to the server.
 */

const API_BASE = '/api/agent-chats'

/**
 * Fetch all agent chats from the server.
 * BUG: No local cache merge - each call fully replaces the caller's state.
 */
export async function getAgentChats() {
  const res = await fetch(API_BASE)
  if (!res.ok) throw new Error(`Failed to fetch chats: ${res.status}`)
  return res.json()
}

/**
 * Fetch context for a specific agent chat.
 * BUG: No request deduplication - rapid calls (e.g. from watcher)
 * can produce overlapping in-flight requests whose responses arrive
 * out of order, causing the UI to display stale context.
 */
export async function getAgentChatContext(chatId) {
  const res = await fetch(`${API_BASE}/${chatId}/context`)
  if (!res.ok) throw new Error(`Failed to fetch context: ${res.status}`)
  return res.json()
}

/**
 * Update context for a specific agent chat.
 * BUG: No optimistic locking or version check - concurrent saves
 * from debounced auto-save and manual save can produce lost updates.
 * The last write wins, potentially overwriting a more recent save.
 */
export async function updateAgentChatContext(chatId, context) {
  const res = await fetch(`${API_BASE}/${chatId}/context`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(context),
  })
  if (!res.ok) throw new Error(`Failed to update context: ${res.status}`)
  return res.json()
}

/**
 * Create a new agent chat.
 */
export async function createAgentChat(chatData) {
  const res = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chatData),
  })
  if (!res.ok) throw new Error(`Failed to create chat: ${res.status}`)
  return res.json()
}

/**
 * Delete an agent chat.
 */
export async function deleteAgentChat(chatId) {
  const res = await fetch(`${API_BASE}/${chatId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete chat: ${res.status}`)
  return res.json()
}

/**
 * Update the last message index in a chat's DB record.
 */
export async function updateLastMessageToDB(chatId, lastIdx) {
  const res = await fetch(`${API_BASE}/${chatId}/last-message`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ last_message_idx: lastIdx }),
  })
  if (!res.ok) throw new Error(`Failed to update last message: ${res.status}`)
  return res.json()
}
