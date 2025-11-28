'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
}

interface NavigationStep {
  action: string
  selector?: string
  value?: string
  name?: string
  description?: string
}

interface FormPage {
  id: number
  form_name: string
  url: string
  network_id: number
  navigation_steps: NavigationStep[]
  is_root: boolean
  parent_form_id: number | null
  parent_form_name?: string
  children?: FormPage[]
  created_at: string
}

interface SessionStatus {
  session: {
    id: number
    status: string
    pages_crawled: number
    forms_found: number
    error_message: string | null
    started_at: string | null
    completed_at: string | null
  }
  forms: FormPage[]
}

interface DiscoveryQueueItem {
  networkId: number
  networkName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  sessionId?: number
  pagesSearched: number
  formsFound: number
  errorMessage?: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeProjectName, setActiveProjectName] = useState<string | null>(null)
  
  const [networks, setNetworks] = useState<Network[]>([])
  const [selectedNetworkIds, setSelectedNetworkIds] = useState<number[]>([])
  const [loadingNetworks, setLoadingNetworks] = useState(false)
  
  const [formPages, setFormPages] = useState<FormPage[]>([])
  const [loadingFormPages, setLoadingFormPages] = useState(false)
  const [sortField, setSortField] = useState<'name' | 'date'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  
  const [headless, setHeadless] = useState(false)
  
  // Sequential discovery state
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [discoveryQueue, setDiscoveryQueue] = useState<DiscoveryQueueItem[]>([])
  const [currentNetworkIndex, setCurrentNetworkIndex] = useState<number>(-1)
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const shouldContinueRef = useRef<boolean>(false)
  
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingFormPage, setEditingFormPage] = useState<FormPage | null>(null)
  const [editFormName, setEditFormName] = useState('')
  const [editNavigationSteps, setEditNavigationSteps] = useState<NavigationStep[]>([])
  const [savingFormPage, setSavingFormPage] = useState(false)
  
  const [showDeleteStepConfirm, setShowDeleteStepConfirm] = useState(false)
  const [stepToDeleteIndex, setStepToDeleteIndex] = useState<number | null>(null)
  
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [formPageToDelete, setFormPageToDelete] = useState<FormPage | null>(null)
  const [deletingFormPage, setDeletingFormPage] = useState(false)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    const storedProjectId = localStorage.getItem('active_project_id')
    const storedProjectName = localStorage.getItem('active_project_name')
    
    if (!storedToken) {
      window.location.href = '/login'
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
    setActiveProjectId(storedProjectId)
    setActiveProjectName(storedProjectName)
    
    if (storedProjectId) {
      loadNetworks(storedProjectId, storedToken)
      loadFormPages(storedProjectId, storedToken)
      checkActiveSessions(storedProjectId, storedToken)
    }
  }, [])

  // Check for active/running sessions on page load
  const checkActiveSessions = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(
        `/api/form-pages/projects/${projectId}/active-sessions`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const activeSessions = await response.json()
        
        if (activeSessions.length > 0) {
          // There are active sessions - restore discovery state
          setIsDiscovering(true)
          shouldContinueRef.current = true
          
          // Build queue from active sessions
          const queue: DiscoveryQueueItem[] = activeSessions.map((session: any) => ({
            networkId: session.network_id,
            networkName: `Network ${session.network_id}`,
            status: session.status === 'running' ? 'running' : 'pending',
            sessionId: session.id,
            pagesSearched: session.pages_crawled || 0,
            formsFound: session.forms_found || 0
          }))
          
          setDiscoveryQueue(queue)
          
          // Find the running session and start polling it
          const runningSession = activeSessions.find((s: any) => s.status === 'running')
          if (runningSession) {
            setCurrentSessionId(runningSession.id)
            startPolling(queue, queue.findIndex(q => q.sessionId === runningSession.id), runningSession.id)
          }
        }
      }
    } catch (err) {
      console.error('Failed to check active sessions:', err)
    }
  }

  useEffect(() => {
    const handleProjectChange = (e: CustomEvent) => {
      const project = e.detail
      setActiveProjectId(project.id.toString())
      setActiveProjectName(project.name)
      setSelectedNetworkIds([])
      stopDiscovery()
      if (token) {
        loadNetworks(project.id.toString(), token)
        loadFormPages(project.id.toString(), token)
      }
    }
    
    window.addEventListener('activeProjectChanged', handleProjectChange as EventListener)
    return () => window.removeEventListener('activeProjectChanged', handleProjectChange as EventListener)
  }, [token])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  const loadNetworks = async (projectId: string, authToken: string) => {
    setLoadingNetworks(true)
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        const allNetworks = [
          ...data.qa.map((n: Network) => ({ ...n, network_type: 'qa' })),
          ...data.staging.map((n: Network) => ({ ...n, network_type: 'staging' })),
          ...data.production.map((n: Network) => ({ ...n, network_type: 'production' }))
        ]
        setNetworks(allNetworks)
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const loadFormPages = async (projectId: string, authToken: string) => {
    setLoadingFormPages(true)
    try {
      const response = await fetch(
        `/api/projects/${projectId}/form-pages`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setFormPages(data)
      }
    } catch (err) {
      console.error('Failed to load form pages:', err)
    } finally {
      setLoadingFormPages(false)
    }
  }

  // Get only QA networks for discovery
  const qaNetworks = networks.filter(n => n.network_type?.toLowerCase() === 'qa')

  const toggleNetworkSelection = (networkId: number) => {
    setSelectedNetworkIds(prev => 
      prev.includes(networkId) 
        ? prev.filter(id => id !== networkId)
        : [...prev, networkId]
    )
  }

  const selectAllNetworks = () => {
    if (selectedNetworkIds.length === qaNetworks.length) {
      setSelectedNetworkIds([])
    } else {
      setSelectedNetworkIds(qaNetworks.map(n => n.id))
    }
  }

  const stopDiscovery = () => {
    shouldContinueRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setIsDiscovering(false)
    setCurrentSessionId(null)
    setCurrentNetworkIndex(-1)
  }

  const startDiscovery = async () => {
    if (selectedNetworkIds.length === 0 || !userId) {
      setError('Please select at least one network')
      return
    }
    
    setError(null)
    setMessage(null)
    setIsDiscovering(true)
    shouldContinueRef.current = true
    
    // Build the queue with all selected networks
    const queue: DiscoveryQueueItem[] = selectedNetworkIds.map(networkId => {
      const network = networks.find(n => n.id === networkId)
      return {
        networkId,
        networkName: network?.name || `Network ${networkId}`,
        status: 'pending',
        pagesSearched: 0,
        formsFound: 0
      }
    })
    
    setDiscoveryQueue(queue)
    setCurrentNetworkIndex(0)
    
    // Start the first network
    await startNetworkDiscovery(queue, 0)
  }

  const startNetworkDiscovery = async (queue: DiscoveryQueueItem[], index: number) => {
    if (!shouldContinueRef.current || index >= queue.length) {
      // All done!
      finishDiscovery(queue)
      return
    }
    
    const item = queue[index]
    
    // Update queue status to running
    const updatedQueue = queue.map((q, i) => 
      i === index ? { ...q, status: 'running' as const } : q
    )
    setDiscoveryQueue(updatedQueue)
    setCurrentNetworkIndex(index)
    
    try {
      const params = new URLSearchParams({
        user_id: userId!,
        headless: headless.toString()
      })
      
      const response = await fetch(
        `/api/form-pages/networks/${item.networkId}/locate?${params}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        const sessionId = data.crawl_session_id
        
        // Update queue with session ID
        const queueWithSession = updatedQueue.map((q, i) => 
          i === index ? { ...q, sessionId } : q
        )
        setDiscoveryQueue(queueWithSession)
        setCurrentSessionId(sessionId)
        
        // Start polling this session
        startPolling(queueWithSession, index, sessionId)
      } else {
        const errData = await response.json()
        console.error(`Failed to start discovery for network ${item.networkId}:`, errData.detail)
        
        // Mark as failed and move to next
        const failedQueue = updatedQueue.map((q, i) => 
          i === index ? { ...q, status: 'failed' as const, errorMessage: errData.detail } : q
        )
        setDiscoveryQueue(failedQueue)
        
        // Move to next network
        await startNetworkDiscovery(failedQueue, index + 1)
      }
    } catch (err) {
      console.error(`Connection error for network ${item.networkId}:`, err)
      
      // Mark as failed and move to next
      const failedQueue = updatedQueue.map((q, i) => 
        i === index ? { ...q, status: 'failed' as const, errorMessage: 'Connection error' } : q
      )
      setDiscoveryQueue(failedQueue)
      
      // Move to next network
      await startNetworkDiscovery(failedQueue, index + 1)
    }
  }

  const startPolling = (queue: DiscoveryQueueItem[], index: number, sessionId: number) => {
    // Clear any existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    pollingRef.current = setInterval(async () => {
      if (!shouldContinueRef.current) {
        if (pollingRef.current) clearInterval(pollingRef.current)
        return
      }
      
      try {
        const response = await fetch(
          `/api/form-pages/sessions/${sessionId}/status`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )
        
        if (response.ok) {
          const data: SessionStatus = await response.json()
          
          // Add new forms from this session to the list (without full reload)
          if (data.forms && data.forms.length > 0) {
            setFormPages(prev => {
              const existingIds = new Set(prev.map(f => f.id))
              const newForms = data.forms.filter(f => !existingIds.has(f.id))
              if (newForms.length > 0) {
                return [...newForms, ...prev]
              }
              return prev
            })
          }
          
          // Update queue with current progress
          setDiscoveryQueue(prev => prev.map((q, i) => 
            i === index ? {
              ...q,
              pagesSearched: data.session.pages_crawled,
              formsFound: data.session.forms_found
            } : q
          ))
          
          // Check if completed or failed
          if (data.session.status === 'completed' || data.session.status === 'failed') {
            // Stop polling this session
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
            
            // Update final status
            const finalStatus = data.session.status === 'completed' ? 'completed' : 'failed'
            const updatedQueue = queue.map((q, i) => 
              i === index ? {
                ...q,
                status: finalStatus as 'completed' | 'failed',
                pagesSearched: data.session.pages_crawled,
                formsFound: data.session.forms_found,
                errorMessage: data.session.error_message || undefined
              } : q
            )
            setDiscoveryQueue(updatedQueue)
            setCurrentSessionId(null)
            
            // Move to next network
            if (shouldContinueRef.current) {
              await startNetworkDiscovery(updatedQueue, index + 1)
            }
          }
        }
      } catch (err) {
        console.error('Failed to poll status:', err)
      }
    }, 3000)
  }

  const finishDiscovery = (queue: DiscoveryQueueItem[]) => {
    stopDiscovery()
    
    const completed = queue.filter(q => q.status === 'completed').length
    const failed = queue.filter(q => q.status === 'failed').length
    const totalForms = queue.reduce((sum, q) => sum + q.formsFound, 0)
    
    if (failed > 0) {
      setMessage(`Discovery finished. Completed: ${completed}, Failed: ${failed}. Found ${totalForms} form pages.`)
    } else {
      setMessage(`Discovery completed! Found ${totalForms} form pages across ${completed} network(s).`)
    }
    
    // Reload form pages
    if (activeProjectId && token) {
      loadFormPages(activeProjectId, token)
    }
  }

  const getNetworkTypeLabel = (type: string) => {
    switch (type) {
      case 'qa': return 'QA'
      case 'staging': return 'Staging'
      case 'production': return 'Prod'
      default: return type
    }
  }

  const getNetworkTypeColors = (type: string) => {
    const colors: Record<string, { bg: string; color: string; border: string }> = {
      qa: { bg: '#e3f2fd', color: '#1565c0', border: '#90caf9' },
      staging: { bg: '#fff3e0', color: '#e65100', border: '#ffcc80' },
      production: { bg: '#ffebee', color: '#c62828', border: '#ef9a9a' }
    }
    return colors[type] || { bg: '#f5f5f5', color: '#666', border: '#ddd' }
  }

  const openEditModal = (formPage: FormPage) => {
    setEditingFormPage(formPage)
    setEditFormName(formPage.form_name)
    setEditNavigationSteps(formPage.navigation_steps || [])
    setShowEditModal(true)
  }

  const updateNavigationStep = (index: number, field: keyof NavigationStep, value: string) => {
    setEditNavigationSteps(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const confirmDeleteStep = (index: number) => {
    setStepToDeleteIndex(index)
    setShowDeleteStepConfirm(true)
  }

  const deleteStep = () => {
    if (stepToDeleteIndex === null) return
    setEditNavigationSteps(prev => prev.filter((_, i) => i !== stepToDeleteIndex))
    setShowDeleteStepConfirm(false)
    setStepToDeleteIndex(null)
  }

  const addStepAtEnd = () => {
    setEditNavigationSteps(prev => [...prev, { action: 'click', selector: '', description: '' }])
  }

  const addStepAfter = (index: number) => {
    setEditNavigationSteps(prev => {
      const updated = [...prev]
      updated.splice(index + 1, 0, { action: 'click', selector: '', description: '' })
      return updated
    })
  }

  const saveFormPage = async () => {
    if (!editingFormPage) return
    
    setSavingFormPage(true)
    try {
      const response = await fetch(
        `/api/form-pages/routes/${editingFormPage.id}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            form_name: editFormName,
            navigation_steps: editNavigationSteps
          })
        }
      )
      
      if (response.ok) {
        setMessage('Form page updated successfully!')
        setShowEditModal(false)
        if (activeProjectId) {
          loadFormPages(activeProjectId, token!)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to update form page')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setSavingFormPage(false)
    }
  }

  const openDeleteModal = (formPage: FormPage) => {
    setFormPageToDelete(formPage)
    setShowDeleteModal(true)
  }

  const deleteFormPage = async () => {
    if (!formPageToDelete) return
    
    setDeletingFormPage(true)
    try {
      const response = await fetch(
        `/api/form-pages/routes/${formPageToDelete.id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Form page deleted successfully!')
        setShowDeleteModal(false)
        setFormPageToDelete(null)
        if (activeProjectId) {
          loadFormPages(activeProjectId, token!)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete form page')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingFormPage(false)
    }
  }

  // Calculate overall stats from queue
  const getOverallStats = () => {
    const totalPagesSearched = discoveryQueue.reduce((sum, q) => sum + q.pagesSearched, 0)
    const totalFormsFound = discoveryQueue.reduce((sum, q) => sum + q.formsFound, 0)
    const completedCount = discoveryQueue.filter(q => q.status === 'completed').length
    const runningCount = discoveryQueue.filter(q => q.status === 'running').length
    const failedCount = discoveryQueue.filter(q => q.status === 'failed').length
    const pendingCount = discoveryQueue.filter(q => q.status === 'pending').length
    
    return { totalPagesSearched, totalFormsFound, completedCount, runningCount, failedCount, pendingCount }
  }

  if (!token) return <p style={{ fontSize: '16px', padding: '20px' }}>Loading...</p>

  if (!activeProjectId) {
    return (
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: '24px' }}>👋 Welcome!</h2>
          <p style={{ fontSize: '16px' }}>Please select a project from the top bar to get started.</p>
          <p style={{ color: '#666', fontSize: '15px' }}>
            If you don't have any projects yet, click on the project dropdown and choose "Add Project".
          </p>
        </div>
      </div>
    )
  }

  const stats = getOverallStats()
  const totalNetworks = discoveryQueue.length
  const completedNetworks = stats.completedCount + stats.failedCount

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {error && (
        <div style={errorBoxStyle}>
          ❌ {error}
          <button onClick={() => setError(null)} style={closeButtonStyle}>×</button>
        </div>
      )}
      {message && (
        <div style={successBoxStyle}>
          ✅ {message}
          <button onClick={() => setMessage(null)} style={closeButtonStyle}>×</button>
        </div>
      )}

      {/* Form Pages Discovery Section - Clean White Design */}
      <div style={cardStyle}>
        {/* Header */}
        <div style={discoveryHeaderStyle}>
          <div style={discoveryIconStyle}>🔍</div>
          <div style={{ flex: 1 }}>
            <h1 style={discoveryTitleStyle}>Form Pages Discovery</h1>
            <p style={discoverySubtitleStyle}>
              Automatically discover all form pages in your web application using AI-powered crawling
            </p>
          </div>
          {isDiscovering && (
            <div style={discoveringBadgeStyle}>
              <div style={pulsingDotStyle} />
              <span>Discovery in Progress</span>
            </div>
          )}
        </div>

        {/* Divider */}
        <div style={dividerStyle} />

        {networks.length === 0 ? (
          <div style={emptyStateStyle}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🌐</div>
            <h3 style={{ margin: '0 0 8px', fontSize: '20px', color: '#333' }}>No Networks Found</h3>
            <p style={{ margin: 0, color: '#666', fontSize: '16px' }}>
              Open the <strong>Networks</strong> modal from the top bar to add your first network.
            </p>
          </div>
        ) : (
          <>
            {/* Network Selection */}
            <div style={sectionStyle}>
              <div style={sectionHeaderStyle}>
                <div>
                  <h3 style={sectionTitleStyle}>Select Networks</h3>
                  <p style={sectionSubtitleStyle}>Select QA environment networks to discover form pages (other environments available when running tests)</p>
                </div>
                <button 
                  onClick={selectAllNetworks} 
                  style={selectAllBtnStyle}
                  disabled={isDiscovering}
                >
                  {selectedNetworkIds.length === networks.length ? '✓ All Selected' : 'Select All'}
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {qaNetworks.map(network => {
                  const colors = getNetworkTypeColors(network.network_type)
                  const isSelected = selectedNetworkIds.includes(network.id)
                  const queueItem = discoveryQueue.find(q => q.networkId === network.id)
                  
                  return (
                    <div 
                      key={network.id}
                      onClick={() => !isDiscovering && toggleNetworkSelection(network.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '12px 16px',
                        border: `1px solid ${isSelected ? '#0070f3' : '#e0e0e0'}`,
                        borderRadius: '8px',
                        background: isSelected ? '#f0f7ff' : '#fff',
                        cursor: isDiscovering ? 'not-allowed' : 'pointer',
                        opacity: isDiscovering ? 0.7 : 1,
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{
                        ...networkCheckboxStyle,
                        background: isSelected ? '#0070f3' : '#fff',
                        borderColor: isSelected ? '#0070f3' : '#ccc'
                      }}>
                        {isSelected && <span style={{ color: '#fff', fontSize: '18px' }}>✓</span>}
                      </div>
                      <span style={{ fontWeight: 500, fontSize: '18px', color: '#2d3748', minWidth: '150px' }}>
                        {network.name}
                      </span>
                      <span style={{ fontSize: '17px', color: '#555', flex: 1 }}>
                        {network.url}
                      </span>
                      {network.login_username && (
                        <span style={{ fontSize: '16px', color: '#666' }}>
                          👤 {network.login_username}
                        </span>
                      )}
                      <span style={{
                        padding: '8px 16px',
                        borderRadius: '8px',
                        fontSize: '15px',
                        fontWeight: 600,
                        background: colors.bg,
                        color: colors.color,
                        border: `1px solid ${colors.border}`
                      }}>
                        {getNetworkTypeLabel(network.network_type)}
                      </span>
                      {queueItem && (
                        <span style={{
                          padding: '8px 16px',
                          borderRadius: '12px',
                          fontSize: '15px',
                          fontWeight: 600,
                          background: queueItem.status === 'running' ? '#fff3e0' :
                                     queueItem.status === 'completed' ? '#e8f5e9' :
                                     queueItem.status === 'failed' ? '#ffebee' : '#f5f5f5',
                          color: queueItem.status === 'running' ? '#e65100' :
                                queueItem.status === 'completed' ? '#2e7d32' :
                                queueItem.status === 'failed' ? '#c62828' : '#666'
                        }}>
                          {queueItem.status === 'running' ? '⏳ Running' :
                           queueItem.status === 'completed' ? '✅ Done' :
                           queueItem.status === 'failed' ? '❌ Failed' : '⏸ Pending'}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>

              {selectedNetworkIds.length > 0 && (
                <div style={selectedCountStyle}>
                  <span style={selectedCountBadgeStyle}>{selectedNetworkIds.length}</span>
                  network{selectedNetworkIds.length > 1 ? 's' : ''} selected
                  {selectedNetworkIds.length > 1 && (
                    <span style={{ marginLeft: '8px', color: '#888', fontSize: '15px' }}>
                      (will be processed sequentially)
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Divider */}
            <div style={dividerStyle} />

            {/* Action - Centered */}
            <div style={{ ...actionSectionStyle, justifyContent: 'center' }}>
              <button
                onClick={startDiscovery}
                disabled={isDiscovering || selectedNetworkIds.length === 0}
                style={{
                  ...startDiscoveryBtnStyle,
                  opacity: (isDiscovering || selectedNetworkIds.length === 0) ? 0.6 : 1,
                  cursor: (isDiscovering || selectedNetworkIds.length === 0) ? 'not-allowed' : 'pointer'
                }}
              >
                {isDiscovering ? '⟳ Discovering...' : '🚀 Start Discovery'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Discovery Status */}
      {discoveryQueue.length > 0 && (
        <div style={{ ...cardStyle, marginTop: '24px' }}>
          <h2 style={{ marginTop: 0, fontSize: '22px', color: '#333' }}>📊 Discovery Progress</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '20px' }}>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Networks</div>
              <div style={statValueStyle}>{completedNetworks} / {totalNetworks}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Forms Found</div>
              <div style={{ ...statValueStyle, color: '#2e7d32' }}>{formPages.length}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Current</div>
              <div style={{ ...statValueStyle, fontSize: '16px', color: stats.runningCount > 0 ? '#e65100' : '#666' }}>
                {stats.runningCount > 0 
                  ? discoveryQueue.find(q => q.status === 'running')?.networkName || '-'
                  : 'None'}
              </div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Status</div>
              <div style={{ 
                ...statValueStyle, 
                fontSize: '16px',
                color: isDiscovering ? '#f57c00' : stats.failedCount > 0 ? '#c62828' : '#2e7d32'
              }}>
                {isDiscovering ? 'IN PROGRESS' : stats.failedCount > 0 ? 'COMPLETED (with errors)' : 'COMPLETED'}
              </div>
            </div>
          </div>

          {totalNetworks > 0 && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '15px', color: '#666' }}>
                <span>Overall Progress</span>
                <span>{Math.round((completedNetworks / totalNetworks) * 100)}%</span>
              </div>
              <div style={{ background: '#e0e0e0', borderRadius: '6px', height: '10px', overflow: 'hidden' }}>
                <div style={{
                  background: 'linear-gradient(90deg, #0070f3, #00c853)',
                  height: '100%',
                  width: `${(completedNetworks / totalNetworks) * 100}%`,
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}

          {/* Network Queue Status */}
          <div style={{ marginTop: '24px' }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '16px', color: '#333' }}>Network Queue</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {discoveryQueue.map((item, idx) => (
                <div 
                  key={item.networkId}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    padding: '12px 16px',
                    background: item.status === 'running' ? '#fff3e0' : 
                               item.status === 'completed' ? '#e8f5e9' :
                               item.status === 'failed' ? '#ffebee' : '#f5f5f5',
                    borderRadius: '8px',
                    border: `1px solid ${
                      item.status === 'running' ? '#ffcc80' :
                      item.status === 'completed' ? '#c8e6c9' :
                      item.status === 'failed' ? '#ffcdd2' : '#e0e0e0'
                    }`
                  }}
                >
                  <span style={{ 
                    width: '28px', 
                    height: '28px', 
                    borderRadius: '50%', 
                    background: item.status === 'running' ? '#ff9800' :
                               item.status === 'completed' ? '#4caf50' :
                               item.status === 'failed' ? '#f44336' : '#9e9e9e',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    fontWeight: 600
                  }}>
                    {idx + 1}
                  </span>
                  <span style={{ flex: 1, fontWeight: 500, fontSize: '15px', color: '#333' }}>
                    {item.networkName}
                  </span>
                  <span style={{ 
                    fontSize: '14px',
                    fontWeight: 600,
                    color: item.status === 'running' ? '#e65100' :
                          item.status === 'completed' ? '#2e7d32' :
                          item.status === 'failed' ? '#c62828' : '#666'
                  }}>
                    {item.status === 'running' ? '⏳ Running...' :
                     item.status === 'completed' ? '✅ Completed' :
                     item.status === 'failed' ? '❌ Failed' : '⏸ Waiting'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Form Pages Table */}
      <div style={{ ...cardStyle, marginTop: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', color: '#1e293b', fontWeight: 600 }}>Discovered Form Pages</h2>
            <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#64748b' }}>{formPages.length} forms found in this project</p>
          </div>
          {formPages.length > 10 && (
            <span style={{ fontSize: '13px', color: '#94a3b8', background: '#f1f5f9', padding: '6px 14px', borderRadius: '20px' }}>Showing 10 of {formPages.length} • Scroll for more</span>
          )}
        </div>
        
        {loadingFormPages ? (
          <p style={{ color: '#64748b', marginTop: '20px', fontSize: '15px' }}>Loading form pages...</p>
        ) : formPages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '50px 20px', background: '#f8fafc', borderRadius: '12px', border: '2px dashed #e2e8f0' }}>
            <div style={{ fontSize: '40px', marginBottom: '16px' }}>📋</div>
            <p style={{ margin: 0, fontSize: '16px', color: '#475569', fontWeight: 500 }}>No form pages discovered yet</p>
            <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8' }}>Select networks above and start a discovery to find form pages</p>
          </div>
        ) : (
          <div style={tableContainerStyle}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th 
                    style={{ ...thStyle, cursor: 'pointer', userSelect: 'none' }}
                    onClick={() => {
                      if (sortField === 'name') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('name')
                        setSortDirection('asc')
                      }
                    }}
                  >
                    Form Name {sortField === 'name' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th style={thStyle}>Path Steps</th>
                  <th style={thStyle}>Type</th>
                  <th 
                    style={{ ...thStyle, cursor: 'pointer', userSelect: 'none' }}
                    onClick={() => {
                      if (sortField === 'date') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('date')
                        setSortDirection('desc')
                      }
                    }}
                  >
                    Discovered {sortField === 'date' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th style={{ ...thStyle, width: '120px', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {[...formPages].sort((a, b) => {
                  if (sortField === 'name') {
                    const nameA = (a.form_name || '').toLowerCase()
                    const nameB = (b.form_name || '').toLowerCase()
                    return sortDirection === 'asc' 
                      ? nameA.localeCompare(nameB)
                      : nameB.localeCompare(nameA)
                  } else {
                    const dateA = new Date(a.created_at || 0).getTime()
                    const dateB = new Date(b.created_at || 0).getTime()
                    return sortDirection === 'asc' 
                      ? dateA - dateB
                      : dateB - dateA
                  }
                }).map((form, index) => (
                  <tr 
                    key={form.id} 
                    style={{
                      ...tableRowStyle,
                      background: '#fff'
                    }} 
                    onMouseOver={(e) => e.currentTarget.style.background = '#e8edf3'} 
                    onMouseOut={(e) => e.currentTarget.style.background = '#fff'}
                    onDoubleClick={() => openEditModal(form)}
                  >
                    <td style={tdStyle}>
                      <strong style={{ fontSize: '18px', color: '#1e293b' }}>{form.form_name}</strong>
                      {form.parent_form_name && (
                        <div style={{ fontSize: '15px', color: '#64748b', marginTop: '4px' }}>
                          Parent: {form.parent_form_name}
                        </div>
                      )}
                    </td>
                    <td style={tdStyle}>
                      <span style={pathStepsBadgeStyle}>
                        {form.navigation_steps?.length || 0} steps
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        background: form.is_root ? '#e8edf3' : '#fef3c7',
                        color: form.is_root ? '#4a5568' : '#d97706',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        fontSize: '16px',
                        fontWeight: 600
                      }}>
                        {form.is_root ? 'Root' : 'Child'}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ fontSize: '17px', color: '#475569' }}>
                        {form.created_at ? new Date(form.created_at).toLocaleDateString() : '-'}
                      </div>
                      <div style={{ fontSize: '15px', color: '#888' }}>
                        {form.created_at ? new Date(form.created_at).toLocaleTimeString() : ''}
                      </div>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                        <button 
                          onClick={() => openEditModal(form)} 
                          style={actionButtonStyle}
                          title="Edit form page"
                        >
                          ✏️
                        </button>
                        <button 
                          onClick={() => openDeleteModal(form)} 
                          style={{ ...actionButtonStyle, borderColor: '#ffcdd2' }}
                          title="Delete form page"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Form Page Modal */}
      {showEditModal && editingFormPage && (
        <div style={modalOverlayStyle}>
          <div style={largeModalContentStyle}>
            <div style={modalHeaderStyle}>
              <div>
                <h2 style={{ margin: 0, fontSize: '24px', color: '#2d3a48' }}>✏️ Edit Form Page</h2>
                <p style={{ margin: '6px 0 0', color: '#4a5a6a', fontSize: '16px' }}>
                  Editing: <strong>{editingFormPage.form_name}</strong>
                </p>
              </div>
              <button onClick={() => setShowEditModal(false)} style={modalCloseButtonStyle}>×</button>
            </div>

            <div style={prominentNoteStyle}>
              <div style={{ fontSize: '32px' }}>💡</div>
              <div>
                <strong style={{ fontSize: '18px', color: '#2d3a48' }}>AI-Discovered Path</strong>
                <p style={{ margin: '6px 0 0', fontSize: '16px', color: '#4a5a6a' }}>
                  This navigation path was automatically discovered by AI. You can modify the steps below if the path needs adjustment.
                </p>
              </div>
            </div>

            <div style={modalBodyStyle}>
              <div style={modalLeftColumnStyle}>
                <div style={{ marginBottom: '24px' }}>
                  <label style={modalLabelStyle}>Form Name</label>
                  <input
                    type="text"
                    value={editFormName}
                    onChange={(e) => setEditFormName(e.target.value)}
                    style={modalInputStyle}
                  />
                </div>

                <div style={infoSectionStyle}>
                  <h4 style={{ margin: '0 0 16px', fontSize: '16px', color: '#333' }}>Hierarchy</h4>
                  <div style={infoRowStyle}>
                    <span style={infoLabelStyle}>Type:</span>
                    <span style={{
                      background: editingFormPage.is_root ? '#e3f2fd' : '#fff3e0',
                      color: editingFormPage.is_root ? '#1565c0' : '#e65100',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '14px',
                      fontWeight: 500
                    }}>
                      {editingFormPage.is_root ? 'Root Form' : 'Child Form'}
                    </span>
                  </div>
                  {editingFormPage.parent_form_name && (
                    <div style={infoRowStyle}>
                      <span style={infoLabelStyle}>Parent:</span>
                      <span style={{ fontSize: '15px', color: '#333' }}>{editingFormPage.parent_form_name}</span>
                    </div>
                  )}
                  {editingFormPage.children && editingFormPage.children.length > 0 && (
                    <div style={{ marginTop: '12px' }}>
                      <span style={infoLabelStyle}>Children:</span>
                      <div style={{ marginTop: '8px' }}>
                        {editingFormPage.children.map((c, i) => (
                          <span key={i} style={childBadgeStyle}>{c.form_name}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div style={infoSectionStyle}>
                  <h4 style={{ margin: '0 0 12px', fontSize: '16px', color: '#333' }}>URL</h4>
                  <div style={{ fontSize: '14px', color: '#666', wordBreak: 'break-all' }}>
                    {editingFormPage.url}
                  </div>
                </div>
              </div>

              <div style={modalRightColumnStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 style={{ margin: 0, fontSize: '18px', color: '#333' }}>Path Steps ({editNavigationSteps.length})</h3>
                  <button onClick={addStepAtEnd} style={addStepButtonStyle}>
                    + Add Step
                  </button>
                </div>

                <div style={pathStepsScrollContainerStyle}>
                  {editNavigationSteps.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px 20px', color: '#888' }}>
                      <p style={{ fontSize: '16px' }}>No path steps defined.</p>
                      <button onClick={addStepAtEnd} style={addStepButtonStyle}>+ Add First Step</button>
                    </div>
                  ) : (
                    editNavigationSteps.map((step, index) => (
                      <div key={index} style={pathStepCardStyle}>
                        <div style={stepHeaderStyle}>
                          <div style={stepNumberBadgeStyle}>{index + 1}</div>
                          <div style={{ flex: 1 }}>
                            <span style={{ fontWeight: 600, fontSize: '16px', color: '#333' }}>Step {index + 1}</span>
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button 
                              onClick={() => addStepAfter(index)} 
                              style={stepActionButtonStyle}
                              title="Add step after this"
                            >
                              ➕
                            </button>
                            <button 
                              onClick={() => confirmDeleteStep(index)} 
                              style={{ ...stepActionButtonStyle, color: '#c62828' }}
                              title="Delete this step"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>

                        <div style={stepFieldsStyle}>
                          <div style={stepFieldRowStyle}>
                            <div style={{ flex: 1 }}>
                              <label style={stepFieldLabelStyle}>Action</label>
                              <input
                                type="text"
                                value={step.action || ''}
                                disabled
                                style={{ ...stepFieldInputStyle, background: '#f0f0f0', color: '#888', cursor: 'not-allowed' }}
                              />
                            </div>
                            <div style={{ flex: 2 }}>
                              <label style={stepFieldLabelStyle}>Description</label>
                              <input
                                type="text"
                                value={step.description || ''}
                                onChange={(e) => updateNavigationStep(index, 'description', e.target.value)}
                                style={stepFieldInputStyle}
                                placeholder="Describe this action"
                              />
                            </div>
                          </div>
                          <div>
                            <label style={stepFieldLabelStyle}>Selector (Locator)</label>
                            <input
                              type="text"
                              value={step.selector || ''}
                              onChange={(e) => updateNavigationStep(index, 'selector', e.target.value)}
                              style={stepFieldInputStyle}
                              placeholder="CSS selector or XPath"
                            />
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div style={modalFooterStyle}>
              <button onClick={() => setShowEditModal(false)} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button 
                onClick={saveFormPage} 
                style={primaryButtonStyle}
                disabled={savingFormPage}
              >
                {savingFormPage ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Step Confirmation */}
      {showDeleteStepConfirm && (
        <div style={modalOverlayStyle}>
          <div style={smallModalContentStyle}>
            <h3 style={{ marginTop: 0, color: '#c62828', fontSize: '22px' }}>⚠️ Delete Step?</h3>
            <p style={{ fontSize: '16px', color: '#333' }}>Are you sure you want to delete <strong>Step {(stepToDeleteIndex || 0) + 1}</strong>?</p>
            <p style={{ fontSize: '15px', color: '#666' }}>This action cannot be undone.</p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
              <button onClick={() => { setShowDeleteStepConfirm(false); setStepToDeleteIndex(null) }} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button onClick={deleteStep} style={dangerButtonStyle}>
                Delete Step
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Form Page Modal */}
      {showDeleteModal && formPageToDelete && (
        <div style={modalOverlayStyle}>
          <div style={deleteModalContentStyle}>
            <h2 style={{ marginTop: 0, color: '#c62828', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '24px' }}>
              <span style={{ fontSize: '32px' }}>⚠️</span>
              Delete Form Page?
            </h2>
            
            <p style={{ fontSize: '17px', margin: '20px 0', color: '#333' }}>
              Are you sure you want to delete <strong>"{formPageToDelete.form_name}"</strong>?
            </p>
            
            <div style={deleteWarningBoxStyle}>
              <div style={{ display: 'flex', gap: '16px' }}>
                <span style={{ fontSize: '28px' }}>📝</span>
                <div>
                  <strong style={{ fontSize: '16px' }}>Important Note:</strong>
                  <p style={{ margin: '8px 0 0', fontSize: '15px' }}>
                    The form mapping (if present) will <strong>NOT</strong> be deleted. 
                    Only the discovered form page entry will be removed from the list.
                  </p>
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '28px' }}>
              <button onClick={() => { setShowDeleteModal(false); setFormPageToDelete(null) }} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button 
                onClick={deleteFormPage} 
                style={dangerButtonStyle}
                disabled={deletingFormPage}
              >
                {deletingFormPage ? 'Deleting...' : 'Delete Form Page'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== STYLES ====================

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #b8c4d0',
  borderRadius: '16px',
  padding: '28px',
  boxShadow: '0 3px 15px rgba(0,0,0,0.08)'
}

const discoveryHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  padding: '12px 20px',
  background: 'linear-gradient(180deg, #d0dae4 0%, #c0ccd8 100%)',
  border: '1px solid #9aaab8',
  borderBottom: '3px solid #8a9aa8',
  borderRadius: '10px',
  marginBottom: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.5)'
}

const discoveryIconStyle: React.CSSProperties = {
  fontSize: '22px',
  background: '#b0bcc8',
  borderRadius: '8px',
  padding: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}

const discoveryTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '18px',
  fontWeight: 700,
  color: '#2d3a48'
}

const discoverySubtitleStyle: React.CSSProperties = {
  margin: '2px 0 0',
  fontSize: '16px',
  color: '#4a5a6a'
}

const discoveringBadgeStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  background: '#fff',
  border: '1px solid #b0bcc8',
  padding: '12px 22px',
  borderRadius: '24px',
  fontSize: '16px',
  fontWeight: 600,
  color: '#3d4852',
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
}

const pulsingDotStyle: React.CSSProperties = {
  width: '10px',
  height: '10px',
  borderRadius: '50%',
  background: '#4caf50',
  boxShadow: '0 0 8px #4caf50'
}

const dividerStyle: React.CSSProperties = {
  display: 'none'
}

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '60px 48px',
  background: 'linear-gradient(135deg, #f5f7fa 0%, #f8f9fb 100%)',
  borderRadius: '16px',
  border: '2px dashed #e0e0e0'
}

const sectionStyle: React.CSSProperties = {
  marginBottom: '24px'
}

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '20px'
}

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '22px',
  fontWeight: 600,
  color: '#1a1a2e'
}

const sectionSubtitleStyle: React.CSSProperties = {
  margin: '6px 0 0',
  fontSize: '17px',
  color: '#555'
}

const selectAllBtnStyle: React.CSSProperties = {
  background: 'linear-gradient(180deg, #d0dae4 0%, #c0ccd8 100%)',
  color: '#2d3a48',
  border: '1px solid #9aaab8',
  borderBottom: '3px solid #8a9aa8',
  padding: '12px 24px',
  borderRadius: '10px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.5)'
}

const networkGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: '20px'
}

const networkCardStyle: React.CSSProperties = {
  padding: '20px',
  border: '2px solid #e0e0e0',
  borderRadius: '12px',
  transition: 'all 0.2s ease'
}

const networkCardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: '14px'
}

const networkCheckboxStyle: React.CSSProperties = {
  width: '24px',
  height: '24px',
  borderRadius: '6px',
  border: '2px solid #ccc',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.2s'
}

const networkTypeBadgeStyle: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 700,
  textTransform: 'uppercase'
}

const networkNameStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '18px',
  fontWeight: 600,
  color: '#333'
}

const networkUrlStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '15px',
  color: '#666',
  wordBreak: 'break-all'
}

const networkCredentialStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginTop: '12px',
  fontSize: '14px',
  color: '#888'
}

const selectedCountStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  marginTop: '20px',
  fontSize: '16px',
  color: '#666'
}

const selectedCountBadgeStyle: React.CSSProperties = {
  background: '#0070f3',
  color: '#fff',
  width: '32px',
  height: '32px',
  borderRadius: '50%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: '16px'
}

const actionSectionStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '24px 28px',
  background: 'linear-gradient(90deg, #f8f9fa 0%, #fff 100%)',
  borderRadius: '16px',
  border: '1px solid #e8e8e8'
}

const settingsRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '40px'
}

const settingItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px'
}

const settingLabelStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 500,
  color: '#333'
}

const settingInputStyle: React.CSSProperties = {
  width: '90px',
  padding: '10px 14px',
  border: '1px solid #ddd',
  borderRadius: '8px',
  fontSize: '16px',
  background: '#fff',
  color: '#333'
}

const checkboxLabelStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  cursor: 'pointer'
}

const checkboxTextStyle: React.CSSProperties = {
  fontSize: '17px',
  fontWeight: 500,
  color: '#2d3748'
}

const checkboxHintStyle: React.CSSProperties = {
  fontSize: '15px',
  color: '#666',
  marginLeft: '8px'
}

const startDiscoveryBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  background: 'linear-gradient(180deg, #c8d4e0 0%, #b8c6d4 100%)',
  color: '#2d3a48',
  border: '1px solid #90a0b0',
  borderBottom: '3px solid #8090a0',
  padding: '16px 36px',
  borderRadius: '14px',
  fontSize: '18px',
  fontWeight: 700,
  cursor: 'pointer',
  boxShadow: '0 2px 6px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.5)',
  transition: 'all 0.3s ease'
}

const tableContainerStyle: React.CSSProperties = {
  maxHeight: '900px',
  overflowY: 'auto',
  marginTop: '24px',
  background: '#fff',
  borderRadius: '16px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  border: '1px solid #b8c4d0'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '18px 22px',
  borderBottom: '2px solid #b8c4d0',
  fontWeight: 700,
  color: '#5a4a3a',
  background: '#e8edf3',
  position: 'sticky',
  top: 0,
  zIndex: 1,
  fontSize: '17px',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
}

const tableRowStyle: React.CSSProperties = {
  transition: 'all 0.2s ease',
  cursor: 'pointer'
}

const tdStyle: React.CSSProperties = {
  padding: '18px 22px',
  borderBottom: '1px solid #e0d8cc',
  verticalAlign: 'middle',
  fontSize: '17px',
  color: '#2d3748'
}

const pathStepsBadgeStyle: React.CSSProperties = {
  background: '#e8edf3',
  color: '#4a5568',
  padding: '10px 18px',
  borderRadius: '20px',
  fontSize: '16px',
  fontWeight: 600
}

const actionButtonStyle: React.CSSProperties = {
  background: '#e8edf3',
  border: '1px solid #b8c4d0',
  borderRadius: '10px',
  padding: '10px 14px',
  cursor: 'pointer',
  fontSize: '16px',
  transition: 'all 0.2s',
  boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
}

const statBoxStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #f8f9fa 0%, #fff 100%)',
  padding: '24px',
  borderRadius: '14px',
  textAlign: 'center',
  border: '1px solid #e8e8e8',
  boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
}

const statLabelStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#888',
  marginBottom: '8px',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  fontWeight: 600
}

const statValueStyle: React.CSSProperties = {
  fontSize: '28px',
  fontWeight: 700,
  color: '#1a1a2e'
}

const errorBoxStyle: React.CSSProperties = {
  background: '#ffebee',
  color: '#c62828',
  padding: '16px 20px',
  borderRadius: '10px',
  marginBottom: '24px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: '16px',
  border: '1px solid #ffcdd2'
}

const successBoxStyle: React.CSSProperties = {
  background: '#e8f5e9',
  color: '#2e7d32',
  padding: '16px 20px',
  borderRadius: '10px',
  marginBottom: '24px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: '16px',
  border: '1px solid #c8e6c9'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  fontSize: '24px',
  cursor: 'pointer',
  padding: '0 0 0 12px'
}

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(180deg, #c8d4e0 0%, #b8c6d4 100%)',
  color: '#2d3a48',
  padding: '14px 28px',
  border: '1px solid #90a0b0',
  borderBottom: '3px solid #8090a0',
  borderRadius: '8px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: '#fff',
  color: '#3d4852',
  padding: '14px 28px',
  border: '1px solid #b8c4d0',
  borderRadius: '8px',
  fontSize: '16px',
  cursor: 'pointer'
}

const dangerButtonStyle: React.CSSProperties = {
  background: '#c62828',
  color: 'white',
  padding: '14px 28px',
  border: 'none',
  borderRadius: '8px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer'
}

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '20px'
}

const largeModalContentStyle: React.CSSProperties = {
  background: '#e8edf3',
  borderRadius: '16px',
  width: '100%',
  maxWidth: '1100px',
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
  border: '1px solid #b8c4d0'
}

const modalHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '28px 32px',
  borderBottom: '2px solid #b8c4d0',
  background: 'linear-gradient(180deg, #d0dae4 0%, #c0ccd8 100%)'
}

const modalCloseButtonStyle: React.CSSProperties = {
  background: '#d8e0e8',
  border: '1px solid #b8c4d0',
  fontSize: '28px',
  cursor: 'pointer',
  padding: '10px 16px',
  borderRadius: '8px',
  color: '#5a4a3a',
  lineHeight: 1
}

const prominentNoteStyle: React.CSSProperties = {
  display: 'flex',
  gap: '20px',
  background: 'linear-gradient(180deg, #e0e6ed 0%, #d4dce6 100%)',
  border: '1px solid #b0bcc8',
  color: '#3d4852',
  padding: '24px 28px',
  margin: '0',
  alignItems: 'flex-start'
}

const modalBodyStyle: React.CSSProperties = {
  display: 'flex',
  flex: 1,
  overflow: 'hidden'
}

const modalLeftColumnStyle: React.CSSProperties = {
  width: '340px',
  padding: '28px',
  borderRight: '2px solid #c5ced9',
  overflowY: 'auto',
  background: '#fff'
}

const modalRightColumnStyle: React.CSSProperties = {
  flex: 1,
  padding: '28px',
  overflowY: 'auto',
  background: '#e8edf3'
}

const modalLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '10px',
  fontWeight: 600,
  color: '#3d4852',
  fontSize: '16px'
}

const modalInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  border: '1px solid #b8c4d0',
  borderRadius: '8px',
  fontSize: '16px',
  boxSizing: 'border-box',
  background: '#fff'
}

const infoSectionStyle: React.CSSProperties = {
  padding: '20px',
  background: '#e8edf3',
  borderRadius: '10px',
  marginBottom: '20px',
  border: '1px solid #c5ced9'
}

const infoRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  marginBottom: '12px',
  fontSize: '15px'
}

const infoLabelStyle: React.CSSProperties = {
  color: '#5a4a3a',
  minWidth: '70px',
  fontSize: '15px'
}

const childBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  background: '#e8edf3',
  color: '#4a5568',
  padding: '6px 12px',
  borderRadius: '12px',
  fontSize: '14px',
  marginRight: '8px',
  marginBottom: '6px',
  border: '1px solid #c5ced9'
}

const addStepButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(180deg, #d0dae4 0%, #c0ccd8 100%)',
  color: '#3d4852',
  border: '1px solid #9aaab8',
  borderBottom: '3px solid #8a9aa8',
  padding: '10px 20px',
  borderRadius: '8px',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer'
}

const pathStepsScrollContainerStyle: React.CSSProperties = {
  maxHeight: 'calc(90vh - 380px)',
  overflowY: 'auto',
  paddingRight: '10px'
}

const pathStepCardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #b8c4d0',
  borderRadius: '12px',
  marginBottom: '16px',
  overflow: 'hidden'
}

const stepHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  padding: '14px 18px',
  background: 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
  borderBottom: '1px solid #b8c4d0'
}

const stepNumberBadgeStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  background: 'linear-gradient(180deg, #c0ccd8 0%, #a8b8c8 100%)',
  color: '#3d4852',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '16px',
  fontWeight: 700,
  flexShrink: 0,
  border: '2px solid #8a9aa8'
}

const stepActionButtonStyle: React.CSSProperties = {
  background: '#d8e0e8',
  border: '1px solid #b8c4d0',
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: '18px',
  borderRadius: '6px'
}

const stepFieldsStyle: React.CSSProperties = {
  padding: '20px',
  background: '#fff'
}

const stepFieldRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '16px',
  marginBottom: '16px'
}

const stepFieldLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontWeight: 500,
  color: '#555',
  fontSize: '14px'
}

const stepFieldInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  border: '1px solid #ddd',
  borderRadius: '8px',
  fontSize: '15px',
  boxSizing: 'border-box'
}

const modalFooterStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '14px',
  padding: '24px 32px',
  borderTop: '2px solid #b8c4d0',
  background: 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)'
}

const smallModalContentStyle: React.CSSProperties = {
  background: '#e8edf3',
  borderRadius: '14px',
  padding: '32px',
  width: '100%',
  maxWidth: '450px',
  boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
  border: '1px solid #b8c4d0'
}

const deleteModalContentStyle: React.CSSProperties = {
  background: '#e8edf3',
  borderRadius: '16px',
  padding: '36px',
  width: '100%',
  maxWidth: '520px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
  border: '1px solid #b8c4d0'
}

const deleteWarningBoxStyle: React.CSSProperties = {
  background: 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
  border: '1px solid #b0bcc8',
  color: '#3d4852',
  padding: '24px',
  borderRadius: '10px',
  marginTop: '20px'
}
