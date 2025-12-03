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
  mapping_status?: 'not_mapped' | 'mapping' | 'mapped' | 'failed'
  mapping_session_id?: number
}

interface SessionStatus {
  session: {
    id: number
    status: string
    pages_crawled: number
    forms_found: number
    error_message: string | null
    error_code: string | null
    started_at: string | null
    completed_at: string | null
  }
  forms: FormPage[]
}

// Error code to friendly message mapping
const ERROR_MESSAGES: Record<string, string> = {
  'PAGE_NOT_FOUND': '🔗 Page not found (404) - check the URL',
  'ACCESS_DENIED': '🔒 Access denied (403) - check permissions',
  'SERVER_ERROR': '⚠️ Server error (500) - site may be experiencing issues',
  'SSL_ERROR': '🔐 SSL certificate error - site security issue',
  'SITE_UNAVAILABLE': '🌐 Site unavailable - server may be down',
  'LOGIN_FAILED': '🔑 Login failed - check credentials or login page changed',
  'SESSION_EXPIRED': '⏰ Session expired during discovery',
  'TIMEOUT': '⏱️ Page load timeout - site may be slow',
  'ELEMENT_NOT_FOUND': '🔍 Required element not found on page',
  'AGENT_DISCONNECTED': '🔌 Agent disconnected - no heartbeat received',
  'USER_CANCELLED': '⏹ Cancelled by user',
  'UNKNOWN': '❓ Unknown error occurred'
}

const getErrorMessage = (errorCode: string | null | undefined, errorMessage: string | null | undefined): string => {
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }
  return errorMessage || 'Discovery failed'
}

interface DiscoveryQueueItem {
  networkId: number
  networkName: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  sessionId?: number
  pagesSearched: number
  formsFound: number
  errorMessage?: string
  errorCode?: string
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
  
  // Panel view instead of modal
  const [showEditPanel, setShowEditPanel] = useState(false)
  const [editingFormPage, setEditingFormPage] = useState<FormPage | null>(null)
  const [editFormName, setEditFormName] = useState('')
  const [editNavigationSteps, setEditNavigationSteps] = useState<NavigationStep[]>([])
  const [savingFormPage, setSavingFormPage] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  
  const [showDeleteStepConfirm, setShowDeleteStepConfirm] = useState(false)
  const [stepToDeleteIndex, setStepToDeleteIndex] = useState<number | null>(null)
  
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [formPageToDelete, setFormPageToDelete] = useState<FormPage | null>(null)
  const [deletingFormPage, setDeletingFormPage] = useState(false)
  
  // Form Mapping state
  const [mappingFormIds, setMappingFormIds] = useState<Set<number>>(new Set())
  const [mappingStatus, setMappingStatus] = useState<Record<number, { status: string; sessionId?: number; error?: string }>>({})
  const mappingPollingRef = useRef<Record<number, NodeJS.Timeout>>({})
  
  // Discovery section collapse state (collapsed by default when forms exist)
  const [isDiscoveryExpanded, setIsDiscoveryExpanded] = useState(false)
  
  // Toggle step expansion
  const toggleStepExpansion = (index: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }


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

  // ============================================
  // FORM MAPPING FUNCTIONS
  // ============================================
  
  const startFormMapping = async (formPage: FormPage) => {
    if (!token || !userId) return
    
    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPage.id))
    setMappingStatus(prev => ({
      ...prev,
      [formPage.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetch('/api/form-mapper/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_page_route_id: formPage.id,
          user_id: parseInt(userId),
          network_id: formPage.network_id,
          test_cases: [
            { test_id: 1, test_name: 'Default Test', description: 'Auto-generated test case' }
          ]
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [formPage.id]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      // Start polling for status
      startMappingStatusPolling(formPage.id, data.session_id)
      
      setMessage(`Started mapping: ${formPage.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPage.id)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPage.id]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to start mapping: ${err.message}`)
    }
  }
  
  const startMappingStatusPolling = (formPageId: number, sessionId: number) => {
    // Clear any existing polling for this form
    if (mappingPollingRef.current[formPageId]) {
      clearInterval(mappingPollingRef.current[formPageId])
    }
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/form-mapper/sessions/${sessionId}/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const data = await response.json()
          
          setMappingStatus(prev => ({
            ...prev,
            [formPageId]: { 
              status: data.status, 
              sessionId,
              error: data.error 
            }
          }))
          
          // Stop polling if completed or failed
          if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
            stopMappingStatusPolling(formPageId)
            setMappingFormIds(prev => {
              const next = new Set(prev)
              next.delete(formPageId)
              return next
            })
            
            if (data.status === 'completed') {
              setMessage(`Mapping completed for form page ${formPageId}`)
            } else if (data.status === 'failed') {
              setError(`Mapping failed: ${data.error || 'Unknown error'}`)
            }
          }
        }
      } catch (err) {
        console.error('Failed to poll mapping status:', err)
      }
    }
    
    // Poll immediately, then every 3 seconds
    poll()
    mappingPollingRef.current[formPageId] = setInterval(poll, 3000)
  }
  
  const stopMappingStatusPolling = (formPageId: number) => {
    if (mappingPollingRef.current[formPageId]) {
      clearInterval(mappingPollingRef.current[formPageId])
      delete mappingPollingRef.current[formPageId]
    }
  }
  
  // Cleanup mapping polling on unmount
  useEffect(() => {
    return () => {
      Object.keys(mappingPollingRef.current).forEach(key => {
        clearInterval(mappingPollingRef.current[parseInt(key)])
      })
    }
  }, [])

  const qaNetworks = networks.filter(n => n.network_type?.toLowerCase() === 'qa')

  const getOverallStats = () => {
    const runningCount = discoveryQueue.filter(q => q.status === 'running').length
    const completedCount = discoveryQueue.filter(q => q.status === 'completed').length
    const failedCount = discoveryQueue.filter(q => q.status === 'failed').length
    const cancelledCount = discoveryQueue.filter(q => q.status === 'cancelled').length
    const totalFormsFound = discoveryQueue.reduce((sum, q) => sum + q.formsFound, 0)
    
    return { runningCount, completedCount, failedCount, cancelledCount, totalFormsFound }
  }

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

  const stopDiscovery = async () => {
    // Stop frontend polling
    shouldContinueRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    
    // Call backend to cancel running sessions
    if (currentSessionId && token) {
      try {
        await fetch(
          `/api/form-pages/sessions/${currentSessionId}/cancel`,
          { 
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` } 
          }
        )
      } catch (err) {
        console.error('Failed to cancel session:', err)
      }
    }
    
    // Update queue to show cancelled status
    setDiscoveryQueue(prev => prev.map(q => 
      q.status === 'running' || q.status === 'pending'
        ? { ...q, status: 'cancelled' }
        : q
    ))
    
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
                errorMessage: getErrorMessage(data.session.error_code, data.session.error_message),
                errorCode: data.session.error_code || undefined
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
    const failedItems = queue.filter(q => q.status === 'failed')
    
    if (failed > 0) {
      // Build error details for failed networks
      const errorDetails = failedItems.map(f => `${f.networkName}: ${f.errorMessage || 'Unknown error'}`).join('; ')
      setMessage(`Discovery finished. Completed: ${completed}, Failed: ${failed}. Found ${totalForms} form pages.`)
      if (failedItems.length > 0 && failedItems[0].errorMessage) {
        setError(errorDetails)
      }
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
      qa: { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' },
      staging: { bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' },
      production: { bg: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' }
    }
    return colors[type] || { bg: 'rgba(255,255,255,0.05)', color: '#94a3b8', border: 'rgba(255,255,255,0.1)' }
  }

  const openEditPanel = (formPage: FormPage) => {
    setEditingFormPage(formPage)
    setEditFormName(formPage.form_name)
    setEditNavigationSteps(formPage.navigation_steps || [])
    setExpandedSteps(new Set()) // Collapse all steps initially
    setShowEditPanel(true)
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
      const newSteps = [...prev]
      newSteps.splice(index + 1, 0, { action: 'click', selector: '', description: '' })
      return newSteps
    })
  }

  const saveFormPage = async () => {
    if (!editingFormPage || !token) return
    
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
        setShowEditPanel(false)
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId, token)
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
    if (!formPageToDelete || !token) return
    
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
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId, token)
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

  // No project selected
  if (!activeProjectId) {
    return (
      <div style={{ maxWidth: '700px', margin: '0 auto' }}>
        <div style={welcomeCardStyle}>
          <div style={{ fontSize: '64px', marginBottom: '24px' }}>👋</div>
          <h2 style={{ margin: '0 0 16px', fontSize: '28px', fontWeight: 700, color: '#fff' }}>Welcome!</h2>
          <p style={{ fontSize: '16px', color: '#94a3b8', margin: 0 }}>Please select a project from the top bar to get started.</p>
          <p style={{ color: '#64748b', fontSize: '14px', marginTop: '12px' }}>
            If you don't have any projects yet, click on the project dropdown and choose "Add Project".
          </p>
        </div>
      </div>
    )
  }

  const stats = getOverallStats()
  const totalNetworks = discoveryQueue.length
  const completedNetworks = stats.completedCount + stats.failedCount + stats.cancelledCount

  return (
    <div style={{ display: 'flex', gap: '0' }}>
      {/* Main Content Area */}
      <div style={{ 
        flex: showEditPanel ? '1 1 60%' : '1 1 100%',
        maxWidth: showEditPanel ? 'calc(100% - 520px)' : '1300px', 
        margin: showEditPanel ? '0' : '0 auto',
        transition: 'all 0.3s ease'
      }}>
        {/* CSS Animations */}
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.05); }
          }
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          @keyframes slideIn {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
          }
          .network-card:hover {
            border-color: rgba(99, 102, 241, 0.5) !important;
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.15) !important;
          }
          .table-row:hover {
            background: rgba(99, 102, 241, 0.08) !important;
          }
          .action-btn:hover {
            transform: scale(1.1);
            background: rgba(99, 102, 241, 0.2) !important;
          }
          .step-card:hover {
            border-color: rgba(99, 102, 241, 0.4) !important;
          }
          .expand-btn:hover {
            background: rgba(99, 102, 241, 0.2) !important;
          }
        `}</style>

        {error && (
          <div style={errorBoxStyle}>
            <span>❌</span> {error}
            <button onClick={() => setError(null)} style={closeButtonStyle}>×</button>
          </div>
        )}
        {message && (
          <div style={successBoxStyle}>
            <span>✅</span> {message}
            <button onClick={() => setMessage(null)} style={closeButtonStyle}>×</button>
          </div>
        )}

        {/* Form Pages Discovery Section - Collapsible */}
        <div style={cardStyle}>
          {/* Clickable Header to expand/collapse */}
          <div 
            onClick={() => !isDiscovering && setIsDiscoveryExpanded(!isDiscoveryExpanded)}
            style={{
            ...discoveryHeaderStyle,
            cursor: isDiscovering ? 'default' : 'pointer',
            marginBottom: isDiscoveryExpanded ? '28px' : 0
          }}
        >
          <div style={discoveryIconStyle}>
            <span>🔍</span>
          </div>
          <div style={{ flex: 1 }}>
            <h1 style={discoveryTitleStyle}>Form Pages Discovery</h1>
            <p style={discoverySubtitleStyle}>
              {isDiscoveryExpanded 
                ? 'Automatically discover all form pages in your web application using AI-powered crawling'
                : `Click to ${formPages.length > 0 ? 'start a new discovery' : 'begin discovering form pages'}`}
            </p>
          </div>
          {isDiscovering ? (
            <div style={discoveringBadgeStyle}>
              <div style={pulsingDotStyle} />
              <span>Discovery in Progress</span>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '14px 24px',
              background: isDiscoveryExpanded ? 'rgba(239, 68, 68, 0.15)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              borderRadius: '14px',
              fontSize: '16px',
              fontWeight: 600,
              color: '#fff',
              boxShadow: isDiscoveryExpanded ? 'none' : '0 4px 20px rgba(99, 102, 241, 0.3)',
              border: isDiscoveryExpanded ? '1px solid rgba(239, 68, 68, 0.3)' : 'none'
            }}>
              <span style={{ fontSize: '18px' }}>{isDiscoveryExpanded ? '▲' : '▼'}</span>
              {isDiscoveryExpanded ? 'Collapse' : 'Expand'}
            </div>
          )}
        </div>

        {/* Collapsible Content */}
        {(isDiscoveryExpanded || isDiscovering) && (
          networks.length === 0 ? (
            <div style={emptyStateStyle}>
              <div style={{ fontSize: '64px', marginBottom: '24px' }}>🌐</div>
              <h3 style={{ margin: '0 0 16px', fontSize: '26px', color: '#fff', fontWeight: 600 }}>No Networks Found</h3>
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '18px' }}>
                Open the <strong style={{ color: '#fff' }}>Test Sites</strong> tab from the sidebar to add your first test site.
              </p>
            </div>
          ) : (
            <>
              {/* Network Selection */}
              <div style={sectionStyle}>
                <div style={sectionHeaderStyle}>
                  <div>
                    <h3 style={sectionTitleStyle}>Select Test Sites</h3>
                    <p style={sectionSubtitleStyle}>Select QA environment test sites to discover form pages</p>
                  </div>
                  <button 
                    onClick={selectAllNetworks} 
                    style={selectAllBtnStyle}
                    disabled={isDiscovering}
                  >
                    {selectedNetworkIds.length === qaNetworks.length ? '✓ All Selected' : 'Select All'}
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {qaNetworks.map(network => {
                    const colors = getNetworkTypeColors(network.network_type)
                    const isSelected = selectedNetworkIds.includes(network.id)
                    const queueItem = discoveryQueue.find(q => q.networkId === network.id)
                    
                    return (
                      <div 
                        key={network.id}
                        onClick={() => !isDiscovering && toggleNetworkSelection(network.id)}
                        className="network-card"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '18px',
                          padding: '20px 26px',
                          border: isSelected ? '2px solid rgba(99, 102, 241, 0.5)' : '1px solid rgba(255,255,255,0.08)',
                          borderRadius: '16px',
                          background: isSelected 
                            ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))'
                            : 'rgba(255,255,255,0.02)',
                          cursor: isDiscovering ? 'not-allowed' : 'pointer',
                          opacity: isDiscovering ? 0.7 : 1,
                          transition: 'all 0.25s ease',
                          boxShadow: isSelected ? '0 4px 20px rgba(99, 102, 241, 0.1)' : 'none'
                      }}
                    >
                      <div style={{
                        ...networkCheckboxStyle,
                        background: isSelected 
                          ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' 
                          : 'rgba(255,255,255,0.05)',
                        borderColor: isSelected ? '#6366f1' : 'rgba(255,255,255,0.2)',
                        boxShadow: isSelected ? '0 4px 12px rgba(99, 102, 241, 0.3)' : 'none'
                      }}>
                        {isSelected && <span style={{ color: '#fff', fontSize: '14px', fontWeight: 700 }}>✓</span>}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '16px', color: '#fff', minWidth: '160px' }}>
                        {network.name}
                      </span>
                      <span style={{ fontSize: '14px', color: '#94a3b8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {network.url}
                      </span>
                      {network.login_username && (
                        <span style={{ fontSize: '13px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>👤</span> {network.login_username}
                        </span>
                      )}
                      <span style={{
                        padding: '8px 14px',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: 700,
                        background: colors.bg,
                        color: colors.color,
                        border: `1px solid ${colors.border}`,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        {getNetworkTypeLabel(network.network_type)}
                      </span>
                      {queueItem && (
                        <span style={{
                          padding: '8px 14px',
                          borderRadius: '20px',
                          fontSize: '13px',
                          fontWeight: 600,
                          background: queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.15)' :
                                     queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.15)' :
                                     queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255,255,255,0.05)',
                          color: queueItem.status === 'running' ? '#f59e0b' :
                                queueItem.status === 'completed' ? '#10b981' :
                                queueItem.status === 'failed' ? '#ef4444' :
                                queueItem.status === 'cancelled' ? '#f59e0b' : '#64748b',
                          border: `1px solid ${
                            queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.3)' :
                            queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.3)' :
                            queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255,255,255,0.1)'
                          }`
                        }}
                        title={queueItem.status === 'failed' && queueItem.errorMessage ? queueItem.errorMessage : undefined}
                        >
                          {queueItem.status === 'running' ? '⏳ Running' :
                           queueItem.status === 'completed' ? '✅ Done' :
                           queueItem.status === 'failed' ? '❌ Failed' :
                           queueItem.status === 'cancelled' ? '⏹ Cancelled' : '⏸ Pending'}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>

              {selectedNetworkIds.length > 0 && (
                <div style={selectedCountStyle}>
                  <span style={selectedCountBadgeStyle}>{selectedNetworkIds.length}</span>
                  <span style={{ color: '#94a3b8' }}>
                    network{selectedNetworkIds.length > 1 ? 's' : ''} selected
                    {selectedNetworkIds.length > 1 && (
                      <span style={{ marginLeft: '8px', color: '#64748b', fontSize: '14px' }}>
                        (will be processed sequentially)
                      </span>
                    )}
                  </span>
                </div>
              )}
            </div>

            {/* Action - Centered */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '32px 0 12px' }}>
              {isDiscovering ? (
                <button
                  onClick={stopDiscovery}
                  style={stopDiscoveryBtnStyle}
                >
                  <span>⏹</span> Stop Discovery
                </button>
              ) : (
                <button
                  onClick={startDiscovery}
                  disabled={selectedNetworkIds.length === 0}
                  style={{
                    ...startDiscoveryBtnStyle,
                    opacity: selectedNetworkIds.length === 0 ? 0.5 : 1,
                    cursor: selectedNetworkIds.length === 0 ? 'not-allowed' : 'pointer'
                  }}
                >
                  <span>🚀</span> Start Discovery
                </button>
              )}
            </div>
          </>
          )
        )}
      </div>

      {/* Discovery Status */}
      {discoveryQueue.length > 0 && (
        <div style={{ ...cardStyle, marginTop: '32px' }}>
          <h2 style={{ marginTop: 0, fontSize: '26px', color: '#fff', fontWeight: 700, marginBottom: '28px', letterSpacing: '-0.5px' }}>
            <span style={{ marginRight: '14px' }}>📊</span> Discovery Progress
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Test Sites</div>
              <div style={statValueStyle}>{completedNetworks} / {totalNetworks}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Forms Found</div>
              <div style={{ ...statValueStyle, color: '#10b981' }}>{stats.totalFormsFound}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Current</div>
              <div style={{ ...statValueStyle, fontSize: '18px', color: stats.runningCount > 0 ? '#f59e0b' : '#64748b' }}>
                {stats.runningCount > 0 
                  ? discoveryQueue.find(q => q.status === 'running')?.networkName || '-'
                  : 'None'}
              </div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Status</div>
              <div style={{ 
                ...statValueStyle, 
                fontSize: '17px',
                color: isDiscovering ? '#f59e0b' : 
                       stats.cancelledCount > 0 ? '#f59e0b' :
                       stats.failedCount > 0 ? '#ef4444' : '#10b981'
              }}>
                {isDiscovering ? 'IN PROGRESS' : 
                 stats.cancelledCount > 0 ? 'CANCELLED' :
                 stats.failedCount > 0 ? 'WITH ERRORS' : 'COMPLETED'}
              </div>
            </div>
          </div>

          {totalNetworks > 0 && (
            <div style={{ marginTop: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '13px', color: '#94a3b8' }}>
                <span>Overall Progress</span>
                <span style={{ fontWeight: 600 }}>{Math.round((completedNetworks / totalNetworks) * 100)}%</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.1)', borderRadius: '10px', height: '10px', overflow: 'hidden' }}>
                <div style={{
                  background: 'linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7)',
                  height: '100%',
                  width: `${(completedNetworks / totalNetworks) * 100}%`,
                  transition: 'width 0.4s ease',
                  borderRadius: '10px'
                }} />
              </div>
            </div>
          )}

          {/* Network Queue Status */}
          <div style={{ marginTop: '28px' }}>
            <h4 style={{ margin: '0 0 16px', fontSize: '14px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Site Queue</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {discoveryQueue.map((item, idx) => (
                <div 
                  key={item.networkId}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    padding: '14px 18px',
                    background: item.status === 'running' ? 'rgba(245, 158, 11, 0.1)' : 
                               item.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' :
                               item.status === 'failed' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.02)',
                    borderRadius: '12px',
                    border: `1px solid ${
                      item.status === 'running' ? 'rgba(245, 158, 11, 0.2)' :
                      item.status === 'completed' ? 'rgba(16, 185, 129, 0.2)' :
                      item.status === 'failed' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.05)'
                    }`
                  }}
                >
                  <span style={{ 
                    width: '32px', 
                    height: '32px', 
                    borderRadius: '50%', 
                    background: item.status === 'running' ? 'linear-gradient(135deg, #f59e0b, #d97706)' :
                               item.status === 'completed' ? 'linear-gradient(135deg, #10b981, #059669)' :
                               item.status === 'failed' ? 'linear-gradient(135deg, #ef4444, #dc2626)' : 'rgba(255,255,255,0.1)',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '13px',
                    fontWeight: 700,
                    boxShadow: item.status === 'running' ? '0 4px 15px rgba(245, 158, 11, 0.3)' : 'none'
                  }}>
                    {idx + 1}
                  </span>
                  <span style={{ flex: 1, fontWeight: 600, fontSize: '15px', color: '#fff' }}>
                    {item.networkName}
                  </span>
                  <span style={{ 
                    fontSize: '13px',
                    fontWeight: 600,
                    color: item.status === 'running' ? '#f59e0b' :
                          item.status === 'completed' ? '#10b981' :
                          item.status === 'failed' ? '#ef4444' :
                          item.status === 'cancelled' ? '#f59e0b' : '#64748b'
                  }}
                  title={item.status === 'failed' && item.errorMessage ? item.errorMessage : undefined}
                  >
                    {item.status === 'running' ? '⏳ Running...' :
                     item.status === 'completed' ? '✅ Completed' :
                     item.status === 'failed' ? '❌ Failed' :
                     item.status === 'cancelled' ? '⏹ Cancelled' : '⏸ Waiting'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Form Pages Table */}
      <div style={{ ...cardStyle, marginTop: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '28px', color: '#fff', fontWeight: 700, letterSpacing: '-0.5px' }}>
              <span style={{ marginRight: '14px' }}>📋</span>Discovered Form Pages
            </h2>
            <p style={{ margin: '12px 0 0', fontSize: '17px', color: '#94a3b8' }}>{formPages.length} forms found in this project</p>
          </div>
          {formPages.length > 10 && (
            <span style={{ fontSize: '15px', color: '#64748b', background: 'rgba(255,255,255,0.05)', padding: '12px 20px', borderRadius: '24px' }}>
              Showing {formPages.length} forms
            </span>
          )}
        </div>
        
        {loadingFormPages ? (
          <p style={{ color: '#94a3b8', marginTop: '24px', fontSize: '17px' }}>Loading form pages...</p>
        ) : formPages.length === 0 ? (
          <div style={emptyStateStyle}>
            <div style={{ fontSize: '64px', marginBottom: '24px' }}>📋</div>
            <p style={{ margin: 0, fontSize: '20px', color: '#fff', fontWeight: 500 }}>No form pages discovered yet</p>
            <p style={{ margin: '14px 0 0', fontSize: '17px', color: '#94a3b8' }}>Expand the discovery section above and start a discovery to find form pages</p>
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
                  <th style={{ ...thStyle, width: '160px', textAlign: 'center' }}>Actions</th>
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
                    className="table-row"
                    style={tableRowStyle}
                    onDoubleClick={() => openEditPanel(form)}
                  >
                    <td style={tdStyle}>
                      <strong style={{ fontSize: '15px', color: '#fff' }}>{form.form_name}</strong>
                      {form.parent_form_name && (
                        <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
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
                        background: form.is_root ? 'rgba(99, 102, 241, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: form.is_root ? '#818cf8' : '#fbbf24',
                        padding: '8px 14px',
                        borderRadius: '20px',
                        fontSize: '13px',
                        fontWeight: 600,
                        border: form.is_root ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
                      }}>
                        {form.is_root ? 'Root' : 'Child'}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ fontSize: '14px', color: '#e2e8f0' }}>
                        {form.created_at ? new Date(form.created_at).toLocaleDateString() : '-'}
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                        {form.created_at ? new Date(form.created_at).toLocaleTimeString() : ''}
                      </div>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
                        {/* Map Button */}
                        {mappingFormIds.has(form.id) ? (
                          <span style={{
                            padding: '8px 14px',
                            background: 'rgba(245, 158, 11, 0.15)',
                            color: '#f59e0b',
                            borderRadius: '8px',
                            fontSize: '13px',
                            fontWeight: 600,
                            border: '1px solid rgba(245, 158, 11, 0.3)'
                          }}>
                            ⏳ Mapping...
                          </span>
                        ) : mappingStatus[form.id]?.status === 'completed' ? (
                          <span style={{
                            padding: '8px 14px',
                            background: 'rgba(16, 185, 129, 0.15)',
                            color: '#10b981',
                            borderRadius: '8px',
                            fontSize: '13px',
                            fontWeight: 600,
                            border: '1px solid rgba(16, 185, 129, 0.3)'
                          }}>
                            ✅ Mapped
                          </span>
                        ) : mappingStatus[form.id]?.status === 'failed' ? (
                          <button 
                            onClick={() => startFormMapping(form)} 
                            className="action-btn"
                            style={{ ...actionButtonStyle, background: 'rgba(239, 68, 68, 0.15)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                            title={`Retry mapping - ${mappingStatus[form.id]?.error || 'Failed'}`}
                          >
                            🔄
                          </button>
                        ) : (
                          <button 
                            onClick={() => startFormMapping(form)} 
                            className="action-btn"
                            style={{ ...actionButtonStyle, background: 'rgba(99, 102, 241, 0.15)', borderColor: 'rgba(99, 102, 241, 0.3)' }}
                            title="Map this form page"
                          >
                            🗺️
                          </button>
                        )}
                        <button 
                          onClick={() => openEditPanel(form)} 
                          className="action-btn"
                          style={actionButtonStyle}
                          title="Edit form page"
                        >
                          ✏️
                        </button>
                        <button 
                          onClick={() => openDeleteModal(form)} 
                          className="action-btn"
                          style={{ ...actionButtonStyle, borderColor: 'rgba(239, 68, 68, 0.3)' }}
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
      </div>
      
      {/* Edit Form Page - Side Panel (not modal) */}
      {showEditPanel && editingFormPage && (
        <div style={{
          width: '520px',
          minWidth: '520px',
          background: 'linear-gradient(180deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98))',
          borderLeft: '1px solid rgba(255,255,255,0.12)',
          height: 'calc(100vh - 88px)',
          position: 'sticky',
          top: '88px',
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideIn 0.3s ease'
        }}>
          {/* Panel Header */}
          <div style={{
            padding: '28px 28px 24px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08))'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '26px', color: '#fff', fontWeight: 700, letterSpacing: '-0.5px' }}>
                  <span style={{ marginRight: '12px' }}>✏️</span>Edit Form Page
                </h2>
                <p style={{ margin: '10px 0 0', color: '#94a3b8', fontSize: '16px' }}>
                  Editing: <strong style={{ color: '#fff' }}>{editingFormPage.form_name}</strong>
                </p>
              </div>
              <button 
                onClick={() => setShowEditPanel(false)} 
                style={{
                  background: 'rgba(255,255,255,0.1)',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  color: '#94a3b8',
                  lineHeight: 1,
                  transition: 'all 0.2s ease'
                }}
              >×</button>
            </div>
          </div>

          {/* Panel Content - Scrollable */}
          <div style={{ flex: 1, overflow: 'auto', padding: '24px 28px' }}>
            {/* Form Name */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '10px', fontWeight: 600, color: '#e2e8f0', fontSize: '16px' }}>Form Name</label>
              <input
                type="text"
                value={editFormName}
                onChange={(e) => setEditFormName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '14px',
                  fontSize: '17px',
                  boxSizing: 'border-box',
                  background: 'rgba(255,255,255,0.05)',
                  color: '#fff',
                  outline: 'none'
                }}
              />
            </div>

            {/* Hierarchy Info */}
            <div style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '16px',
              padding: '20px 22px',
              border: '1px solid rgba(255,255,255,0.08)',
              marginBottom: '24px'
            }}>
              <h4 style={{ margin: '0 0 16px', fontSize: '15px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1.5px' }}>Hierarchy</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '12px' }}>
                <span style={{ fontSize: '15px', color: '#64748b', minWidth: '60px' }}>Type:</span>
                <span style={{
                  background: editingFormPage.is_root ? 'rgba(99, 102, 241, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: editingFormPage.is_root ? '#818cf8' : '#fbbf24',
                  padding: '8px 16px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600
                }}>
                  {editingFormPage.is_root ? 'Root Form' : 'Child Form'}
                </span>
              </div>
              {editingFormPage.parent_form_name && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{ fontSize: '15px', color: '#64748b', minWidth: '60px' }}>Parent:</span>
                  <span style={{ fontSize: '16px', color: '#e2e8f0' }}>{editingFormPage.parent_form_name}</span>
                </div>
              )}
            </div>

            {/* URL Info */}
            <div style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '16px',
              padding: '20px 22px',
              border: '1px solid rgba(255,255,255,0.08)',
              marginBottom: '28px'
            }}>
              <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1.5px' }}>URL</h4>
              <div style={{ fontSize: '14px', color: '#64748b', wordBreak: 'break-all', lineHeight: 1.6 }}>
                {editingFormPage.url}
              </div>
            </div>

            {/* AI-Discovered Path Section Header */}
            <div style={{
              display: 'flex',
              gap: '16px',
              background: 'rgba(0, 187, 249, 0.1)',
              border: '1px solid rgba(0, 187, 249, 0.2)',
              padding: '20px 22px',
              borderRadius: '16px',
              marginBottom: '20px',
              alignItems: 'flex-start'
            }}>
              <div style={{ fontSize: '28px' }}>💡</div>
              <div>
                <strong style={{ fontSize: '17px', color: '#00BBF9' }}>AI-Discovered Path</strong>
                <p style={{ margin: '8px 0 0', fontSize: '15px', color: '#94a3b8', lineHeight: 1.5 }}>
                  This navigation path was automatically discovered by AI. Click on a step to expand and edit it.
                </p>
              </div>
            </div>

            {/* Path Steps Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: '#fff', fontWeight: 600 }}>
                Path Steps ({editNavigationSteps.length})
              </h3>
              <button onClick={addStepAtEnd} style={{
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#818cf8',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                padding: '12px 18px',
                borderRadius: '12px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                ＋ Add Step
              </button>
            </div>

            {/* Collapsible Steps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {editNavigationSteps.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '50px 24px', color: '#64748b', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px dashed rgba(255,255,255,0.1)' }}>
                  <p style={{ fontSize: '17px', marginBottom: '20px' }}>No path steps defined.</p>
                  <button onClick={addStepAtEnd} style={{
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    color: '#fff',
                    border: 'none',
                    padding: '14px 24px',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}>＋ Add First Step</button>
                </div>
              ) : (
                editNavigationSteps.map((step, index) => (
                  <div 
                    key={index} 
                    className="step-card"
                    style={{
                      background: expandedSteps.has(index) ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255,255,255,0.02)',
                      border: expandedSteps.has(index) ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '14px',
                      overflow: 'hidden',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {/* Step Header - Always Visible */}
                    <div 
                      onClick={() => toggleStepExpansion(index)}
                      className="expand-btn"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        padding: '16px 18px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <div style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '15px',
                        fontWeight: 700,
                        flexShrink: 0
                      }}>{index + 1}</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                          {step.description || `Step ${index + 1}`}
                        </div>
                        <div style={{ fontSize: '13px', color: '#64748b' }}>
                          {step.action || 'click'} • {step.selector ? step.selector.substring(0, 40) + '...' : 'No selector'}
                        </div>
                      </div>
                      <span style={{ 
                        fontSize: '18px', 
                        color: '#64748b',
                        transform: expandedSteps.has(index) ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease'
                      }}>▼</span>
                    </div>

                    {/* Expanded Content */}
                    {expandedSteps.has(index) && (
                      <div style={{ padding: '0 18px 18px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', padding: '12px 0' }}>
                          <button 
                            onClick={() => addStepAfter(index)} 
                            style={{
                              background: 'rgba(99, 102, 241, 0.15)',
                              border: '1px solid rgba(99, 102, 241, 0.3)',
                              borderRadius: '10px',
                              padding: '10px 14px',
                              cursor: 'pointer',
                              fontSize: '15px',
                              color: '#818cf8'
                            }}
                            title="Add step after this"
                          >
                            ➕ Insert After
                          </button>
                          <button 
                            onClick={() => confirmDeleteStep(index)} 
                            style={{
                              background: 'rgba(239, 68, 68, 0.15)',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              borderRadius: '10px',
                              padding: '10px 14px',
                              cursor: 'pointer',
                              fontSize: '15px',
                              color: '#ef4444'
                            }}
                            title="Delete this step"
                          >
                            🗑️ Delete
                          </button>
                        </div>

                        <div style={{ display: 'flex', gap: '14px', marginBottom: '14px' }}>
                          <div style={{ flex: 1 }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#94a3b8' }}>Action</label>
                            <input
                              type="text"
                              value={step.action || ''}
                              disabled
                              style={{
                                width: '100%',
                                padding: '14px 16px',
                                border: '1px solid rgba(255,255,255,0.08)',
                                borderRadius: '12px',
                                fontSize: '15px',
                                boxSizing: 'border-box',
                                background: 'rgba(255,255,255,0.02)',
                                color: '#64748b',
                                cursor: 'not-allowed'
                              }}
                            />
                          </div>
                          <div style={{ flex: 2 }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#94a3b8' }}>Description</label>
                            <input
                              type="text"
                              value={step.description || ''}
                              onChange={(e) => updateNavigationStep(index, 'description', e.target.value)}
                              style={{
                                width: '100%',
                                padding: '14px 16px',
                                border: '1px solid rgba(255,255,255,0.12)',
                                borderRadius: '12px',
                                fontSize: '15px',
                                boxSizing: 'border-box',
                                background: 'rgba(255,255,255,0.05)',
                                color: '#fff',
                                outline: 'none'
                              }}
                              placeholder="Describe this action"
                            />
                          </div>
                        </div>
                        <div>
                          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#94a3b8' }}>Selector (Locator)</label>
                          <input
                            type="text"
                            value={step.selector || ''}
                            onChange={(e) => updateNavigationStep(index, 'selector', e.target.value)}
                            style={{
                              width: '100%',
                              padding: '14px 16px',
                              border: '1px solid rgba(255,255,255,0.12)',
                              borderRadius: '12px',
                              fontSize: '15px',
                              boxSizing: 'border-box',
                              background: 'rgba(255,255,255,0.05)',
                              color: '#fff',
                              outline: 'none'
                            }}
                            placeholder="CSS selector or XPath"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Panel Footer */}
          <div style={{
            padding: '20px 28px',
            borderTop: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(0,0,0,0.2)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '14px'
          }}>
            <button onClick={() => setShowEditPanel(false)} style={secondaryButtonStyle}>
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
      )}

      {/* Delete Step Confirmation */}
      {showDeleteStepConfirm && (
        <div style={modalOverlayStyle}>
          <div style={smallModalContentStyle}>
            <h3 style={{ marginTop: 0, color: '#ef4444', fontSize: '20px', fontWeight: 700 }}>
              <span style={{ marginRight: '8px' }}>⚠️</span>Delete Step?
            </h3>
            <p style={{ fontSize: '15px', color: '#e2e8f0', margin: '16px 0' }}>
              Are you sure you want to delete <strong style={{ color: '#fff' }}>Step {(stepToDeleteIndex || 0) + 1}</strong>?
            </p>
            <p style={{ fontSize: '14px', color: '#94a3b8', margin: '0 0 24px' }}>This action cannot be undone.</p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
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
            <h2 style={{ marginTop: 0, color: '#ef4444', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '22px', fontWeight: 700 }}>
              <span style={{ fontSize: '28px' }}>⚠️</span>
              Delete Form Page?
            </h2>
            
            <p style={{ fontSize: '16px', margin: '20px 0', color: '#e2e8f0' }}>
              Are you sure you want to delete <strong style={{ color: '#fff' }}>"{formPageToDelete.form_name}"</strong>?
            </p>
            
            <div style={deleteWarningBoxStyle}>
              <div style={{ display: 'flex', gap: '14px' }}>
                <span style={{ fontSize: '24px' }}>📝</span>
                <div>
                  <strong style={{ fontSize: '15px', color: '#00BBF9' }}>Important Note:</strong>
                  <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8' }}>
                    The form mapping (if present) will <strong style={{ color: '#fff' }}>NOT</strong> be deleted. 
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

const welcomeCardStyle: React.CSSProperties = {
  background: 'rgba(51, 65, 85, 0.5)',
  backdropFilter: 'blur(20px)',
  borderRadius: '28px',
  padding: '80px',
  textAlign: 'center',
  border: '1px solid rgba(255,255,255,0.08)',
  boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(51, 65, 85, 0.5)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '28px',
  padding: '36px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
}

const discoveryHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '24px',
  padding: '26px 32px',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))',
  border: '1px solid rgba(99, 102, 241, 0.2)',
  borderRadius: '20px',
  marginBottom: '0'
}

const discoveryIconStyle: React.CSSProperties = {
  fontSize: '36px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  borderRadius: '18px',
  padding: '18px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.3)'
}

const discoveryTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '32px',
  fontWeight: 700,
  color: '#fff',
  letterSpacing: '-0.5px'
}

const discoverySubtitleStyle: React.CSSProperties = {
  margin: '10px 0 0',
  fontSize: '18px',
  color: '#94a3b8',
  lineHeight: 1.5
}

const discoveringBadgeStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  background: 'rgba(16, 185, 129, 0.15)',
  border: '1px solid rgba(16, 185, 129, 0.3)',
  padding: '16px 28px',
  borderRadius: '30px',
  fontSize: '17px',
  fontWeight: 600,
  color: '#10b981'
}

const pulsingDotStyle: React.CSSProperties = {
  width: '14px',
  height: '14px',
  borderRadius: '50%',
  background: '#10b981',
  boxShadow: '0 0 14px rgba(16, 185, 129, 0.6)',
  animation: 'pulse 1.5s infinite'
}

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '100px 60px',
  background: 'rgba(255,255,255,0.02)',
  borderRadius: '24px',
  border: '2px dashed rgba(255,255,255,0.1)'
}

const sectionStyle: React.CSSProperties = {
  marginBottom: '12px'
}

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '28px'
}

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '26px',
  fontWeight: 700,
  color: '#fff',
  letterSpacing: '-0.5px'
}

const sectionSubtitleStyle: React.CSSProperties = {
  margin: '10px 0 0',
  fontSize: '18px',
  color: '#94a3b8'
}

const selectAllBtnStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  color: '#e2e8f0',
  border: '1px solid rgba(255,255,255,0.12)',
  padding: '16px 28px',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const networkCheckboxStyle: React.CSSProperties = {
  width: '28px',
  height: '28px',
  borderRadius: '10px',
  border: '2px solid rgba(255,255,255,0.2)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.2s ease',
  flexShrink: 0
}

const selectedCountStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  marginTop: '24px',
  fontSize: '17px'
}

const selectedCountBadgeStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  width: '36px',
  height: '36px',
  borderRadius: '50%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: '16px',
  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
}

const startDiscoveryBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  padding: '18px 48px',
  borderRadius: '16px',
  fontSize: '18px',
  fontWeight: 700,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.4)',
  transition: 'all 0.3s ease'
}

const stopDiscoveryBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  color: '#fff',
  border: 'none',
  padding: '18px 48px',
  borderRadius: '16px',
  fontSize: '18px',
  fontWeight: 700,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(239, 68, 68, 0.4)',
  transition: 'all 0.3s ease'
}

const tableContainerStyle: React.CSSProperties = {
  maxHeight: '700px',
  overflowY: 'auto',
  background: 'rgba(255,255,255,0.02)',
  borderRadius: '20px',
  border: '1px solid rgba(255,255,255,0.08)'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '22px 30px',
  borderBottom: '1px solid rgba(255,255,255,0.1)',
  fontWeight: 600,
  color: '#94a3b8',
  background: 'rgba(255,255,255,0.03)',
  position: 'sticky',
  top: 0,
  zIndex: 1,
  fontSize: '15px',
  textTransform: 'uppercase',
  letterSpacing: '1.5px'
}

const tableRowStyle: React.CSSProperties = {
  transition: 'all 0.2s ease',
  cursor: 'pointer',
  background: 'transparent'
}

const tdStyle: React.CSSProperties = {
  padding: '24px 30px',
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  verticalAlign: 'middle',
  fontSize: '18px',
  color: '#e2e8f0'
}

const pathStepsBadgeStyle: React.CSSProperties = {
  background: 'rgba(99, 102, 241, 0.15)',
  color: '#818cf8',
  padding: '14px 22px',
  borderRadius: '24px',
  fontSize: '17px',
  fontWeight: 600,
  border: '1px solid rgba(99, 102, 241, 0.3)'
}

const actionButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  padding: '16px 18px',
  cursor: 'pointer',
  fontSize: '20px',
  transition: 'all 0.2s ease'
}

const statBoxStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  padding: '30px',
  borderRadius: '20px',
  textAlign: 'center',
  border: '1px solid rgba(255,255,255,0.08)'
}

const statLabelStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#64748b',
  marginBottom: '12px',
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
  fontWeight: 600
}

const statValueStyle: React.CSSProperties = {
  fontSize: '36px',
  fontWeight: 700,
  color: '#fff'
}

const errorBoxStyle: React.CSSProperties = {
  background: 'rgba(239, 68, 68, 0.15)',
  color: '#fca5a5',
  padding: '20px 28px',
  borderRadius: '18px',
  marginBottom: '28px',
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  fontSize: '17px',
  border: '1px solid rgba(239, 68, 68, 0.3)'
}

const successBoxStyle: React.CSSProperties = {
  background: 'rgba(16, 185, 129, 0.15)',
  color: '#6ee7b7',
  padding: '18px 24px',
  borderRadius: '16px',
  marginBottom: '28px',
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  fontSize: '16px',
  border: '1px solid rgba(16, 185, 129, 0.3)'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '6px 12px',
  borderRadius: '8px',
  marginLeft: 'auto',
  color: 'inherit',
  transition: 'all 0.2s ease'
}

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: 'white',
  padding: '16px 32px',
  border: 'none',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.3)',
  transition: 'all 0.2s ease'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  color: '#e2e8f0',
  padding: '16px 32px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const dangerButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  color: 'white',
  padding: '16px 32px',
  border: 'none',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
  transition: 'all 0.2s ease'
}

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '24px'
}

const largeModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(51, 65, 85, 0.98), rgba(30, 41, 59, 0.98))',
  borderRadius: '28px',
  width: '100%',
  maxWidth: '1200px',
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
}

const modalHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '28px 36px',
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))'
}

const modalCloseButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: 'none',
  fontSize: '28px',
  cursor: 'pointer',
  padding: '12px 18px',
  borderRadius: '12px',
  color: '#94a3b8',
  lineHeight: 1,
  transition: 'all 0.2s ease'
}

const prominentNoteStyle: React.CSSProperties = {
  display: 'flex',
  gap: '20px',
  background: 'rgba(0, 187, 249, 0.1)',
  border: '1px solid rgba(0, 187, 249, 0.2)',
  color: '#94a3b8',
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
  width: '360px',
  padding: '28px',
  borderRight: '1px solid rgba(255,255,255,0.05)',
  overflowY: 'auto',
  background: 'rgba(255,255,255,0.02)'
}

const modalRightColumnStyle: React.CSSProperties = {
  flex: 1,
  padding: '28px',
  overflowY: 'auto'
}

const modalLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '12px',
  fontWeight: 600,
  color: '#e2e8f0',
  fontSize: '16px'
}

const modalInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '16px 20px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '12px',
  fontSize: '17px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.05)',
  color: '#fff',
  outline: 'none'
}

const infoSectionStyle: React.CSSProperties = {
  padding: '22px',
  background: 'rgba(255,255,255,0.03)',
  borderRadius: '16px',
  marginBottom: '20px',
  border: '1px solid rgba(255,255,255,0.08)'
}

const infoRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  marginBottom: '14px',
  fontSize: '16px'
}

const infoLabelStyle: React.CSSProperties = {
  color: '#64748b',
  minWidth: '70px',
  fontSize: '15px'
}

const childBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  background: 'rgba(255,255,255,0.05)',
  color: '#94a3b8',
  padding: '8px 14px',
  borderRadius: '10px',
  fontSize: '15px',
  border: '1px solid rgba(255,255,255,0.1)'
}

const addStepButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  padding: '12px 22px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)'
}

const pathStepsScrollContainerStyle: React.CSSProperties = {
  maxHeight: 'calc(90vh - 400px)',
  overflowY: 'auto',
  paddingRight: '12px'
}

const pathStepCardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '16px',
  marginBottom: '16px',
  overflow: 'hidden'
}

const stepHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  padding: '16px 20px',
  background: 'rgba(255,255,255,0.03)',
  borderBottom: '1px solid rgba(255,255,255,0.05)'
}

const stepNumberBadgeStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '16px',
  fontWeight: 700,
  flexShrink: 0,
  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
}

const stepActionButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  padding: '10px 12px',
  cursor: 'pointer',
  fontSize: '16px',
  borderRadius: '10px',
  transition: 'all 0.2s ease'
}

const stepFieldsStyle: React.CSSProperties = {
  padding: '20px'
}

const stepFieldRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '18px',
  marginBottom: '16px'
}

const stepFieldLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '10px',
  fontWeight: 500,
  color: '#94a3b8',
  fontSize: '15px'
}

const stepFieldInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '12px',
  fontSize: '16px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.05)',
  color: '#fff',
  outline: 'none'
}

const modalFooterStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '14px',
  padding: '24px 36px',
  borderTop: '1px solid rgba(255,255,255,0.05)',
  background: 'rgba(255,255,255,0.02)'
}

const smallModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(51, 65, 85, 0.98), rgba(30, 41, 59, 0.98))',
  borderRadius: '24px',
  padding: '40px',
  width: '100%',
  maxWidth: '500px',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
}

const deleteModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(51, 65, 85, 0.98), rgba(30, 41, 59, 0.98))',
  borderRadius: '28px',
  padding: '44px',
  width: '100%',
  maxWidth: '560px',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
}

const deleteWarningBoxStyle: React.CSSProperties = {
  background: 'rgba(0, 187, 249, 0.1)',
  border: '1px solid rgba(0, 187, 249, 0.2)',
  padding: '24px',
  borderRadius: '16px',
  marginTop: '24px'
}
