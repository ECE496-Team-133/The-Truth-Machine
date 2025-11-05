import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './ProgressDisplay.css'

function ProgressDisplay({ currentStep, progressUpdates }) {
  const getStatusIcon = (type, status) => {
    if (status === 'validating' || status === 'selecting_article' || status === 'fetching_article' || 
        status === 'factchecking' || status === 'extracting' || status === 'generating') {
      return '🔄'
    }
    if (status === 'validated' || status === 'completed') {
      return '✓'
    }
    if (status === 'failed') {
      return '✗'
    }
    return '⏳'
  }

  const getStatusColor = (status) => {
    if (status === 'validating' || status === 'selecting_article' || status === 'fetching_article' || 
        status === 'factchecking' || status === 'extracting' || status === 'generating') {
      return '#ff9800'
    }
    if (status === 'validated' || status === 'completed') {
      return '#4caf50'
    }
    if (status === 'failed') {
      return '#f44336'
    }
    return '#9e9e9e'
  }

  return (
    <div className="progress-display">
      <div className="progress-header">
        <div className="spinner"></div>
        <h3>Processing your query...</h3>
      </div>

      <div className="progress-steps">
        <AnimatePresence>
          {progressUpdates.map((update, index) => {
            const status = update.data?.status || 'pending'
            const icon = getStatusIcon(update.type, status)
            const color = getStatusColor(status)
            
            return (
              <motion.div
                key={index}
                className="progress-step"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="step-indicator" style={{ color }}>
                  <motion.span
                    animate={status.includes('validating') || status.includes('selecting') || 
                            status.includes('fetching') || status.includes('factchecking') || 
                            status.includes('extracting') || status.includes('generating') 
                              ? { rotate: 360 } : {}}
                    transition={
                      status.includes('validating') || status.includes('selecting') || 
                      status.includes('fetching') || status.includes('factchecking') || 
                      status.includes('extracting') || status.includes('generating')
                        ? { duration: 2, repeat: Infinity, ease: 'linear' }
                        : {}
                    }
                  >
                    {icon}
                  </motion.span>
                </div>
                <div className="step-content">
                  <p className="step-message">{update.message}</p>
                  {update.data?.article_query && (
                    <p className="step-detail">Article: {update.data.article_query}</p>
                  )}
                  {update.data?.label && (
                    <p className="step-detail">Result: <strong>{update.data.label}</strong></p>
                  )}
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {currentStep && (
          <motion.div
            className="progress-step current"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="step-indicator" style={{ color: getStatusColor(currentStep.data?.status || 'validating') }}>
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              >
                🔄
              </motion.span>
            </div>
            <div className="step-content">
              <p className="step-message">{currentStep.message}</p>
              {currentStep.data?.article_query && (
                <p className="step-detail">Article: {currentStep.data.article_query}</p>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default ProgressDisplay

