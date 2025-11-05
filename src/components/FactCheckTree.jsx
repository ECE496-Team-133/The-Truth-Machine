import React from 'react'
import { motion } from 'framer-motion'
import ClaimNode from './ClaimNode'
import './FactCheckTree.css'

function FactCheckTree({ data, isLoading = false, currentStep = null }) {
  return (
    <motion.div
      className="fact-check-tree"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="tree-header">
        <h2>{isLoading ? 'Fact-Checking in Progress...' : 'Fact-Check Results'}</h2>
        {data.total_time && (
          <p className="total-time">Total time: {data.total_time.toFixed(2)}s</p>
        )}
      </div>

      {data.claims && data.claims.length > 0 ? (
        <div className="claims-container">
          {data.claims.map((claim, index) => {
            // Check if this claim is currently being processed
            const isCurrentlyProcessing = isLoading && 
              currentStep && 
              currentStep.data?.claim_index === index + 1
            
            return (
              <ClaimNode 
                key={index} 
                claim={claim} 
                index={index}
                isProcessing={isCurrentlyProcessing}
                currentStep={isCurrentlyProcessing ? currentStep : null}
              />
            )
          })}
        </div>
      ) : (
        <div className="no-claims">
          <p>{isLoading ? 'Starting fact-checking process...' : 'No claims found to validate.'}</p>
        </div>
      )}
    </motion.div>
  )
}

export default FactCheckTree

