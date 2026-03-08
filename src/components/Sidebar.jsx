import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './Sidebar.css'

function getSessionVerdict(factCheckData) {
  if (!factCheckData?.claims?.length) return 'unknown'
  const claims = factCheckData.claims
  const anyFalse = claims.some(c => c.final_validation?.label === 'False')
  const allTrue = claims.every(c => c.final_validation?.label === 'True')
  if (anyFalse) return 'false'
  if (allTrue) return 'true'
  return 'mixed'
}

function VerdictBadge({ verdict, pending }) {
  if (pending) return (
    <motion.span
      className="verdict-badge verdict-pending"
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
    >
      ···
    </motion.span>
  )
  if (verdict === 'true') return <span className="verdict-badge verdict-true">✓</span>
  if (verdict === 'false') return <span className="verdict-badge verdict-false">✗</span>
  if (verdict === 'mixed') return <span className="verdict-badge verdict-mixed">~</span>
  return <span className="verdict-badge verdict-unknown">?</span>
}

function Sidebar({ sessions, activeId, onNewChat, onSelectSession, loading, onDeleteSession }) {
  const formatTime = (timestamp) => {
    const now = Date.now()
    const diff = now - timestamp
    const mins = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-icon">🔍</span>
        <span className="sidebar-brand-name">Truth Machine</span>
      </div>

      <motion.button
        className="new-chat-btn"
        onClick={onNewChat}
        whileHover={{ backgroundColor: 'rgba(0, 255, 136, 0.1)', borderColor: 'rgba(0, 255, 136, 0.4)' }}
        whileTap={{ scale: 0.97 }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        <span>New check</span>
      </motion.button>

      <div className="sessions-section">
        {sessions.length > 0 && (
          <div className="sessions-section-label">Recent</div>
        )}
        <div className="sessions-list">
          <AnimatePresence initial={false}>
            {sessions.map((session) => {
                  const verdict = session.pending ? null : getSessionVerdict(session.factCheckData)
              const isActive = activeId === session.id
              return (
                <motion.div
                  key={session.id}
                  className={`session-item ${isActive ? 'active' : ''}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => onSelectSession(session.id)}
                  title={session.title}
                >
                  <VerdictBadge verdict={verdict} pending={session.pending} />
                  <div className="session-item-body">
                    <span className="session-item-title">
                      {session.title.length > 48
                        ? session.title.substring(0, 48) + '…'
                        : session.title}
                    </span>
                    <span className="session-item-time">{formatTime(session.timestamp)}</span>
                  </div>
                  {onDeleteSession && (
                    <button
                      className="session-delete-btn"
                      onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id) }}
                      title="Delete"
                    >
                      ×
                    </button>
                  )}
                </motion.div>
              )
            })}
          </AnimatePresence>
          {sessions.length === 0 && (
            <div className="sessions-empty">
              <p>No fact-checks yet.</p>
              <p>Submit a claim to get started.</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
