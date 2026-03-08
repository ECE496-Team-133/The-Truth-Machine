import React, { useState } from 'react'
import { motion } from 'framer-motion'
import './QueryInput.css'

function QueryInput({ onSubmit, onRunLocally, disabled, localConfig }) {
  const [query, setQuery] = useState('')
  const [sources, setSources] = useState({
    wikipedia: true,
    ap: false,
    reuters: false,
    guardian: false
  })

  const handleSourceChange = (source) => {
    setSources(prev => ({
      ...prev,
      [source]: !prev[source]
    }))
  }

  const getSelectedSources = () => {
    return Object.entries(sources)
      .filter(([_, selected]) => selected)
      .map(([source, _]) => source)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !disabled) {
      const selectedSources = getSelectedSources()
      if (selectedSources.length === 0) {
        alert('Please select at least one source')
        return
      }
      onSubmit(query.trim(), selectedSources)
    }
  }

  const handleRunLocally = () => {
    if (query.trim() && !disabled) {
      const selectedSources = getSelectedSources()
      if (selectedSources.length === 0) {
        alert('Please select at least one source')
        return
      }
      onRunLocally(query.trim(), selectedSources)
    }
  }

  return (
    <motion.form
      className="query-input-container"
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="query-input-wrapper">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your query to fact-check..."
          className="query-input"
          disabled={disabled}
        />
        <motion.button
          type="submit"
          className="query-submit-button"
          disabled={disabled || !query.trim()}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {disabled ? 'Checking...' : 'Check'}
        </motion.button>
        <motion.button
          type="button"
          className="query-submit-button query-local-button"
          disabled={disabled || !query.trim()}
          onClick={handleRunLocally}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {disabled ? 'Checking...' : (localConfig?.enabled && localConfig?.ollama_running) ? 'Run Locally' : 'Set Up Local'}
        </motion.button>
      </div>
      <div className="source-selection">
        <label className="source-label">Sources:</label>
        <div className="source-checkboxes">
          <label className="source-checkbox">
            <input
              type="checkbox"
              checked={sources.wikipedia}
              onChange={() => handleSourceChange('wikipedia')}
              disabled={disabled}
            />
            <span>Wikipedia</span>
          </label>
          <label className="source-checkbox">
            <input
              type="checkbox"
              checked={sources.ap}
              onChange={() => handleSourceChange('ap')}
              disabled={disabled}
            />
            <span>AP</span>
          </label>
          <label className="source-checkbox">
            <input
              type="checkbox"
              checked={sources.reuters}
              onChange={() => handleSourceChange('reuters')}
              disabled={disabled}
            />
            <span>Reuters</span>
          </label>
          <label className="source-checkbox">
            <input
              type="checkbox"
              checked={sources.guardian}
              onChange={() => handleSourceChange('guardian')}
              disabled={disabled}
            />
            <span>The Guardian</span>
          </label>
        </div>
        <div className="source-note">
          <span className="note-icon">ℹ️</span>
          <span>Entity detection and basic factual queries are automatically checked via Wikipedia, even if not selected above.</span>
        </div>
      </div>
    </motion.form>
  )
}

export default QueryInput

