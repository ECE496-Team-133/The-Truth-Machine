import React from 'react'
import { motion } from 'framer-motion'
import './ValidationBlock.css'

const SOURCE_LABELS = {
  wikipedia:       'Wikipedia',
  ap:              'AP',
  reuters:         'Reuters',
  guardian:        'The Guardian',
  bbc:             'BBC',
  nytimes:         'NYT',
  washingtonpost:  'WashPost',
  cnn:             'CNN',
  bloomberg:       'Bloomberg',
  ft:              'FT',
  aljazeera:       'Al Jazeera',
  cnbc:            'CNBC',
  wsj:             'WSJ',
  politico:        'Politico',
  economist:       'Economist',
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

function computeWeightedVerdict(perSourceResults, weights) {
  if (!perSourceResults || perSourceResults.length < 2) return null
  let trueWeight = 0
  let totalWeight = 0
  for (const r of perSourceResults) {
    if (r.label === 'Skipped') continue  // skipped sources don't count in the verdict
    const w = weights?.[r.source] ?? 0
    totalWeight += w
    if (r.label === 'True') trueWeight += w
  }
  if (totalWeight === 0) return null
  const ratio = trueWeight / totalWeight
  return { trueWeight, totalWeight, ratio, isTrue: ratio > 0.5 }
}

function ValidationBlock({ title, subtitle, answer, validation, type, isCurrentlyProcessing = false, sourceWeights = {} }) {
  let status = validation?.status || 'pending'
  const label = validation?.label
  const evidence = validation?.evidence
  const link = validation?.link
  const error = validation?.error
  const articleQuery = validation?.article_query
  const source = validation?.source
  const sourcesChecked = validation?.sources_checked || []
  const perSourceResults = validation?.per_source_results || null

  // If status is "validated" but label is "False", it should be "failed"
  if (status === 'validated' && label === 'False') {
    status = 'failed'
  }

  // Compute weighted verdict when we have per-source data
  const weighted = computeWeightedVerdict(perSourceResults, sourceWeights)
  // If weighted verdict disagrees with primary label, note it
  const weightedLabel = weighted ? (weighted.isTrue ? 'True' : 'False') : null
  const hasMultiSource = perSourceResults && perSourceResults.length >= 2
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

        {/* Per-source results breakdown — only for the final claim (weights don't apply to prerequisites) */}
        {hasMultiSource && type === 'final-claim' && (
          <div className="per-source-section">
            <div className="per-source-label">Per-source results</div>
            <div className="per-source-list">
              {perSourceResults.map((r) => {
                const w = sourceWeights?.[r.source] ?? 0
                const isSkipped = r.label === 'Skipped'
                const isTrue = r.label === 'True'
                return (
                  <div key={r.source} className={`per-source-row ${isSkipped ? 'psr-skip' : isTrue ? 'psr-true' : 'psr-false'}`}>
                    <span className="psr-icon">{isSkipped ? '–' : isTrue ? '✓' : '✗'}</span>
                    <span className="psr-source">{SOURCE_LABELS[r.source] || r.source}</span>
                    {type === 'final-claim' && (
                      <span className="psr-weight">{isSkipped ? '–' : `${w} pts`}</span>
                    )}
                    {r.link ? (
                      <a className="psr-link" href={r.link} target="_blank" rel="noopener noreferrer" title={r.evidence || ''}>
                        ↗
                      </a>
                    ) : null}
                  </div>
                )
              })}
            </div>

            {/* Weighted verdict only makes sense for the final claim */}
            {type === 'final-claim' && weighted && (
              <div className={`weighted-verdict ${weighted.isTrue ? 'wv-true' : 'wv-false'}`}>
                <span className="wv-icon">{weighted.isTrue ? '✓' : '✗'}</span>
                <span className="wv-label">Weighted verdict</span>
                <span className="wv-math">
                  {weighted.trueWeight}/{weighted.totalWeight} pts ({Math.round(weighted.ratio * 100)}%)
                  {' → '}
                  <strong>{weighted.isTrue ? 'True' : 'False'}</strong>
                </span>
              </div>
            )}
          </div>
        )}

        {/* Result label — always shown for prerequisites; for final-claim only when no per-source breakdown */}
        {label && type !== 'additional-info' && (type !== 'final-claim' || !hasMultiSource) && (
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
        {(type !== 'final-claim' || !hasMultiSource) && (source || sourcesChecked.length > 0) && (
          <div className="block-source">
            <strong>Source{source ? ':' : 's checked:'}</strong>{' '}
            {source ? (
              <span className="source-badge">{source.charAt(0).toUpperCase() + source.slice(1)}</span>
            ) : (
              <span>{sourcesChecked.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ')}</span>
            )}
          </div>
        )}
        {(type !== 'final-claim' || !hasMultiSource) && link && (
          <div className="block-link">
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
            >
              🔗 View Source {source && `(${source.charAt(0).toUpperCase() + source.slice(1)})`}
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

