/**
 * agentChats.js - Express routes for agent chat CRUD.
 *
 * Tables touched:
 *   agent_chats        - chat metadata (id, title, type, created_at)
 *   agent_chat_context - per-chat context blobs (system_prompt, plan_notes, temperature)
 *   agent_chat_messages - individual messages
 */
const express = require('express')
const router = express.Router()
const db = require('../db')

// GET /api/agent-chats
router.get('/', async (req, res) => {
  try {
    const chats = await db.query(
      'SELECT * FROM agent_chats ORDER BY updated_at DESC'
    )
    // BUG: Also loads all messages inline - expensive and causes
    // the frontend to hold stale message arrays after partial edits
    for (const chat of chats) {
      const msgs = await db.query(
        'SELECT * FROM agent_chat_messages WHERE chat_id = ? ORDER BY idx ASC',
        [chat.id]
      )
      chat.messages = msgs
    }
    res.json(chats)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// GET /api/agent-chats/:id/context
router.get('/:id/context', async (req, res) => {
  try {
    const [ctx] = await db.query(
      'SELECT * FROM agent_chat_context WHERE chat_id = ?',
      [req.params.id]
    )
    res.json(ctx || {})
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// PUT /api/agent-chats/:id/context
// BUG: No version/etag check - last-write-wins causes silent data loss
// when auto-save and manual save race
router.put('/:id/context', async (req, res) => {
  try {
    const { system_prompt, plan_notes, temperature } = req.body
    await db.query(
      `INSERT INTO agent_chat_context (chat_id, system_prompt, plan_notes, temperature)
       VALUES (?, ?, ?, ?)
       ON CONFLICT(chat_id) DO UPDATE SET
         system_prompt = excluded.system_prompt,
         plan_notes = excluded.plan_notes,
         temperature = excluded.temperature,
         updated_at = CURRENT_TIMESTAMP`,
      [req.params.id, system_prompt, plan_notes, temperature]
    )
    res.json({ ok: true })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// PUT /api/agent-chats/:id/last-message
router.put('/:id/last-message', async (req, res) => {
  try {
    const { last_message_idx } = req.body
    await db.query(
      'UPDATE agent_chats SET last_message_idx = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [last_message_idx, req.params.id]
    )
    res.json({ ok: true })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

module.exports = router
