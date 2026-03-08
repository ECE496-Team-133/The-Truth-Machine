import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './TopBar.css'

const SOURCE_LABELS = {
  wikipedia:       'Wikipedia',
  ap:              'AP',
  reuters:         'Reuters',
  guardian:        'The Guardian',
  bbc:             'BBC',
  nytimes:         'New York Times',
  washingtonpost:  'Washington Post',
  cnn:             'CNN',
  bloomberg:       'Bloomberg',
  ft:              'Financial Times',
  aljazeera:       'Al Jazeera',
  cnbc:            'CNBC',
  wsj:             'Wall Street Journal',
  politico:        'Politico',
  economist:       'The Economist',
}

// ── Mode Dropdown ──────────────────────────────────────────
function ModeDropdown({ localConfig, onOpenSetup, onModeChange }) {
  const [open, setOpen] = useState(false)
  const [ollamaModels, setOllamaModels] = useState([])
  const [switching, setSwitching] = useState(null) // model_tag being switched to
  const ref = useRef(null)

  const isLocal = localConfig?.enabled && localConfig?.model_ready
  const currentModel = isLocal ? (localConfig?.model_tag || 'local') : 'gpt-5-nano'

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Fetch installed Ollama models when dropdown opens
  useEffect(() => {
    if (!open) return
    fetch('/api/local/ollama/models')
      .then(r => r.json())
      .then(d => { if (d.models) setOllamaModels(d.models) })
      .catch(() => {})
  }, [open])

  const switchToApi = async () => {
    setSwitching('api')
    try {
      const res = await fetch('/api/local/disable', { method: 'POST' })
      if (res.ok) {
        onModeChange({ enabled: false, model_tag: null, ollama_running: false, model_ready: false, setup_completed: false })
      }
    } catch {}
    setSwitching(null)
    setOpen(false)
  }

  const switchToLocal = async (modelTag) => {
    setSwitching(modelTag)
    try {
      const res = await fetch('/api/local/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_tag: modelTag, ollama_base_url: 'http://localhost:11434' }),
      })
      if (res.ok) {
        const data = await res.json()
        onModeChange({
          enabled: true,
          model_tag: modelTag,
          ollama_running: true,
          model_ready: true,
          setup_completed: data.config?.setup_completed ?? true,
        })
      }
    } catch {}
    setSwitching(null)
    setOpen(false)
  }

  return (
    <div className="mode-dropdown-root" ref={ref}>
      {/* Trigger button */}
      <motion.button
        className={`mode-selector ${open ? 'is-open' : ''}`}
        onClick={() => setOpen(o => !o)}
        whileHover={{ backgroundColor: 'rgba(255,255,255,0.07)' }}
        whileTap={{ scale: 0.97 }}
      >
        <span className="mode-selector-icon">🔍</span>
        <span className="mode-selector-label">Truth Machine</span>
        <span className={`mode-selector-badge ${isLocal ? 'badge-local' : 'badge-api'}`}>
          <span className={`badge-dot ${isLocal ? 'badge-dot-local' : 'badge-dot-api'}`} />
          {currentModel}
        </span>
        <svg
          className={`mode-selector-caret ${open ? 'caret-open' : ''}`}
          width="12" height="12" viewBox="0 0 12 12" fill="none"
        >
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </motion.button>

      {/* Dropdown panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            className="mode-dropdown"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.15 }}
          >
            {/* Section: API */}
            <div className="dropdown-section-label">OpenAI API</div>
            <button
              className={`dropdown-item ${!isLocal ? 'item-active' : ''}`}
              onClick={switchToApi}
              disabled={switching !== null}
            >
              <span className="dropdown-item-icon api-icon">✦</span>
              <span className="dropdown-item-body">
                <span className="dropdown-item-name">gpt-5-nano</span>
                <span className="dropdown-item-sub">OpenAI API · fast &amp; accurate</span>
              </span>
              {switching === 'api' && <Spinner />}
              {!isLocal && switching !== 'api' && <span className="item-check">✓</span>}
            </button>

            {/* Section: Local models */}
            <div className="dropdown-divider" />
            <div className="dropdown-section-label">
              Local (Ollama)
              {ollamaModels.length === 0 && (
                <span className="section-label-hint"> · not running</span>
              )}
            </div>

            {ollamaModels.map(tag => (
              <button
                key={tag}
                className={`dropdown-item ${isLocal && currentModel === tag ? 'item-active' : ''}`}
                onClick={() => switchToLocal(tag)}
                disabled={switching !== null}
              >
                <span className="dropdown-item-icon local-icon">⚡</span>
                <span className="dropdown-item-body">
                  <span className="dropdown-item-name">{tag}</span>
                  <span className="dropdown-item-sub">Runs on your machine</span>
                </span>
                {switching === tag && <Spinner />}
                {isLocal && currentModel === tag && switching !== tag && (
                  <span className="item-check">✓</span>
                )}
              </button>
            ))}

            {ollamaModels.length === 0 && (
              <div className="dropdown-empty">No local models installed yet.</div>
            )}

            <div className="dropdown-divider" />
            <button
              className="dropdown-item dropdown-item-setup"
              onClick={() => { setOpen(false); onOpenSetup() }}
            >
              <span className="dropdown-item-icon">+</span>
              <span className="dropdown-item-body">
                <span className="dropdown-item-name">Set up local model…</span>
              </span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Spinner() {
  return (
    <motion.svg
      width="14" height="14" viewBox="0 0 14 14" fill="none"
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      style={{ flexShrink: 0, color: 'var(--text-tertiary)' }}
    >
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="2" strokeDasharray="22" strokeDashoffset="8" strokeLinecap="round"/>
    </motion.svg>
  )
}

// ── Sources Dropdown ───────────────────────────────────────
function SourcesDropdown({ sources, onToggleSource, sourceWeights, onWeightsChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const activeSources = Object.entries(sources).filter(([, v]) => v).map(([k]) => k)
  const multiSource = activeSources.length >= 2
  const totalPts = activeSources.reduce((sum, k) => sum + (sourceWeights[k] || 0), 0)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const adjustWeight = (key, delta) => {
    onWeightsChange(prev => ({ ...prev, [key]: Math.max(0, Math.min(10, (prev[key] || 0) + delta)) }))
  }

  // Build the button label: "Wikipedia" / "Wikipedia · AP" / "3 sources"
  let buttonLabel
  if (activeSources.length === 0) {
    buttonLabel = 'No sources'
  } else if (activeSources.length <= 2) {
    buttonLabel = activeSources.map(k => SOURCE_LABELS[k]).join(' · ')
  } else {
    buttonLabel = `${activeSources.length} sources`
  }

  return (
    <div className="sources-dropdown-root" ref={ref}>
      <motion.button
        className={`mode-selector ${open ? 'is-open' : ''}`}
        onClick={() => setOpen(o => !o)}
        whileHover={{ backgroundColor: 'rgba(255,255,255,0.07)' }}
        whileTap={{ scale: 0.97 }}
      >
        <span className="mode-selector-icon">📰</span>
        <span className="mode-selector-label">{buttonLabel}</span>
        {multiSource && (
          <span className="sources-weight-badge">⚖ {totalPts} pts</span>
        )}
        <svg
          className={`mode-selector-caret ${open ? 'caret-open' : ''}`}
          width="12" height="12" viewBox="0 0 12 12" fill="none"
        >
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="sources-dropdown"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.15 }}
          >
            <div className="dropdown-section-label">Sources</div>

            {Object.entries(SOURCE_LABELS).map(([key, label]) => {
              const isOn = sources[key]
              return (
                <div key={key} className={`sources-row ${isOn ? 'sources-row-on' : ''}`}>
                  <button
                    className="sources-row-toggle"
                    onClick={() => onToggleSource(key)}
                  >
                    <span className={`sources-row-check ${isOn ? 'check-on' : 'check-off'}`}>
                      {isOn ? '✓' : ''}
                    </span>
                    <span className="sources-row-label">{label}</span>
                  </button>

                  {isOn && multiSource && (
                    <div className="sources-row-stepper">
                      <button
                        className="step-btn"
                        onClick={(e) => { e.stopPropagation(); adjustWeight(key, -1) }}
                        disabled={(sourceWeights[key] || 0) <= 0}
                      >−</button>
                      <span className="weights-val">{sourceWeights[key] || 0}</span>
                      <button
                        className="step-btn"
                        onClick={(e) => { e.stopPropagation(); adjustWeight(key, 1) }}
                        disabled={(sourceWeights[key] || 0) >= 10}
                      >+</button>
                    </div>
                  )}
                </div>
              )
            })}

            {multiSource && (
              <>
                <div className="dropdown-divider" />
                <div className="sources-weight-footer">
                  <span className="sources-weight-icon">⚖</span>
                  <span>Weighted verdict · <strong>{totalPts} pts</strong> total</span>
                  {totalPts === 0 && <span className="weights-warn"> · set weights above</span>}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Main TopBar ────────────────────────────────────────────
function TopBar({ localConfig, onOpenSetup, onModeChange, sources, onToggleSource, sourceWeights, onWeightsChange, isLive, viewingTimestamp }) {
  return (
    <div className="topbar">
      {/* Left — mode selector */}
      <div className="topbar-left">
        <ModeDropdown
          localConfig={localConfig}
          onOpenSetup={onOpenSetup}
          onModeChange={onModeChange}
        />

        <AnimatePresence>
          {isLive && (
            <motion.span
              className="topbar-live"
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
            >
              <span className="live-pulse" />
              Live
            </motion.span>
          )}
          {viewingTimestamp && (
            <motion.span
              className="topbar-timestamp"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {new Date(viewingTimestamp).toLocaleString()}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Right — sources dropdown */}
      <div className="topbar-right">
        <SourcesDropdown
          sources={sources}
          onToggleSource={onToggleSource}
          sourceWeights={sourceWeights}
          onWeightsChange={onWeightsChange}
        />
      </div>
    </div>
  )
}

export default TopBar
