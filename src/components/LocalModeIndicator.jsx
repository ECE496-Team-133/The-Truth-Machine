import React from 'react'
import { motion } from 'framer-motion'
import './LocalSetupModal.css'

function LocalModeIndicator({ config, onClick }) {
  const isLocal = config?.enabled

  return (
    <motion.button
      className={`local-mode-indicator ${isLocal ? 'mode-local' : 'mode-api'}`}
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      title={isLocal
        ? `Local mode: ${config.model_tag} — click to configure`
        : 'Using OpenAI API — click to set up local mode'
      }
    >
      <span className="indicator-dot" />
      <span>{isLocal ? 'LOCAL' : 'API'}</span>
      {isLocal && config.model_tag && (
        <span className="indicator-model">{config.model_tag}</span>
      )}
    </motion.button>
  )
}

export default LocalModeIndicator
