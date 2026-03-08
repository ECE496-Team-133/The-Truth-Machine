import React from 'react'
import { motion } from 'framer-motion'
import ValidationBlock from './ValidationBlock'
import './ClaimNode.css'

function ClaimNode({ claim, index, isProcessing = false, currentStep = null, sourceWeights = {} }) {
  // Determine which prerequisite/additional info is currently being processed
  let currentPrereqIndex = null
  let currentInfoIndex = null
  
  if (isProcessing && currentStep) {
    if (currentStep.type === 'prerequisite' && currentStep.data?.index) {
      currentPrereqIndex = currentStep.data.index - 1
    } else if (currentStep.type === 'additional_info' && currentStep.data?.index) {
      currentInfoIndex = currentStep.data.index - 1
    }
  }
  
  return (
    <motion.div
      className="claim-node"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <div className="claim-header">
        <h3 className="claim-title">Claim {index + 1}</h3>
        <p className="claim-text">{claim.text || 'Loading claim...'}</p>
      </div>

      <div className="claim-content">
        {/* Prerequisites - show section as soon as we have any prerequisite data */}
        {claim.prerequisites && claim.prerequisites.length > 0 ? (
          <div className="prerequisites-section">
            <h4 className="section-title">Prerequisites</h4>
            <div className="blocks-container">
              {claim.prerequisites
                .filter(prereq => prereq !== null) // Show all, including pending ones
                .map((prereq, i) => {
                  const actualIndex = i
                  return (
                    <ValidationBlock
                      key={`prereq-${actualIndex}`}
                      title={prereq.text || 'Loading...'}
                      validation={prereq.validation || { status: 'pending' }}
                      type="prerequisite"
                      isCurrentlyProcessing={currentPrereqIndex === actualIndex}
                      sourceWeights={sourceWeights}
                    />
                  )
                })}
            </div>
          </div>
        ) : null}

        {/* Additional Info - show section as soon as we have any additional info data */}
        {claim.additional_info && claim.additional_info.length > 0 ? (
          <div className="additional-info-section">
            <h4 className="section-title">Additional Information</h4>
            <div className="blocks-container">
              {claim.additional_info
                .filter(info => info !== null) // Show all, including pending ones
                .map((info, i) => {
                  const actualIndex = i
                  return (
                    <ValidationBlock
                      key={`info-${actualIndex}`}
                      title={info.question || info.purpose || 'Loading...'}
                      subtitle={null}
                      answer={info.answer}
                      validation={info.validation || { status: 'pending' }}
                      type="additional-info"
                      isCurrentlyProcessing={currentInfoIndex === actualIndex}
                    />
                  )
                })}
            </div>
          </div>
        ) : null}

        {/* Final Claim - show when generated or being processed */}
        {(claim.final_claim || (isProcessing && currentStep?.type === 'final_claim')) && (
          <div className="final-claim-section">
            <h4 className="section-title">Final Claim</h4>
            <ValidationBlock
              title={claim.final_claim || 
                     (currentStep?.data?.final_claim) ||
                     (currentStep?.message.includes(':') 
                       ? currentStep.message.split(':').slice(1).join(':').trim()
                       : 'Generating final claim...')}
              validation={claim.final_validation || {
                status: currentStep?.data?.status || 'validating',
                article_query: currentStep?.data?.article_query || null,
                label: currentStep?.data?.label || null,
                evidence: null,
                article_url: null,
                link: null,
                error: null
              }}
              type="final-claim"
              isCurrentlyProcessing={isProcessing && currentStep?.type === 'final_claim'}
              sourceWeights={sourceWeights}
            />
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default ClaimNode

