import React, { useState } from 'react'
import QueryInput from './components/QueryInput'
import FactCheckTree from './components/FactCheckTree'
import ProgressDisplay from './components/ProgressDisplay'
import './App.css'

function App() {
  const [factCheckData, setFactCheckData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [progressUpdates, setProgressUpdates] = useState([])
  const [currentStep, setCurrentStep] = useState(null)
  const [incrementalData, setIncrementalData] = useState(null)
  const [abortController, setAbortController] = useState(null)

  const handleQuerySubmit = async (query, sources = ['wikipedia']) => {
    // Cancel any existing request
    if (abortController) {
      abortController.abort()
    }
    
    // Create new abort controller for this request
    const controller = new AbortController()
    setAbortController(controller)
    
    setLoading(true)
    setError(null)
    setFactCheckData(null)
    setProgressUpdates([])
    setCurrentStep(null)
    setIncrementalData({ query, claims: [] })

    try {
      const response = await fetch('/api/factcheck', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, top_n_urls: 1, sources }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      console.log('🔍 Starting fact-check for query:', query)
      console.log('📡 Connected to API stream')
      
      // Handle Server-Sent Events stream
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
              
              // Console logging for debugging
              console.log(`[${data.type.toUpperCase()}]`, data.message, data.data || '')
              
              // Handle plan generation - create all structure immediately
              if (data.type === 'plan_generated') {
                console.log('📋 Plan structure received - showing all items with loading states')
                setIncrementalData(prev => {
                  if (!prev) return prev
                  
                  const newData = { ...prev }
                  const claimIndex = (data.data?.claim_index || 1) - 1
                  
                  // Ensure claim exists
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
                  
                  // Create all prerequisites with pending status immediately
                  if (data.data?.prerequisites && Array.isArray(data.data.prerequisites)) {
                    claim.prerequisites = data.data.prerequisites.map((prereqText, i) => ({
                      text: prereqText,
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
                    console.log(`  ✓ Created ${claim.prerequisites.length} prerequisite blocks`)
                  }
                  
                  // Create all additional info items with pending status immediately
                  if (data.data?.additional_info && Array.isArray(data.data.additional_info)) {
                    claim.additional_info = data.data.additional_info.map((info, i) => ({
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
              
              // Update progress (also handle plan_generated for updates)
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
                
                // Update incremental tree structure
                setIncrementalData(prev => {
                  if (!prev) return prev
                  
                  const newData = { ...prev }
                  const claimIndex = (data.data?.claim_index || 1) - 1
                  
                  // Ensure claim exists
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
                  
                  // Ensure prerequisites array exists even if empty
                  if (!claim.prerequisites) {
                    claim.prerequisites = []
                  }
                  
                  // Ensure additional_info array exists even if empty
                  if (!claim.additional_info) {
                    claim.additional_info = []
                  }
                  
                    // Handle prerequisite updates
                  if (data.type === 'prerequisite') {
                    const prereqIndex = (data.data?.index || 1) - 1
                    const status = data.data?.status || 'validating'
                    
                    console.log(`  └─ Prerequisite ${prereqIndex + 1}: ${status}`, data.data?.article_query ? `→ Article: ${data.data.article_query}` : '')
                    
                    // Ensure prerequisites array is large enough
                    while (claim.prerequisites.length <= prereqIndex) {
                      claim.prerequisites.push({
                        text: '',
                        validation: { status: 'pending' }
                      })
                    }
                    
                    // Find or update prerequisite
                    let prereq = claim.prerequisites[prereqIndex]
                    if (!prereq) {
                      prereq = {
                        text: data.data?.text || data.message.replace(/^Validating prerequisite \d+\/\d+:?\s*/, '').trim(),
                        validation: {
                          status: 'validating',
                          label: null,
                          evidence: null,
                          article_query: null,
                          article_url: null,
                          link: null,
                          error: null
                        }
                      }
                      claim.prerequisites[prereqIndex] = prereq
                      console.log(`    📝 Created prerequisite block: "${prereq.text}"`)
                    } else {
                      // Update existing prerequisite text if we have it
                      if (data.data?.text && !prereq.text) {
                        prereq.text = data.data.text
                      }
                    }
                    
                    // Update validation status and details
                    if (status === 'validating' || status === 'selecting_article') {
                      prereq.validation.status = 'validating'
                      if (data.data?.article_query) {
                        prereq.validation.article_query = data.data.article_query
                        console.log(`    🔍 Article selected: ${data.data.article_query}`)
                      }
                      if (data.data?.text && !prereq.text) {
                        prereq.text = data.data.text
                      }
                    } else if (status === 'fetching_article') {
                      prereq.validation.status = 'validating'
                      prereq.validation.article_query = data.data?.article_query || prereq.validation.article_query
                      console.log(`    📥 Fetching article: ${prereq.validation.article_query}`)
                    } else if (status === 'factchecking') {
                      prereq.validation.status = 'validating'
                      console.log(`    🔎 Fact-checking prerequisite...`)
                    } else if (status === 'validated') {
                      // Only mark as validated if label is "True"
                      const label = data.data?.label || null
                      if (label === 'True') {
                        prereq.validation.status = 'validated'
                        prereq.validation.label = label
                        console.log(`    ✅ Prerequisite validated: ${label}`)
                      } else {
                        // If label is "False", mark as failed
                        prereq.validation.status = 'failed'
                        prereq.validation.label = label
                        prereq.validation.error = `Prerequisite validation failed: ${label}`
                        console.log(`    ❌ Prerequisite failed: ${label}`)
                      }
                    } else if (status === 'failed') {
                      prereq.validation.status = 'failed'
                      prereq.validation.error = data.message
                      prereq.validation.label = data.data?.label || null
                      console.log(`    ❌ Prerequisite failed: ${data.message}`)
                    }
                    
                    // Ensure validation object exists
                    if (!prereq.validation) {
                      prereq.validation = {
                        status: status === 'validating' ? 'validating' : 'pending',
                        label: null,
                        evidence: null,
                        article_query: null,
                        article_url: null,
                        link: null,
                        error: null
                      }
                    }
                  }
                  
                  // Handle additional info updates
                  if (data.type === 'additional_info') {
                    const infoIndex = (data.data?.index || 1) - 1
                    const status = data.data?.status || 'validating'
                    
                    console.log(`  └─ Additional Info ${infoIndex + 1}: ${status}`, data.data?.purpose ? `(${data.data.purpose})` : '')
                    
                    // Ensure additional_info array is large enough
                    while (claim.additional_info.length <= infoIndex) {
                      claim.additional_info.push({
                        purpose: '',
                        question: '',
                        answer: null,
                        validation: { status: 'pending' }
                      })
                    }
                    
                    // Find or update additional info
                    let info = claim.additional_info[infoIndex]
                    if (!info) {
                      info = {
                        purpose: data.data?.purpose || data.message.replace(/^Extracting info \d+\/\d+:?\s*/, '').trim(),
                        question: data.data?.question || '',
                        answer: null,
                        validation: {
                          status: 'validating',
                          label: null,
                          evidence: null,
                          article_query: null,
                          article_url: null,
                          link: null,
                          error: null
                        }
                      }
                      claim.additional_info[infoIndex] = info
                      console.log(`    📝 Created info block: "${info.purpose}"`)
                    } else {
                      // Update existing info if we have it
                      if (data.data?.purpose && !info.purpose) {
                        info.purpose = data.data.purpose
                      }
                      if (data.data?.question && !info.question) {
                        info.question = data.data.question
                      }
                    }
                    
                    // Update validation status and details
                    if (status === 'validating' || status === 'selecting_article') {
                      info.validation.status = 'validating'
                      if (data.data?.article_query) {
                        info.validation.article_query = data.data.article_query
                        console.log(`    🔍 Article selected: ${data.data.article_query}`)
                      }
                      if (data.data?.purpose && !info.purpose) {
                        info.purpose = data.data.purpose
                      }
                      if (data.data?.question && !info.question) {
                        info.question = data.data.question
                      }
                    } else if (status === 'fetching_article') {
                      info.validation.status = 'validating'
                      info.validation.article_query = data.data?.article_query || info.validation.article_query
                      console.log(`    📥 Fetching article: ${info.validation.article_query}`)
                    } else if (status === 'extracting') {
                      info.validation.status = 'validating'
                      console.log(`    🔎 Extracting answer from article...`)
                    } else if (status === 'validated') {
                      info.validation.status = 'validated'
                      info.answer = data.data?.answer || info.answer
                      // Update evidence and link if provided
                      if (data.data?.evidence) {
                        info.validation.evidence = data.data.evidence
                      }
                      if (data.data?.link) {
                        info.validation.link = data.data.link
                      }
                      if (data.data?.article_url) {
                        info.validation.article_url = data.data.article_url
                      }
                      console.log(`    ✅ Info extracted: "${info.answer?.substring(0, 50)}${info.answer?.length > 50 ? '...' : ''}"`)
                    } else if (status === 'failed') {
                      info.validation.status = 'failed'
                      info.validation.error = data.message
                      console.log(`    ❌ Info extraction failed: ${data.message}`)
                    }
                    
                    // Ensure validation object exists
                    if (!info.validation) {
                      info.validation = {
                        status: status === 'validating' ? 'validating' : 'pending',
                        label: null,
                        evidence: null,
                        article_query: null,
                        article_url: null,
                        link: null,
                        error: null
                      }
                    }
                  }
                  
                  // Handle final claim updates
                  if (data.type === 'final_claim') {
                    const status = data.data?.status || 'validating'
                    
                    console.log(`  └─ Final Claim: ${status}`)
                    
                    if (status === 'generating') {
                      claim.final_claim = null
                      claim.final_validation = { status: 'validating' }
                      console.log(`    🔄 Generating final claim from template...`)
                    } else if (status === 'generated') {
                      claim.final_claim = data.data?.final_claim || data.message.split(':').slice(1).join(':').trim()
                      claim.final_validation = { status: 'validating' }
                      console.log(`    📝 Final claim generated: "${claim.final_claim}"`)
                    } else if (status === 'selecting_article' || status === 'fetching_article') {
                      if (!claim.final_validation) {
                        claim.final_validation = { status: 'validating' }
                      }
                      claim.final_validation.article_query = data.data?.article_query || claim.final_validation.article_query
                      if (status === 'selecting_article') {
                        console.log(`    🔍 Selecting article for final claim...`)
                      } else {
                        console.log(`    📥 Fetching article: ${claim.final_validation.article_query}`)
                      }
                    } else if (status === 'factchecking') {
                      if (!claim.final_validation) {
                        claim.final_validation = { status: 'validating' }
                      }
                      console.log(`    🔎 Fact-checking final claim...`)
                    } else if (status === 'validated') {
                      claim.final_validation = {
                        status: 'validated',
                        label: data.data?.label || null,
                        evidence: null,
                        article_query: claim.final_validation?.article_query || null,
                        article_url: null,
                        link: null,
                        error: null
                      }
                      console.log(`    ✅ Final claim validated: ${data.data?.label || 'N/A'}`)
                    } else if (status === 'failed') {
                      claim.final_validation = {
                        status: 'failed',
                        error: data.message,
                        article_query: claim.final_validation?.article_query || null
                      }
                      console.log(`    ❌ Final claim failed: ${data.message}`)
                    }
                  }
                  
                  return { ...newData }
                })
              }
              
              // Handle completion
              if (data.type === 'complete') {
                console.log('✅ Fact-checking completed!')
                console.log('📊 Final data:', data.data)
                if (data.data?.total_time) {
                  console.log(`⏱️  Total time: ${data.data.total_time.toFixed(2)}s`)
                }
                setFactCheckData(data.data)
                setLoading(false)
                setCurrentStep(null)
              }
              
              // Handle errors
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
      // Don't show error if request was aborted
      if (err.name === 'AbortError') {
        console.log('Request aborted')
        return
      }
      console.error('❌ Request error:', err)
      setError(err.message)
      setLoading(false)
      setCurrentStep(null)
    } finally {
      // Clear abort controller when done
      setAbortController(null)
    }
  }

  return (
    <div className="app">
      <div className="app-container">
        <header className="app-header">
          <h1>The Truth Machine</h1>
          <p>Fact-check claims against Wikipedia with AI-powered validation</p>
        </header>

        <QueryInput onSubmit={handleQuerySubmit} disabled={loading} />

        {error && (
          <div className="error-container">
            <p>❌ Error: {error}</p>
          </div>
        )}

        {/* Show incremental tree while loading, or final tree when complete */}
        {(incrementalData || factCheckData) && (
          <FactCheckTree 
            data={factCheckData || incrementalData} 
            isLoading={loading}
            currentStep={currentStep}
          />
        )}
      </div>
    </div>
  )
}

export default App

