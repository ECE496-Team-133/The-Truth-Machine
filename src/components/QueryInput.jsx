import React, { useState } from 'react'
import { motion } from 'framer-motion'
import './QueryInput.css'

function QueryInput({ onSubmit, disabled }) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !disabled) {
      onSubmit(query.trim())
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
      </div>
    </motion.form>
  )
}

export default QueryInput

