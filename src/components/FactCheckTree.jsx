import React from 'react'
import { motion } from 'framer-motion'
import ClaimNode from './ClaimNode'
import './FactCheckTree.css'

function FactCheckTree({ data, isLoading = false, currentStep = null, sourceWeights = {} }) {
  return (
    <div className="fact-check-tree">
      {data.claims && data.claims.length > 0 ? (
        <div className="claims-container">
          {data.claims.map((claim, index) => {
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
                sourceWeights={sourceWeights}
              />
            )
          })}
        </div>
      ) : (
        <p className="no-claims">No claims found to validate.</p>
      )}
    </div>
  )
}

export default FactCheckTree
