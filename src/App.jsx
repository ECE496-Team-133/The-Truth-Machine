import React, { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import QueryInput from './components/QueryInput'
import FactCheckTree from './components/FactCheckTree'
import ThinkingPanel from './components/ThinkingPanel'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import LocalSetupModal from './components/LocalSetupModal'
import './App.css'

function App() {
  // Current in-progress fact-check state
  const [factCheckData, setFactCheckData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [progressUpdates, setProgressUpdates] = useState([])
  const [currentStep, setCurrentStep] = useState(null)
  const [incrementalData, setIncrementalData] = useState(null)
  const [abortController, setAbortController] = useState(null)
  const [currentQuery, setCurrentQuery] = useState('')

  // Session management: 'welcome' | 'active' | <sessionId>
  const [currentView, setCurrentView] = useState('welcome')
  const [sessions, setSessions] = useState(() => {
    try {
      // Strip any stale pending sessions that never completed (e.g. after a page refresh)
      const saved = JSON.parse(localStorage.getItem('ttm-sessions') || '[]')
      return saved.filter(s => !s.pending)
    } catch {
      return []
    }
  })

  // Persistent source selection (shown in TopBar)
  const [sources, setSources] = useState({
    wikipedia: true, ap: false, reuters: false, guardian: false,
    bbc: false, nytimes: false, washingtonpost: false, cnn: false,
    bloomberg: false, ft: false, aljazeera: false, cnbc: false,
    wsj: false, politico: false, economist: false,
  })

  // Trust weights: user allocates points per source (any positive number; normalized at verdict time)
  const [sourceWeights, setSourceWeights] = useState({
    wikipedia: 4, ap: 3, reuters: 3, guardian: 2,
    bbc: 3, nytimes: 3, washingtonpost: 3, cnn: 2,
    bloomberg: 2, ft: 2, aljazeera: 2, cnbc: 2,
    wsj: 3, politico: 2, economist: 2,
  })

  const getSelectedSources = () =>
    Object.entries(sources).filter(([, v]) => v).map(([k]) => k)

  const handleToggleSource = (key) => {
    setSources(prev => ({ ...prev, [key]: !prev[key] }))
  }

  // Tracks the session ID of the currently running check so background completion can update it
  const currentSessionIdRef = useRef(null)

  // Ref for the results scroll container so we auto-scroll to bottom
  const resultsEndRef = useRef(null)

  // Local mode state
  const [localConfig, setLocalConfig] = useState(null)
  const [showSetupModal, setShowSetupModal] = useState(false)

  const fetchLocalStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/local/status')
      if (res.ok) {
        const data = await res.json()
        const cfg = {
          enabled: data.local_mode_enabled,
          model_tag: data.model_tag,
          setup_completed: data.setup_completed,
          ollama_running: data.ollama_running,
          model_ready: data.model_ready,
        }
        setLocalConfig(cfg)
        if (cfg.enabled && (!cfg.ollama_running || !cfg.model_ready)) {
          setShowSetupModal(true)
        }
      }
    } catch {
      // API not reachable
    }
  }, [])

  useEffect(() => {
    fetchLocalStatus()
  }, [fetchLocalStatus])

  const handleSetupComplete = (config) => {
    if (config) {
      setLocalConfig({
        enabled: config.enabled,
        model_tag: config.model_tag,
        setup_completed: config.setup_completed,
        ollama_running: true,
        model_ready: true,
      })
    } else {
      setLocalConfig(prev => prev ? { ...prev, enabled: false } : null)
    }
    setShowSetupModal(false)
  }

  const handleNewChat = () => {
    if (loading) {
      // A check is in progress — just navigate away; let it finish and auto-save in the background
      setCurrentView('welcome')
      return
    }
    // Nothing running — full reset
    if (abortController) abortController.abort()
    setCurrentView('welcome')
    setFactCheckData(null)
    setIncrementalData(null)
    setError(null)
    setLoading(false)
    setCurrentStep(null)
    setCurrentQuery('')
  }

  const handleSelectSession = (sessionId) => {
    const session = sessions.find(s => s.id === sessionId)
    if (session?.pending) {
      // Still loading — jump back to the live 'active' view
      setCurrentView('active')
    } else {
      setCurrentView(sessionId)
    }
  }

  const handleDeleteSession = (sessionId) => {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId)
      try { localStorage.setItem('ttm-sessions', JSON.stringify(updated)) } catch {}
      return updated
    })
    if (currentView === sessionId) {
      setCurrentView('welcome')
    }
  }

  const handleRunLocally = async (query) => {
    try {
      const res = await fetch('/api/local/status')
      if (res.ok) {
        const data = await res.json()
        if (!data.local_mode_enabled || !data.ollama_running || !data.model_ready) {
          setLocalConfig(prev => ({
            ...prev,
            enabled: data.local_mode_enabled,
            ollama_running: data.ollama_running,
            model_ready: data.model_ready,
          }))
          setShowSetupModal(true)
          return
        }
      }
    } catch {
      setShowSetupModal(true)
      return
    }
    return handleQuerySubmit(query)
  }

  const handleQuerySubmit = async (query) => {
    const sources = getSelectedSources().length > 0 ? getSelectedSources() : ['wikipedia']

    if (abortController) {
      abortController.abort()
      // Remove the orphaned pending session from a previous check that was navigated away from
      const prevId = currentSessionIdRef.current
      if (prevId) {
        setSessions(prev => prev.filter(s => !(s.id === prevId && s.pending)))
      }
    }

    // Create an ID for this session up-front so background completion can find it
    const sessionId = Date.now().toString()
    currentSessionIdRef.current = sessionId

    // Add a pending placeholder to the sidebar immediately
    setSessions(prev => {
      const pending = { id: sessionId, title: query, query, factCheckData: null, pending: true, timestamp: Date.now() }
      return [pending, ...prev].slice(0, 50)
    })

    const controller = new AbortController()
    setAbortController(controller)

    setCurrentQuery(query)
    setCurrentView('active')
    setLoading(true)
    setError(null)
    setFactCheckData(null)
    setProgressUpdates([])
    setCurrentStep(null)
    setIncrementalData({ query, claims: [] })

    try {
      const response = await fetch('/api/factcheck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_n_urls: 1, sources }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      console.log('🔍 Starting fact-check for query:', query)
      console.log('📡 Connected to API stream')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log('✅ Stream completed')
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              console.log(`[${data.type.toUpperCase()}]`, data.message, data.data || '')

              if (data.type === 'plan_generated') {
                console.log('📋 Plan structure received - showing all items with loading states')
                setIncrementalData(prev => {
                  if (!prev) return prev
                  const newData = { ...prev }
                  const claimIndex = (data.data?.claim_index || 1) - 1

                  if (!newData.claims[claimIndex]) {
                    newData.claims[claimIndex] = {
                      text: data.data?.claim_text || `Claim ${claimIndex + 1}`,
                      prerequisites: [],
                      additional_info: [],
                      final_claim: null,
                      final_validation: null
                    }
                  }

                  const claim = newData.claims[claimIndex]

                  // Always overwrite with real text — never keep the "Claim N" placeholder
                  if (data.data?.claim_text) {
                    claim.text = data.data.claim_text
                  }

                  if (data.data?.prerequisites && Array.isArray(data.data.prerequisites)) {
                    claim.prerequisites = data.data.prerequisites.map(() => ({
                      text: '',
                      validation: {
                        status: 'pending',
                        label: null,
                        evidence: null,
                        article_query: null,
                        article_url: null,
                        link: null,
                        error: null
                      }
                    }))
                    // Fill in text after map
                    data.data.prerequisites.forEach((prereqText, i) => {
                      claim.prerequisites[i].text = prereqText
                    })
                    console.log(`  ✓ Created ${claim.prerequisites.length} prerequisite blocks`)
                  }

                  if (data.data?.additional_info && Array.isArray(data.data.additional_info)) {
                    claim.additional_info = data.data.additional_info.map((info) => ({
                      purpose: info.purpose || '',
                      question: info.question || '',
                      answer: null,
                      validation: {
                        status: 'pending',
                        label: null,
                        evidence: null,
                        article_query: null,
                        article_url: null,
                        link: null,
                        error: null
                      }
                    }))
                    console.log(`  ✓ Created ${claim.additional_info.length} additional info blocks`)
                  }

                  return { ...newData }
                })
              }

              if (data.type === 'step' || data.type === 'claim' || data.type === 'prerequisite' ||
                data.type === 'additional_info' || data.type === 'final_claim' || data.type === 'plan_generated') {
                if (data.type === 'step') {
                  console.log(`📋 ${data.message}`)
                } else if (data.type === 'claim') {
                  console.log(`\n📌 ${data.message}`)
                  if (data.data?.claim_text) {
                    console.log(`   Claim: "${data.data.claim_text}"`)
                  }
                }
                setProgressUpdates(prev => [...prev, data])
                setCurrentStep(data)

                setIncrementalData(prev => {
                  if (!prev) return prev
                  const newData = { ...prev }
                  const claimIndex = (data.data?.claim_index || 1) - 1

                  if (!newData.claims[claimIndex]) {
                    newData.claims[claimIndex] = {
                      text: data.data?.claim_text || `Claim ${claimIndex + 1}`,
                      prerequisites: [],
                      additional_info: [],
                      final_claim: null,
                      final_validation: null
                    }
                  }

                  const claim = newData.claims[claimIndex]

                  // Always update claim text when we have real text (overwrite the "Claim N" placeholder)
                  if (data.data?.claim_text) {
                    claim.text = data.data.claim_text
                  }

                  if (!claim.prerequisites) claim.prerequisites = []
                  if (!claim.additional_info) claim.additional_info = []

                  if (data.type === 'prerequisite') {
                    const prereqIndex = (data.data?.index || 1) - 1
                    const status = data.data?.status || 'validating'

                    console.log(`  └─ Prerequisite ${prereqIndex + 1}: ${status}`, data.data?.article_query ? `→ Article: ${data.data.article_query}` : '')

                    while (claim.prerequisites.length <= prereqIndex) {
                      claim.prerequisites.push({ text: '', validation: { status: 'pending' } })
                    }

                    let prereq = claim.prerequisites[prereqIndex]
                    if (!prereq) {
                      prereq = {
                        text: data.data?.text || data.message.replace(/^Validating prerequisite \d+\/\d+:?\s*/, '').trim(),
                        validation: { status: 'validating', label: null, evidence: null, article_query: null, article_url: null, link: null, error: null }
                      }
                      claim.prerequisites[prereqIndex] = prereq
                    } else {
                      if (data.data?.text && !prereq.text) prereq.text = data.data.text
                    }

                    if (status === 'validating' || status === 'selecting_article') {
                      prereq.validation.status = 'validating'
                      if (data.data?.article_query) prereq.validation.article_query = data.data.article_query
                      if (data.data?.text && !prereq.text) prereq.text = data.data.text
                    } else if (status === 'fetching_article') {
                      prereq.validation.status = 'validating'
                      prereq.validation.article_query = data.data?.article_query || prereq.validation.article_query
                    } else if (status === 'sources_fetched') {
                      prereq.validation.found_sources = data.data?.found_sources || []
                      prereq.validation.skipped_sources = data.data?.skipped_sources || []
                    } else if (status === 'factchecking') {
                      prereq.validation.status = 'validating'
                    } else if (status === 'source_result') {
                      if (!prereq.validation.live_source_results) prereq.validation.live_source_results = []
                      const alreadyHas = prereq.validation.live_source_results.some(r => r.source === data.data?.source)
                      if (!alreadyHas) {
                        prereq.validation.live_source_results = [
                          ...prereq.validation.live_source_results,
                          { source: data.data?.source, label: data.data?.label }
                        ]
                      }
                    } else if (status === 'validated') {
                      const label = data.data?.label || null
                      if (label === 'True') {
                        prereq.validation.status = 'validated'
                        prereq.validation.label = label
                      } else {
                        prereq.validation.status = 'failed'
                        prereq.validation.label = label
                        prereq.validation.error = `Prerequisite validation failed: ${label}`
                      }
                      if (data.data?.per_source_results) {
                        prereq.validation.per_source_results = data.data.per_source_results
                      }
                    } else if (status === 'failed') {
                      prereq.validation.status = 'failed'
                      prereq.validation.error = data.message
                      prereq.validation.label = data.data?.label || null
                      if (data.data?.per_source_results) {
                        prereq.validation.per_source_results = data.data.per_source_results
                      }
                    }

                    if (!prereq.validation) {
                      prereq.validation = { status: status === 'validating' ? 'validating' : 'pending', label: null, evidence: null, article_query: null, article_url: null, link: null, error: null }
                    }
                  }

                  if (data.type === 'additional_info') {
                    const infoIndex = (data.data?.index || 1) - 1
                    const status = data.data?.status || 'validating'

                    while (claim.additional_info.length <= infoIndex) {
                      claim.additional_info.push({ purpose: '', question: '', answer: null, validation: { status: 'pending' } })
                    }

                    let info = claim.additional_info[infoIndex]
                    if (!info) {
                      info = {
                        purpose: data.data?.purpose || data.message.replace(/^Extracting info \d+\/\d+:?\s*/, '').trim(),
                        question: data.data?.question || '',
                        answer: null,
                        validation: { status: 'validating', label: null, evidence: null, article_query: null, article_url: null, link: null, error: null }
                      }
                      claim.additional_info[infoIndex] = info
                    } else {
                      if (data.data?.purpose && !info.purpose) info.purpose = data.data.purpose
                      if (data.data?.question && !info.question) info.question = data.data.question
                    }

                    if (status === 'validating' || status === 'selecting_article') {
                      info.validation.status = 'validating'
                      if (data.data?.article_query) info.validation.article_query = data.data.article_query
                      if (data.data?.purpose && !info.purpose) info.purpose = data.data.purpose
                      if (data.data?.question && !info.question) info.question = data.data.question
                    } else if (status === 'fetching_article') {
                      info.validation.status = 'validating'
                      info.validation.article_query = data.data?.article_query || info.validation.article_query
                    } else if (status === 'extracting') {
                      info.validation.status = 'validating'
                    } else if (status === 'validated') {
                      info.validation.status = 'validated'
                      info.answer = data.data?.answer || info.answer
                      if (data.data?.evidence) info.validation.evidence = data.data.evidence
                      if (data.data?.link) info.validation.link = data.data.link
                      if (data.data?.article_url) info.validation.article_url = data.data.article_url
                    } else if (status === 'failed') {
                      info.validation.status = 'failed'
                      info.validation.error = data.message
                    }

                    if (!info.validation) {
                      info.validation = { status: status === 'validating' ? 'validating' : 'pending', label: null, evidence: null, article_query: null, article_url: null, link: null, error: null }
                    }
                  }

                  if (data.type === 'final_claim') {
                    const status = data.data?.status || 'validating'

                    if (status === 'generating') {
                      claim.final_claim = null
                      claim.final_validation = { status: 'validating' }
                    } else if (status === 'generated') {
                      claim.final_claim = data.data?.final_claim || data.message.split(':').slice(1).join(':').trim()
                      claim.final_validation = { status: 'validating' }
                    } else if (status === 'selecting_article' || status === 'fetching_article') {
                      if (!claim.final_validation) claim.final_validation = { status: 'validating' }
                      claim.final_validation.article_query = data.data?.article_query || claim.final_validation.article_query
                    } else if (status === 'sources_fetched') {
                      if (!claim.final_validation) claim.final_validation = { status: 'validating' }
                      claim.final_validation.found_sources = data.data?.found_sources || []
                      claim.final_validation.skipped_sources = data.data?.skipped_sources || []
                    } else if (status === 'factchecking') {
                      if (!claim.final_validation) claim.final_validation = { status: 'validating' }
                    } else if (status === 'source_result') {
                      if (!claim.final_validation) claim.final_validation = { status: 'validating' }
                      if (!claim.final_validation.live_source_results) claim.final_validation.live_source_results = []
                      const alreadyHas = claim.final_validation.live_source_results.some(r => r.source === data.data?.source)
                      if (!alreadyHas) {
                        claim.final_validation.live_source_results = [
                          ...claim.final_validation.live_source_results,
                          { source: data.data?.source, label: data.data?.label }
                        ]
                      }
                    } else if (status === 'validated') {
                      claim.final_validation = {
                        status: 'validated',
                        label: data.data?.label || null,
                        evidence: null,
                        article_query: claim.final_validation?.article_query || null,
                        article_url: null,
                        link: null,
                        error: null,
                        per_source_results: data.data?.per_source_results || null,
                      }
                    } else if (status === 'failed') {
                      claim.final_validation = {
                        status: 'failed',
                        error: data.message,
                        article_query: claim.final_validation?.article_query || null,
                        per_source_results: data.data?.per_source_results || null,
                      }
                    }
                  }

                  return { ...newData }
                })
              }

              if (data.type === 'complete') {
                console.log('✅ Fact-checking completed!')
                const completedData = data.data
                setFactCheckData(completedData)
                setLoading(false)
                setCurrentStep(null)

                // Update the pending session that was created at the start of this check
                const sid = currentSessionIdRef.current
                setSessions(prev => {
                  const updated = prev.map(s =>
                    s.id === sid
                      ? { ...s, factCheckData: completedData, pending: false }
                      : s
                  )
                  // Persist only completed sessions
                  try { localStorage.setItem('ttm-sessions', JSON.stringify(updated.filter(s => !s.pending))) } catch {}
                  return updated
                })
              }

              if (data.type === 'error') {
                console.error('❌ Error:', data.message)
                setError(data.message)
                setLoading(false)
                setCurrentStep(null)
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Request aborted')
        return
      }
      console.error('❌ Request error:', err)
      setError(err.message)
      setLoading(false)
      setCurrentStep(null)
    } finally {
      setAbortController(null)
    }
  }

  // Determine what to show in the main area
  const isViewingPastSession = currentView !== 'welcome' && currentView !== 'active'
  const viewingSession = isViewingPastSession ? sessions.find(s => s.id === currentView) : null
  const displayData = isViewingPastSession
    ? viewingSession?.factCheckData
    : (factCheckData || incrementalData)
  const displayQuery = isViewingPastSession ? viewingSession?.query : currentQuery
  const isLive = currentView === 'active' && loading

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={currentView}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        loading={loading}
      />

      <div className="main-content">
        {/* Persistent top bar — always visible */}
        <TopBar
          localConfig={localConfig}
          onOpenSetup={() => setShowSetupModal(true)}
          onModeChange={handleSetupComplete}
          sources={sources}
          onToggleSource={handleToggleSource}
          sourceWeights={sourceWeights}
          onWeightsChange={setSourceWeights}
          isLive={isLive}
          viewingTimestamp={isViewingPastSession && viewingSession ? viewingSession.timestamp : null}
        />

        <AnimatePresence mode="wait">
          {/* ── Welcome / landing ── */}
          {currentView === 'welcome' ? (
            <motion.div
              key="welcome"
              className="welcome-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="welcome-center">
                <h1 className="welcome-title">Ready when you are.</h1>
                <div className="welcome-input">
                  <QueryInput
                    onSubmit={handleQuerySubmit}
                    onRunLocally={handleRunLocally}
                    disabled={loading}
                    localConfig={localConfig}
                  />
                </div>
              </div>
            </motion.div>
          ) : (
            /* ── Chat conversation view ── */
            <motion.div
              key={currentView}
              className="chat-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* Scrollable message list */}
              <div className="chat-results">
                <div className="chat-messages-list">

                  {/* User message bubble */}
                  {displayQuery && (
                    <motion.div
                      className="chat-msg user-msg"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <div className="user-bubble">
                        <p>{displayQuery}</p>
                      </div>
                    </motion.div>
                  )}

                  {/* AI message bubble */}
                  <motion.div
                    className="chat-msg ai-msg"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: 0.1 }}
                  >
                    <div className="ai-avatar" aria-hidden="true">🔍</div>
                    <div className="ai-bubble">
                      {error && (
                        <div className="error-container">
                          <p>Error: {error}</p>
                        </div>
                      )}

                      <AnimatePresence mode="wait">
                        {isLive ? (
                          <motion.div
                            key="thinking"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0, scale: 0.98 }}
                            transition={{ duration: 0.2 }}
                          >
                            <ThinkingPanel
                              progressUpdates={progressUpdates}
                              incrementalData={incrementalData}
                              currentStep={currentStep}
                            />
                          </motion.div>
                        ) : displayData ? (
                          <motion.div
                            key="results"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3 }}
                          >
                            <FactCheckTree
                              data={displayData}
                              isLoading={false}
                              currentStep={null}
                              sourceWeights={sourceWeights}
                            />
                            {displayData.total_time && (
                              <div className="result-footer">
                                Completed in {displayData.total_time.toFixed(1)}s
                              </div>
                            )}
                          </motion.div>
                        ) : null}
                      </AnimatePresence>
                    </div>
                  </motion.div>

                </div>
                <div ref={resultsEndRef} />
              </div>

              {/* Bottom input bar: hidden while a check is running, hidden for past sessions */}
              {!isViewingPastSession && !loading && (
                <div className="chat-input-bar">
                  <QueryInput
                    onSubmit={handleQuerySubmit}
                    onRunLocally={handleRunLocally}
                    disabled={loading}
                    localConfig={localConfig}
                  />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <LocalSetupModal
        isOpen={showSetupModal}
        onClose={() => setShowSetupModal(false)}
        onSetupComplete={handleSetupComplete}
        currentConfig={localConfig}
      />
    </div>
  )
}

export default App
