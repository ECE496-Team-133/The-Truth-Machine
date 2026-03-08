import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './LocalSetupModal.css'

const STEPS = ['hardware', 'model', 'ollama', 'pull', 'done']

function LocalSetupModal({ isOpen, onClose, onSetupComplete, currentConfig }) {
  const [step, setStep] = useState('hardware')
  const [hardware, setHardware] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [allModels, setAllModels] = useState([])
  const [installedModels, setInstalledModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [ollamaStatus, setOllamaStatus] = useState({ installed: false, running: false })
  const [modelReady, setModelReady] = useState(false)
  const [modelAlreadyInstalled, setModelAlreadyInstalled] = useState(false)
  const [pulling, setPulling] = useState(false)
  const [pullError, setPullError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const normalize = (s) => {
    s = (s || '').trim().toLowerCase()
    return s.endsWith(':latest') ? s.slice(0, -7) : s
  }

  const isModelInList = (modelTag, models) => {
    const target = normalize(modelTag)
    return models.some(m => {
      const name = normalize(m.name || m.model || '')
      return name === target
        || name === target.split(':')[0]
        || target === name.split(':')[0]
    })
  }

  // Always start fresh from hardware step when modal opens
  useEffect(() => {
    if (!isOpen) return
    setStep('hardware')
    setError(null)
    setPullError(null)
    setModelReady(false)
    setModelAlreadyInstalled(false)
    // Pre-select the current model if configured
    if (currentConfig?.model_tag) {
      setSelectedModel(currentConfig.model_tag)
    }
    detectHardware()
  }, [isOpen])

  const detectHardware = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/local/hardware')
      if (!res.ok) throw new Error('Failed to detect hardware')
      const data = await res.json()
      setHardware(data.hardware)
      setRecommendation(data.recommendation)
      setAllModels(data.all_models || [])
      // Only set selected model if not already set from config
      setSelectedModel(prev => prev || data.recommendation.model_tag)

      // Also fetch installed models for badges
      try {
        const modelsRes = await fetch('/api/local/ollama/models')
        const modelsData = await modelsRes.json()
        setInstalledModels(modelsData.models || [])
      } catch {
        setInstalledModels([])
      }

      setStep('model')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const checkOllama = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/local/status')
      if (!res.ok) throw new Error('Failed to check status')
      const data = await res.json()
      setOllamaStatus({
        installed: data.ollama_installed,
        running: data.ollama_running,
      })

      if (data.ollama_running) {
        // Refresh installed models and go to pull step (which checks automatically)
        try {
          const modelsRes = await fetch('/api/local/ollama/models')
          const modelsData = await modelsRes.json()
          setInstalledModels(modelsData.models || [])
          const installed = isModelInList(selectedModel, modelsData.models || [])
          setModelAlreadyInstalled(installed)
        } catch {
          setModelAlreadyInstalled(false)
        }
        setStep('pull')
      } else if (data.ollama_installed) {
        setStep('ollama')
      } else {
        setStep('ollama')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const startOllama = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/local/ollama/start', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setOllamaStatus(prev => ({ ...prev, running: true }))
        // Check installed models after starting
        try {
          const modelsRes = await fetch('/api/local/ollama/models')
          const modelsData = await modelsRes.json()
          setInstalledModels(modelsData.models || [])
          const installed = isModelInList(selectedModel, modelsData.models || [])
          setModelAlreadyInstalled(installed)
        } catch {
          setModelAlreadyInstalled(false)
        }
        setStep('pull')
      } else {
        setError(data.message)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const pullModel = async () => {
    setPulling(true)
    setPullError(null)
    try {
      const res = await fetch('/api/local/ollama/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_tag: selectedModel }),
      })
      const data = await res.json()
      if (data.success) {
        setModelReady(true)
        setModelAlreadyInstalled(true)
        setStep('done')
      } else {
        setPullError(data.message)
      }
    } catch (e) {
      setPullError(e.message)
    } finally {
      setPulling(false)
    }
  }

  const enableLocalMode = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/local/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_tag: selectedModel }),
      })
      const data = await res.json()
      if (data.success) {
        onSetupComplete(data.config)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const disableLocalMode = async () => {
    setLoading(true)
    try {
      await fetch('/api/local/disable', { method: 'POST' })
      onSetupComplete(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setStep('hardware')
    setError(null)
    setPullError(null)
    onClose()
  }

  const stepIndex = STEPS.indexOf(step)

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        className="local-modal-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={handleClose}
      >
        <motion.div
          className="local-modal"
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 40, scale: 0.95 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={e => e.stopPropagation()}
        >
          <button className="local-modal-close" onClick={handleClose}>×</button>

          <div className="local-modal-header">
            <h2>Local Mode Setup</h2>
            <p>Run inference on your own hardware</p>
          </div>

          {/* Progress bar */}
          <div className="local-modal-progress">
            {STEPS.map((s, i) => (
              <div key={s} className={`progress-dot ${i <= stepIndex ? 'active' : ''} ${i === stepIndex ? 'current' : ''}`} />
            ))}
          </div>

          <div className="local-modal-body">
            {error && (
              <div className="local-modal-error">{error}</div>
            )}

            {/* Step: Hardware Detection */}
            {step === 'hardware' && (
              <div className="local-step">
                <h3>Detecting Hardware</h3>
                {loading ? (
                  <div className="local-step-loading">
                    <div className="local-spinner" />
                    <p>Scanning your system...</p>
                  </div>
                ) : (
                  <button className="local-btn local-btn-primary" onClick={detectHardware}>
                    Retry Detection
                  </button>
                )}
              </div>
            )}

            {/* Step: Model Selection */}
            {step === 'model' && hardware && (
              <div className="local-step">
                <h3>Your Hardware</h3>
                <div className="hardware-card">
                  <div className="hw-row"><span className="hw-label">CPU</span><span className="hw-value">{hardware.cpu_name}</span></div>
                  <div className="hw-row"><span className="hw-label">RAM</span><span className="hw-value">{hardware.ram_gb} GB</span></div>
                  <div className="hw-row"><span className="hw-label">GPU</span><span className="hw-value">
                    {hardware.gpu.vendor === 'none' ? 'None detected' : `${hardware.gpu.name} (${hardware.gpu.vram_gb} GB)`}
                    {hardware.gpu.metal_support && <span className="hw-badge">Metal</span>}
                  </span></div>
                  <div className="hw-row"><span className="hw-label">Arch</span><span className="hw-value">{hardware.arch}</span></div>
                </div>

                <h3>Recommended Model</h3>
                <div className="model-recommendation">
                  <div className="model-rec-main">
                    <span className="model-tag">{recommendation.model_tag}</span>
                    <span className="model-desc">{recommendation.description}</span>
                  </div>
                  <span className="model-reason">{recommendation.reason}</span>
                </div>

                <h3>All Compatible Models</h3>
                <div className="model-list">
                  {allModels.filter(m => m.compatible).map(m => (
                    <label
                      key={m.model_tag}
                      className={`model-option ${selectedModel === m.model_tag ? 'selected' : ''}`}
                    >
                      <input
                        type="radio"
                        name="model"
                        value={m.model_tag}
                        checked={selectedModel === m.model_tag}
                        onChange={() => setSelectedModel(m.model_tag)}
                      />
                      <div className="model-option-info">
                        <span className="model-option-tag">
                          {m.model_tag}
                          {isModelInList(m.model_tag, installedModels) && (
                            <span className="hw-badge model-installed-badge">Installed</span>
                          )}
                        </span>
                        <span className="model-option-desc">{m.description}</span>
                      </div>
                      <span className="model-option-size">{m.param_size}</span>
                    </label>
                  ))}
                </div>

                <button className="local-btn local-btn-primary" onClick={checkOllama} disabled={loading}>
                  {loading ? 'Checking...' : 'Continue'}
                </button>
              </div>
            )}

            {/* Step: Ollama Check */}
            {step === 'ollama' && (
              <div className="local-step">
                <h3>Ollama Runtime</h3>
                <p className="local-step-desc">
                  Ollama runs open-source models locally. It's required for local inference.
                </p>
                <div className="ollama-status">
                  <div className="ollama-row">
                    <span>Installed</span>
                    <span className={ollamaStatus.installed ? 'status-ok' : 'status-no'}>
                      {ollamaStatus.installed ? 'Yes' : 'No'}
                    </span>
                  </div>
                  <div className="ollama-row">
                    <span>Running</span>
                    <span className={ollamaStatus.running ? 'status-ok' : 'status-no'}>
                      {ollamaStatus.running ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>

                {!ollamaStatus.installed && (
                  <div className="ollama-install-guide">
                    <p>Install Ollama first:</p>
                    <code>brew install ollama</code>
                    <p className="local-step-desc">Or download from <a href="https://ollama.com" target="_blank" rel="noreferrer">ollama.com</a></p>
                    <button className="local-btn local-btn-secondary" onClick={checkOllama} disabled={loading}>
                      {loading ? 'Checking...' : 'I\'ve installed it — check again'}
                    </button>
                  </div>
                )}

                {ollamaStatus.installed && !ollamaStatus.running && (
                  <div className="ollama-start-guide">
                    <p>Ollama is installed but not running.</p>
                    <button className="local-btn local-btn-primary" onClick={startOllama} disabled={loading}>
                      {loading ? 'Starting...' : 'Start Ollama'}
                    </button>
                    <p className="local-step-desc">Or run <code>ollama serve</code> in your terminal.</p>
                    <button className="local-btn local-btn-secondary" onClick={checkOllama} disabled={loading}>
                      {loading ? 'Checking...' : 'Check again'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Step: Pull Model */}
            {step === 'pull' && (
              <div className="local-step">
                {modelAlreadyInstalled ? (
                  <>
                    <div className="model-installed-check">
                      <div className="done-icon">&#10003;</div>
                      <h3>Model Already Installed</h3>
                    </div>
                    <p className="local-step-desc">
                      <strong>{selectedModel}</strong> is already downloaded and ready to use.
                    </p>
                    <button className="local-btn local-btn-primary" onClick={() => { setModelReady(true); setStep('done') }}>
                      Continue
                    </button>
                  </>
                ) : (
                  <>
                    <h3>Download Model</h3>
                    <p className="local-step-desc">
                      Model <strong>{selectedModel}</strong> needs to be downloaded. This is a one-time download.
                    </p>
                    {pullError && (
                      <div className="local-modal-error">{pullError}</div>
                    )}
                    {pulling ? (
                      <div className="local-step-loading">
                        <div className="local-spinner" />
                        <p>Downloading <strong>{selectedModel}</strong>...</p>
                        <p className="local-step-desc">This may take several minutes depending on your connection.</p>
                      </div>
                    ) : (
                      <button className="local-btn local-btn-primary" onClick={pullModel}>
                        Download {selectedModel}
                      </button>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Step: Done */}
            {step === 'done' && (
              <div className="local-step local-step-done">
                <div className="done-icon">&#10003;</div>
                <h3>Ready to Go</h3>
                <p className="local-step-desc">
                  Model <strong>{selectedModel}</strong> is installed and Ollama is running.
                </p>
                <div className="done-actions">
                  {currentConfig?.enabled && currentConfig?.model_tag === selectedModel ? (
                    <>
                      <button className="local-btn local-btn-primary" onClick={handleClose}>
                        Done
                      </button>
                      <button className="local-btn local-btn-danger" onClick={disableLocalMode} disabled={loading}>
                        {loading ? 'Switching...' : 'Switch to API Mode'}
                      </button>
                    </>
                  ) : (
                    <button className="local-btn local-btn-primary" onClick={enableLocalMode} disabled={loading}>
                      {loading ? 'Activating...' : 'Activate Local Mode'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default LocalSetupModal
