import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './QueryInput.css'

function QueryInput({ onSubmit, onRunLocally, disabled, localConfig }) {
  const [query, setQuery] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [query])

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (query.trim() && !disabled) {
      onSubmit(query.trim())
      setQuery('')
    }
  }

  const handleRunLocally = () => {
    if (query.trim() && !disabled) {
      onRunLocally(query.trim())
      setQuery('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const isLocal = localConfig?.enabled && localConfig?.ollama_running && localConfig?.model_ready
  const canSubmit = query.trim().length > 0 && !disabled

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <div className={`chat-input-box ${disabled ? 'is-disabled' : ''}`}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a claim to fact-check…"
          disabled={disabled}
          rows={1}
        />

        <div className="chat-input-actions">
          {/* Local run button — only shown when local mode is available */}
          {localConfig && (
            <AnimatePresence>
              {isLocal && (
                <motion.button
                  key="local-btn"
                  type="button"
                  className="action-btn local-btn"
                  onClick={handleRunLocally}
                  disabled={!canSubmit}
                  title="Run fact-check locally with Ollama"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  whileHover={canSubmit ? { scale: 1.08 } : {}}
                  whileTap={canSubmit ? { scale: 0.94 } : {}}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M7 1.5L12 7L7 12.5M2 7h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Local
                </motion.button>
              )}
            </AnimatePresence>
          )}

          {/* Send button */}
          <motion.button
            type="submit"
            className={`action-btn send-btn ${canSubmit ? 'send-ready' : ''}`}
            disabled={!canSubmit}
            title={disabled ? 'Checking…' : 'Send (Enter)'}
            whileHover={canSubmit ? { scale: 1.08 } : {}}
            whileTap={canSubmit ? { scale: 0.92 } : {}}
          >
            {disabled ? (
              <motion.svg
                width="16" height="16" viewBox="0 0 16 16" fill="none"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              >
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeDasharray="30" strokeDashoffset="10" strokeLinecap="round"/>
              </motion.svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 13V3M3.5 7.5L8 3L12.5 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </motion.button>
        </div>
      </div>

      <p className="chat-input-hint">Press Enter to send · Shift+Enter for new line</p>
    </form>
  )
}

export default QueryInput
