import React, { useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './ThinkingPanel.css'

const SOURCE_SHORT = {
  wikipedia: 'Wikipedia', ap: 'AP', reuters: 'Reuters', guardian: 'Guardian',
  bbc: 'BBC', nytimes: 'NYT', washingtonpost: 'WaPo', cnn: 'CNN',
  bloomberg: 'Bloomberg', ft: 'FT', aljazeera: 'Al Jazeera', cnbc: 'CNBC',
  wsj: 'WSJ', politico: 'Politico', economist: 'Economist',
}

// Convert raw SSE events into flat log lines for the streaming panel
function eventsToLogLines(events) {
  const lines = []
  const claimHeaderShown = new Set()
  const planShown = new Set()

  for (const evt of events) {
    const { type, data } = evt
    const claimIdx = (data?.claim_index || 1) - 1
    const src = SOURCE_SHORT[data?.source] || data?.source || ''

    if (type === 'claim' && data?.claim_text && !claimHeaderShown.has(claimIdx)) {
      claimHeaderShown.add(claimIdx)
      if (claimIdx > 0) lines.push({ type: 'divider', text: '', level: 0 })
      lines.push({ type: 'claim-header', text: data.claim_text, level: 0 })
    }

    if (type === 'plan_generated') {
      if (data?.claim_text && !claimHeaderShown.has(claimIdx)) {
        claimHeaderShown.add(claimIdx)
        lines.push({ type: 'claim-header', text: data.claim_text, level: 0 })
      }
      if (!planShown.has(claimIdx)) {
        planShown.add(claimIdx)
        const n = data?.prerequisites?.length || 0
        lines.push({ type: 'plan', text: `Plan ready — ${n} prerequisite${n !== 1 ? 's' : ''} to check`, level: 1 })
      }
    }

    if (type === 'step') {
      const msg = evt.message || data?.message || ''
      if (msg.includes('Generating fact-checking plan')) {
        lines.push({ type: 'info', text: 'Generating fact-check plan…', level: 1 })
      } else if (msg.includes('Found') && msg.includes('claim')) {
        lines.push({ type: 'info', text: msg, level: 0 })
      }
    }

    if (type === 'prerequisite') {
      const status = data?.status
      if (status === 'factchecking' && src) {
        lines.push({ type: 'searching', text: `Searching ${src}…`, level: 2 })
      } else if (status === 'article_found' && src) {
        lines.push({ type: 'found', text: `${src} · article found`, level: 2 })
      } else if (status === 'sources_fetched') {
        for (const s of (data?.skipped_sources || [])) {
          lines.push({ type: 'skipped', text: `${SOURCE_SHORT[s] || s} · no results`, level: 2 })
        }
      } else if (status === 'validated' && data?.label === 'True') {
        lines.push({ type: 'true', text: `Prerequisite ${data?.index}: confirmed ✓`, level: 1 })
      } else if (status === 'failed') {
        lines.push({ type: 'false', text: `Prerequisite ${data?.index}: failed`, level: 1 })
      }
    }

    if (type === 'final_claim') {
      const status = data?.status
      if (status === 'fetching_article') {
        lines.push({ type: 'section', text: 'Running final fact-check', level: 0 })
        if (data?.article_query) {
          lines.push({ type: 'info', text: `Article topic: ${data.article_query}`, level: 1 })
        }
      } else if (status === 'sources_fetched') {
        for (const s of (data?.found_sources || [])) {
          lines.push({ type: 'found', text: `${SOURCE_SHORT[s] || s} · article found`, level: 1 })
        }
        for (const s of (data?.skipped_sources || [])) {
          lines.push({ type: 'skipped', text: `${SOURCE_SHORT[s] || s} · no results`, level: 1 })
        }
      } else if (status === 'factchecking' && src) {
        lines.push({ type: 'searching', text: `Checking ${src}…`, level: 1 })
      } else if (status === 'source_result') {
        const lbl = data?.label
        lines.push({
          type: lbl === 'True' ? 'true' : 'false',
          text: `${src}: ${lbl}`,
          level: 1,
        })
      } else if (status === 'validated') {
        const lbl = data?.label
        lines.push({
          type: lbl === 'True' ? 'verdict-true' : 'verdict-false',
          text: `Verdict: ${lbl}`,
          level: 0,
        })
      } else if (status === 'failed') {
        lines.push({ type: 'verdict-false', text: 'Verdict: could not determine', level: 0 })
      }
    }
  }

  return lines
}

const LINE_ICONS = {
  'claim-header': '◆',
  'plan':         '↳',
  'section':      '◆',
  'info':         '·',
  'searching':    '⟳',
  'found':        '↳',
  'skipped':      '–',
  'true':         '✓',
  'false':        '✗',
  'verdict-true': '✓',
  'verdict-false':'✗',
  'divider':      '',
}

function ThinkingDots() {
  return (
    <span className="thinking-dots-row" aria-label="thinking">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="thinking-dot"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2, ease: 'easeInOut' }}
        />
      ))}
    </span>
  )
}

function ThinkingPanel({ progressUpdates = [], incrementalData, currentStep }) {
  const logEndRef = useRef(null)
  const logContainerRef = useRef(null)

  const logLines = useMemo(() => eventsToLogLines(progressUpdates), [progressUpdates])

  // Auto-scroll to bottom as new lines appear
  useEffect(() => {
    const el = logContainerRef.current
    if (!el) return
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (isNearBottom) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [logLines.length])

  const hasContent = logLines.length > 0
  const claims = incrementalData?.claims || []
  const claimCount = claims.length

  return (
    <div className="thinking-panel">
      <div className="thinking-panel-header">
        <ThinkingDots />
        <span className="thinking-panel-label">
          Thinking{claimCount > 0 ? ` · ${claimCount} claim${claimCount > 1 ? 's' : ''}` : ''}
        </span>
      </div>

      <div className="thinking-log" ref={logContainerRef}>
        {!hasContent && (
          <div className="log-line log-info log-level-0">
            <span className="log-icon">·</span>
            <span className="log-text">Extracting claims from your query…</span>
          </div>
        )}

        <AnimatePresence initial={false}>
          {logLines.map((line, i) => {
            if (line.type === 'divider') {
              return <div key={i} className="log-divider" />
            }
            const icon = LINE_ICONS[line.type] || '·'
            return (
              <motion.div
                key={i}
                className={`log-line log-${line.type} log-level-${line.level}`}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
              >
                <span className={`log-icon ${line.type === 'searching' ? 'log-icon-spin' : ''}`}>
                  {icon}
                </span>
                <span className="log-text">{line.text}</span>
              </motion.div>
            )
          })}
        </AnimatePresence>

        <div ref={logEndRef} />
      </div>
    </div>
  )
}

export default ThinkingPanel
