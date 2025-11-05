import React from 'react'
import { motion } from 'framer-motion'
import './ValidationBlock.css'

const statusColors = {
  pending: '#9e9e9e',
  validating: '#ff9800',
  validated: '#4caf50',
  failed: '#f44336',
}

const statusIcons = {
  pending: '⏳',
  validating: '🔄',
  validated: '✓',
  failed: '✗',
}

const statusText = {
  pending: 'Pending',
  validating: 'Validating',
  validated: 'Validated',
  failed: 'Failed',
}

function ValidationBlock({ title, subtitle, answer, validation, type, isCurrentlyProcessing = false }) {
  let status = validation?.status || 'pending'
  const label = validation?.label
  const evidence = validation?.evidence
  const link = validation?.link
  const error = validation?.error
  const articleQuery = validation?.article_query

  // If status is "validated" but label is "False", it should be "failed"
  if (status === 'validated' && label === 'False') {
    status = 'failed'
  }

  const isAnimating = status === 'validating' || status === 'pending'

  return (
    <motion.div
      className={`validation-block ${type} status-${status} ${isCurrentlyProcessing ? 'currently-processing' : ''}`}
      initial={{ opacity: 0, scale: 0.9, y: -10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <div className="block-header">
        <div className="status-indicator">
          <motion.div
            className="status-icon"
            animate={
              status === 'validating' ? { rotate: 360 } : 
              status === 'pending' ? { scale: [1, 1.1, 1] } : {}
            }
            transition={
              status === 'validating'
                ? { duration: 2, repeat: Infinity, ease: 'linear' }
                : status === 'pending'
                ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' }
                : {}
            }
          >
            {statusIcons[status] || '⏳'}
          </motion.div>
          <span className="status-text">{statusText[status] || status}</span>
        </div>
      </div>

      <div className="block-content">
        <h5 className="block-title">{title}</h5>
        {subtitle && type !== 'additional-info' && (
          <p className="block-subtitle">
            <strong>Question:</strong> {subtitle}
          </p>
        )}
        {answer && (
          <p className="block-answer">
            <strong>Answer:</strong> {answer}
          </p>
        )}
        {articleQuery && type !== 'additional-info' && (
          <p className="block-article">
            <strong>Article:</strong> {articleQuery}
          </p>
        )}
        {label && type !== 'additional-info' && (
          <div className="block-label">
            <strong>Result:</strong>{' '}
            <span className={`label-${label.toLowerCase()}`}>{label}</span>
          </div>
        )}
        {evidence && (
          <div className="block-evidence">
            <strong>Evidence:</strong>
            <p>{evidence}</p>
          </div>
        )}
        {error && (
          <div className="block-error">
            <strong>Error:</strong> {error}
          </div>
        )}
        {link && (
          <div className="block-link">
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
            >
              🔗 View Source
            </a>
          </div>
        )}
      </div>

      {isAnimating && (
        <motion.div
          className="loading-bar"
          initial={{ width: 0 }}
          animate={{ width: '100%' }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
      )}
    </motion.div>
  )
}

export default ValidationBlock

