'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import TestPageEditPanel from './TestPageEditPanel'

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
}

interface TestPage {
  id: number
  project_id: number
  company_id: number
  network_id: number
  url: string
  test_name: string
  test_case_description: string
  status: 'not_mapped' | 'mapping' | 'mapped' | 'failed'
  created_at: string
  updated_at: string
  network_name?: string
  paths_count?: number
}

interface JunctionChoice {
  junction_id?: string
  junction_name: string
  option: string
  selector?: string
}

interface CompletedPath {
  id: number
  path_number: number
  path_junctions: JunctionChoice[]
  steps: any[]
  steps_count: number
  is_verified: boolean
  created_at: string
  updated_at: string
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

interface SessionStatus {
  session: {
    id: number
    status: string
    pages_crawled: number
    forms_found: number
    error_message: string | null
    error_code: string | null
  }
  forms: any[]
}

interface LoginLogoutData {
  login_stages: any[]
  logout_stages: any[]
  network_name: string
  url: string
  updated_at: string | null
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

export default function TestPagesPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  
  const [networks, setNetworks] = useState<Network[]>([])
  const [testPages, setTestPages] = useState<TestPage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Sorting
  const [sortField, setSortField] = useState<'name' | 'date'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  
  // Add/Edit modal
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingTestPage, setEditingTestPage] = useState<TestPage | null>(null)
  const [formData, setFormData] = useState({
    test_name: '',
    url: '',
    test_case_description: '',
    network_id: 0
  })
  const [saving, setSaving] = useState(false)
  
  // Delete confirm
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [testPageToDelete, setTestPageToDelete] = useState<TestPage | null>(null)
  const [deleting, setDeleting] = useState(false)
  
  // Detail panel
  const [showDetailPanel, setShowDetailPanel] = useState(false)
  const [selectedTestPage, setSelectedTestPage] = useState<TestPage | null>(null)
  const [paths, setPaths] = useState<CompletedPath[]>([])
  const [loadingPaths, setLoadingPaths] = useState(false)
  const [expandedPathId, setExpandedPathId] = useState<number | null>(null)
  const [editingPathStep, setEditingPathStep] = useState<{ pathId: number; stepIndex: number } | null>(null)
  const [editedPathStepData, setEditedPathStepData] = useState<any>(null)
  const [editTestName, setEditTestName] = useState('')
  const [editUrl, setEditUrl] = useState('')
  const [editTestCaseDescription, setEditTestCaseDescription] = useState('')
  const [mappingStatus, setMappingStatus] = useState<Record<number, { status: string; sessionId?: number; error?: string }>>({})
  const [showStepsModal, setShowStepsModal] = useState(false)
  const [viewingSteps, setViewingSteps] = useState<{type: 'login' | 'logout', networkName: string, steps: any[]}>({ type: 'login', networkName: '', steps: [] })

  // Mapping state
  const [mappingTestPageIds, setMappingTestPageIds] = useState<Set<number>>(new Set())
  const mappingPollingRef = useRef<Record<number, NodeJS.Timeout>>({})

  // Discovery state
  const [isDiscoveryExpanded, setIsDiscoveryExpanded] = useState(true)
  const [selectedNetworkIds, setSelectedNetworkIds] = useState<number[]>([])
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [discoveryQueue, setDiscoveryQueue] = useState<DiscoveryQueueItem[]>([])
  const [currentNetworkIndex, setCurrentNetworkIndex] = useState<number>(-1)
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const shouldContinueRef = useRef<boolean>(false)
  const [headless, setHeadless] = useState(false)
  
  // Login/Logout data
  const [loginLogoutData, setLoginLogoutData] = useState<Record<number, LoginLogoutData>>({})

  // Theme configuration - Pearl White (synced with layout.tsx)
  const theme = {
    name: 'Pearl White',
    colors: {
      bgGradient: 'linear-gradient(180deg, #dbe5f0 0%, #c8d8e8 50%, #b4c8dc 100%)',
      headerBg: 'rgba(248, 250, 252, 0.98)',
      sidebarBg: 'rgba(241, 245, 249, 0.95)',
      cardBg: 'rgba(242, 246, 250, 0.98)',
      cardBorder: 'rgba(100, 116, 139, 0.3)',
      accentPrimary: '#0369a1',
      accentSecondary: '#0ea5e9',
      textPrimary: '#1e293b',
      textSecondary: '#475569',
      statusOnline: '#16a34a',
    }
  }

  const getTheme = () => theme
  const isLightTheme = () => true
  
  const getBgColor = (type: string) => {
    if (type === 'header') {
      return 'rgba(241, 245, 249, 0.98)'
    }
    return theme.colors.cardBg
  }

  const getBorderColor = (intensity: string) => {
    return intensity === 'light' ? 'rgba(100, 116, 139, 0.2)' : 'rgba(100, 116, 139, 0.3)'
  }

  const getNetworkTypeColors = (networkType: string) => {
    switch (networkType?.toLowerCase()) {
      case 'qa':
        return { bg: 'rgba(16, 185, 129, 0.15)', color: '#059669', border: 'rgba(16, 185, 129, 0.3)' }
      case 'staging':
        return { bg: 'rgba(245, 158, 11, 0.15)', color: '#d97706', border: 'rgba(245, 158, 11, 0.3)' }
      case 'production':
        return { bg: 'rgba(239, 68, 68, 0.15)', color: '#dc2626', border: 'rgba(239, 68, 68, 0.3)' }
      default:
        return { bg: 'rgba(107, 114, 128, 0.15)', color: '#6b7280', border: 'rgba(107, 114, 128, 0.3)' }
    }
  }

  const getNetworkTypeLabel = (networkType: string) => {
    return networkType?.toUpperCase() || 'UNKNOWN'
  }

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    const storedCompanyId = localStorage.getItem('company_id')
    const storedProjectId = localStorage.getItem('active_project_id')
    
    if (!storedToken) {
      router.push('/login')
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
    setCompanyId(storedCompanyId)
    setActiveProjectId(storedProjectId)
    
    if (storedProjectId && storedCompanyId) {
      loadNetworks(storedProjectId, storedToken)
      loadTestPages(storedProjectId, storedToken)
      checkActiveMappingSessions(storedToken, storedProjectId)
    }
  }, [])

  // Listen for project changes and reload on navigation
  useEffect(() => {
    const checkAndLoadProject = () => {
      const currentProjectId = localStorage.getItem('active_project_id')
      const currentToken = localStorage.getItem('token')
      
      if (currentProjectId && currentToken) {
        if (currentProjectId !== activeProjectId) {
          setActiveProjectId(currentProjectId)
        }
        loadNetworks(currentProjectId, currentToken)
        loadTestPages(currentProjectId, currentToken)
        checkActiveMappingSessions(currentToken, currentProjectId)
      }
    }
    
    window.addEventListener('storage', checkAndLoadProject)
    window.addEventListener('focus', checkAndLoadProject)
    
    return () => {
      window.removeEventListener('storage', checkAndLoadProject)
      window.removeEventListener('focus', checkAndLoadProject)
    }
  }, [])

  const loadNetworks = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/networks`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (response.ok) {
        const data = await response.json()
        const allNetworks = [...(data.qa || []), ...(data.staging || []), ...(data.production || [])]
        setNetworks(allNetworks)
        
        // Fetch login/logout stages for QA networks
        const qaNetworks = allNetworks.filter((n: Network) => n.network_type?.toLowerCase() === 'qa')
        if (qaNetworks.length > 0) {
          fetchLoginLogoutStages(qaNetworks.map((n: Network) => n.id), authToken)
        }
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    }
  }

  const loadTestPages = async (projectId: string, authToken: string) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/test-pages?project_id=${projectId}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (response.ok) {
        const data = await response.json()
        setTestPages(data.test_pages || [])
      } else {
        setError('Failed to load test pages')
      }
    } catch (err) {
      setError('Failed to load test pages')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Check for active mapping sessions and restore UI state (prevent stuck mapping)
  const checkActiveMappingSessions = async (authToken: string, projectId: string) => {
    try {
      const response = await fetch('/api/form-mapper/active-sessions', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      if (response.ok) {
        const activeSessions = await response.json()

        const newMappingIds = new Set<number>()
        const newMappingStatus: Record<number, { status: string; sessionId?: number }> = {}

        for (const session of activeSessions) {
          const activeStatuses = ['running', 'initializing', 'pending', 'logging_in', 'navigating', 'extracting_initial_dom', 'getting_initial_screenshot', 'ai_analyzing', 'executing_step', 'waiting_for_dom', 'waiting_for_screenshot']
          if (activeStatuses.includes(session.status)) {
            newMappingIds.add(session.test_page_route_id)
            newMappingStatus[session.test_page_route_id] = {
              status: 'mapping',
              sessionId: session.session_id
            }
            // Resume polling for this session
            startMappingPolling(session.test_page_route_id, session.session_id, projectId)
          }
        }

        setMappingTestPageIds(newMappingIds)
        setMappingStatus(newMappingStatus)
      }
    } catch (err) {
      console.error('Failed to check active mapping sessions:', err)
    }
  }

  // Fetch login/logout stages for networks
  const fetchLoginLogoutStages = async (networkIds: number[], authToken: string) => {
    const results: Record<number, LoginLogoutData> = {}
    
    for (const networkId of networkIds) {
      try {
        const response = await fetch(
          `/api/form-pages/networks/${networkId}/login-logout-stages`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`,
              'Content-Type': 'application/json'
            }
          }
        )
        if (response.ok) {
          const data = await response.json()
          results[networkId] = {
            login_stages: data.login_stages || [],
            logout_stages: data.logout_stages || [],
            network_name: data.network_name,
            url: data.url,
            updated_at: data.updated_at
          }
        }
      } catch (err) {
        console.error(`Failed to fetch login/logout for network ${networkId}:`, err)
      }
    }
    
    setLoginLogoutData(results)
  }

  // Enrich test pages with network names when networks load
  useEffect(() => {
    if (networks.length > 0 && testPages.length > 0) {
      setTestPages(prev => prev.map(tp => ({
        ...tp,
        network_name: networks.find(n => n.id === tp.network_id)?.name || 'Unknown'
      })))
    }
  }, [networks])

  // Discovery functions
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

  const stopDiscovery = async () => {
    shouldContinueRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    
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
    
    await startNetworkDiscovery(queue, 0)
  }

  const startNetworkDiscovery = async (queue: DiscoveryQueueItem[], index: number) => {
    if (!shouldContinueRef.current || index >= queue.length) {
      finishDiscovery(queue)
      return
    }
    
    const item = queue[index]
    
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
        
        const queueWithSession = updatedQueue.map((q, i) => 
          i === index ? { ...q, sessionId } : q
        )
        setDiscoveryQueue(queueWithSession)
        setCurrentSessionId(sessionId)
        
        startPolling(queueWithSession, index, sessionId)
      } else {
        const errData = await response.json()
        console.error(`Failed to start discovery for network ${item.networkId}:`, errData.detail)
        
        const failedQueue = updatedQueue.map((q, i) => 
          i === index ? { ...q, status: 'failed' as const, errorMessage: errData.detail } : q
        )
        setDiscoveryQueue(failedQueue)
        
        await startNetworkDiscovery(failedQueue, index + 1)
      }
    } catch (err) {
      console.error(`Connection error for network ${item.networkId}:`, err)
      
      const failedQueue = updatedQueue.map((q, i) => 
        i === index ? { ...q, status: 'failed' as const, errorMessage: 'Connection error' } : q
      )
      setDiscoveryQueue(failedQueue)
      
      await startNetworkDiscovery(failedQueue, index + 1)
    }
  }

  const startPolling = (queue: DiscoveryQueueItem[], index: number, sessionId: number) => {
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
          
          setDiscoveryQueue(prev => prev.map((q, i) => 
            i === index ? {
              ...q,
              pagesSearched: data.session.pages_crawled,
              formsFound: data.session.forms_found
            } : q
          ))
          
          if (data.session.status === 'completed' || data.session.status === 'failed') {
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
            
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
            
            // Refresh login/logout data after discovery
            if (token) {
              fetchLoginLogoutStages(selectedNetworkIds, token)
            }
            
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
    
    if (failed > 0) {
      setMessage(`Discovery finished. Completed: ${completed}, Failed: ${failed}.`)
    } else {
      setMessage(`Discovery completed successfully! Login/logout stages captured.`)
    }
    
    // Collapse discovery section after completion
    setIsDiscoveryExpanded(false)
  }

  const getOverallStats = () => {
    const runningCount = discoveryQueue.filter(q => q.status === 'running').length
    const completedCount = discoveryQueue.filter(q => q.status === 'completed').length
    const failedCount = discoveryQueue.filter(q => q.status === 'failed').length
    const cancelledCount = discoveryQueue.filter(q => q.status === 'cancelled').length
    
    return { runningCount, completedCount, failedCount, cancelledCount }
  }

  // Test page functions
  const openAddModal = () => {
    setEditingTestPage(null)
    setFormData({
      test_name: '',
      url: '',
      test_case_description: '',
      network_id: networks.length > 0 ? networks[0].id : 0
    })
    setShowAddModal(true)
  }

  const openEditModal = (testPage: TestPage) => {
    setEditingTestPage(testPage)
    setFormData({
      test_name: testPage.test_name,
      url: testPage.url,
      test_case_description: testPage.test_case_description,
      network_id: testPage.network_id
    })
    setShowAddModal(true)
  }

  const handleSave = async () => {
    if (!formData.test_name || !formData.url || !formData.test_case_description) {
      setError('Please fill all required fields')
      return
    }
    
    if (!formData.network_id) {
      setError('Please select a network (test site)')
      return
    }
    
    setSaving(true)
    setError(null)
    
    try {
      const url = editingTestPage 
        ? `/api/test-pages/${editingTestPage.id}`
        : '/api/test-pages'
      
      const method = editingTestPage ? 'PUT' : 'POST'
      
      const body = editingTestPage ? {
        test_name: formData.test_name,
        url: formData.url,
        test_case_description: formData.test_case_description,
        network_id: formData.network_id
      } : {
        project_id: parseInt(activeProjectId!),
        company_id: parseInt(companyId!),
        network_id: formData.network_id,
        url: formData.url,
        test_name: formData.test_name,
        test_case_description: formData.test_case_description,
        created_by: parseInt(userId!)
      }
      
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        setMessage(editingTestPage ? 'Test page updated' : 'Test page created')
        setShowAddModal(false)
        loadTestPages(activeProjectId!, token!)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to save')
      }
    } catch (err) {
      setError('Failed to save test page')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!testPageToDelete) return
    
    setDeleting(true)
    try {
      const response = await fetch(`/api/test-pages/${testPageToDelete.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        setMessage('Test page deleted')
        setShowDeleteConfirm(false)
        setTestPageToDelete(null)
        loadTestPages(activeProjectId!, token!)
        if (selectedTestPage?.id === testPageToDelete.id) {
          setShowDetailPanel(false)
          setSelectedTestPage(null)
        }
      } else {
        setError('Failed to delete')
      }
    } catch (err) {
      setError('Failed to delete')
    } finally {
      setDeleting(false)
    }
  }

  const openDetailPanel = async (testPage: TestPage) => {
    setSelectedTestPage(testPage)
    setShowDetailPanel(true)
    setEditTestName(testPage.test_name)
    setEditUrl(testPage.url)
    setEditTestCaseDescription(testPage.test_case_description)
    setExpandedPathId(null)
    setLoadingPaths(true)
    try {
      const response = await fetch(`/api/test-pages/${testPage.id}/paths`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setPaths(data.paths || [])
      }
    } catch (err) {
      console.error('Failed to load paths:', err)
    } finally {
      setLoadingPaths(false)
    }
  }

  const handleSaveTestPage = async () => {
    if (!selectedTestPage) return
    setSaving(true)
    try {
      const response = await fetch(`/api/test-pages/${selectedTestPage.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          test_name: editTestName,
          url: editUrl,
          test_case_description: editTestCaseDescription
        })
      })
      if (response.ok) {
        setMessage('Test page updated')
        loadTestPages(activeProjectId!, token!)
        setSelectedTestPage({ ...selectedTestPage, test_name: editTestName, url: editUrl, test_case_description: editTestCaseDescription })
      } else {
        setError('Failed to update test page')
      }
    } catch (err) {
      setError('Failed to update test page')
    } finally {
      setSaving(false)
    }
  }

  const handleCancelMapping = async (testPageId: number) => {
    // Get the session ID for this test page
    const status = mappingStatus[testPageId]
    if (!status?.sessionId) {
      setError('No active mapping session found')
      return
    }

    // Set status to stopping
    setMappingStatus(prev => ({
      ...prev,
      [testPageId]: { ...prev[testPageId], status: 'stopping' }
    }))

    try {
      // Call API to cancel the mapping session
      const response = await fetch(`/api/form-mapper/sessions/${status.sessionId}/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        // Stop polling
        if (mappingPollingRef.current[testPageId]) {
          clearInterval(mappingPollingRef.current[testPageId])
          delete mappingPollingRef.current[testPageId]
        }

        // Update UI state
        setMappingTestPageIds(prev => {
          const next = new Set(prev)
          next.delete(testPageId)
          return next
        })
        setMappingStatus(prev => {
          const next = { ...prev }
          delete next[testPageId]
          return next
        })

        // Refresh test pages to get updated status
        loadTestPages(activeProjectId!, token!)
        setMessage('Mapping cancelled')
      } else {
        setError('Failed to cancel mapping')
        // Reset stopping status
        setMappingStatus(prev => ({
          ...prev,
          [testPageId]: { ...prev[testPageId], status: 'mapping' }
        }))
      }
    } catch (err) {
      console.error('Failed to cancel mapping:', err)
      setError('Failed to cancel mapping')
      setMappingStatus(prev => ({
        ...prev,
        [testPageId]: { ...prev[testPageId], status: 'mapping' }
      }))
    }
  }

  const handleDeletePath = async (pathId: number) => {
    if (!confirm('Delete this path?')) return
    try {
      const response = await fetch(`/api/form-mapper/paths/${pathId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setPaths(prev => prev.filter(p => p.id !== pathId))
        setMessage('Path deleted')
      } else {
        setError('Failed to delete path')
      }
    } catch (err) {
      setError('Failed to delete path')
    }
  }

  const handleSavePathStep = async (pathId: number, stepIndex: number, stepData?: any) => {
    if (!stepData) return
    try {
      const response = await fetch(`/api/form-mapper/paths/${pathId}/steps/${stepIndex}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(stepData)
      })
      if (response.ok) {
        setMessage('Step updated')
        // Refresh paths
        if (selectedTestPage) {
          const pathsResponse = await fetch(`/api/test-pages/${selectedTestPage.id}/paths`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (pathsResponse.ok) {
            const data = await pathsResponse.json()
            setPaths(data.paths || [])
          }
        }
      } else {
        setError('Failed to update step')
      }
    } catch (err) {
      setError('Failed to update step')
    }
  }

  const handleExportPath = (path: CompletedPath) => {
    const exportData = JSON.stringify(path, null, 2)
    const blob = new Blob([exportData], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `path-${path.path_number}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleRefreshPaths = async () => {
    if (!selectedTestPage) return
    setLoadingPaths(true)
    try {
      const response = await fetch(`/api/test-pages/${selectedTestPage.id}/paths`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setPaths(data.paths || [])
      }
    } catch (err) {
      console.error('Failed to load paths:', err)
    } finally {
      setLoadingPaths(false)
    }
  }

  const handleDeleteTestPageFromPanel = async (testPageId: number) => {
    try {
      const response = await fetch(`/api/test-pages/${testPageId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setMessage('Test page deleted')
        setShowDetailPanel(false)
        setSelectedTestPage(null)
        loadTestPages(activeProjectId!, token!)
      } else {
        setError('Failed to delete test page')
      }
    } catch (err) {
      setError('Failed to delete test page')
    }
  }

  const startMapping = async (testPage: TestPage) => {
    // Check if agent is online first
    try {
      const agentResponse = await fetch(`/api/agent/status?user_id=${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (agentResponse.ok) {
        const agentData = await agentResponse.json()
        if (agentData.status !== 'online') {
          setError('⚠️ Agent is offline. Please start your desktop agent before mapping.')
          return
        }
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
    }

    // Warn if paths exist - they will be deleted on remap
    if (paths.length > 0) {
      const confirmed = confirm(`⚠️ This test already has mapping results. Re-mapping will DELETE the existing mapping. Continue?`)
      if (!confirmed) return
    }

    setMappingTestPageIds(prev => new Set(prev).add(testPage.id))
    setError(null)
    
    try {
      const response = await fetch(`/api/test-pages/${testPage.id}/start-mapping`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: parseInt(userId!),
          agent_id: `agent-test-001`,
          config: { headless: false }
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setMessage('Mapping started')
        
        setTestPages(prev => prev.map(tp => 
          tp.id === testPage.id ? { ...tp, status: 'mapping' as const } : tp
        ))
        
        // Store sessionId so cancel can find it
        setMappingStatus(prev => ({
          ...prev,
          [testPage.id]: { status: 'mapping', sessionId: data.session_id }
        }))

        startMappingPolling(testPage.id, data.session_id, activeProjectId!)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to start mapping')
        setMappingTestPageIds(prev => {
          const next = new Set(prev)
          next.delete(testPage.id)
          return next
        })
      }
    } catch (err) {
      setError('Failed to start mapping')
      setMappingTestPageIds(prev => {
        const next = new Set(prev)
        next.delete(testPage.id)
        return next
      })
    }
  }

  const startMappingPolling = (testPageId: number, sessionId: number, projectId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/form-mapper/sessions/${sessionId}/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const data = await response.json()
          const status = data.status
          
          if (status === 'completed' || status === 'failed' || status === 'cancelled') {
            clearInterval(interval)
            delete mappingPollingRef.current[testPageId]
            
            setMappingTestPageIds(prev => {
              const next = new Set(prev)
              next.delete(testPageId)
              return next
            })

            // Clean up mappingStatus
            setMappingStatus(prev => {
              const next = { ...prev }
              delete next[testPageId]
              return next
            })
            
            loadTestPages(projectId, token!)

            // Refresh paths if the completed test page is currently selected
            if (selectedTestPage && selectedTestPage.id === testPageId) {
              handleRefreshPaths()
            }
            
            if (status === 'completed') {
              setMessage('Mapping completed!')
            } else {
              setError('Mapping failed')
            }
          }
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 3000)
    
    mappingPollingRef.current[testPageId] = interval
  }

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      Object.values(mappingPollingRef.current).forEach(interval => clearInterval(interval))
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  const getStatusBadge = (testPage: TestPage) => {
    const isMapping = mappingTestPageIds.has(testPage.id)
    const pathsCount = testPage.paths_count || 0
    
    if (isMapping) {
      return (
        <span style={{
          background: 'rgba(245, 158, 11, 0.15)',
          color: '#f59e0b',
          padding: '8px 16px',
          borderRadius: '20px',
          fontSize: '15px',
          fontWeight: 600
        }}>
          Mapping...
        </span>
      )
    }
    
    if (pathsCount > 0) {
      return (
        <span style={{
          background: 'rgba(16, 185, 129, 0.15)',
          color: '#059669',
          padding: '8px 16px',
          borderRadius: '20px',
          fontSize: '15px',
          fontWeight: 600
        }}>
          {pathsCount} path{pathsCount > 1 ? 's' : ''}
        </span>
      )
    }
    
    return (
      <span style={{
        background: 'rgba(107, 114, 128, 0.15)',
        color: '#6b7280',
        padding: '8px 16px',
        borderRadius: '20px',
        fontSize: '15px',
        fontWeight: 600
      }}>
        Not mapped
      </span>
    )
  }

  // Sort test pages
  const sortedTestPages = [...testPages].sort((a, b) => {
    if (sortField === 'name') {
      const nameA = (a.test_name || '').toLowerCase()
      const nameB = (b.test_name || '').toLowerCase()
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
  })

  // Clear messages after 5 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => {
        setMessage(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [message])

  if (!activeProjectId) {
    return (
      <div style={{ 
        textAlign: 'center', 
        padding: '100px 60px',
        background: theme.colors.cardBg,
        borderRadius: '20px',
        border: `1px solid ${theme.colors.cardBorder}`
      }}>
        <div style={{ fontSize: '64px', marginBottom: '24px' }}>📋</div>
        <p style={{ margin: 0, fontSize: '22px', color: theme.colors.textPrimary, fontWeight: 500 }}>No Project Selected</p>
        <p style={{ margin: '14px 0 0', fontSize: '18px', color: theme.colors.textSecondary }}>Please select a project from the dropdown above</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '0' }}>
      {/* Messages */}
      {message && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#10b981',
          padding: '16px 24px',
          borderRadius: '12px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>✅ {message}</span>
          <button onClick={() => setMessage(null)} style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}
      
      {error && !showDetailPanel && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#ef4444',
          padding: '16px 24px',
          borderRadius: '12px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>❌ {error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '18px' }}>×</button>
        </div>
      )}

      {showDetailPanel && selectedTestPage ? (
        <TestPageEditPanel
          editingTestPage={selectedTestPage}
          completedPaths={paths}
          loadingPaths={loadingPaths}
          token={token || ''}
          editTestName={editTestName}
          setEditTestName={setEditTestName}
          editUrl={editUrl}
          setEditUrl={setEditUrl}
          editTestCaseDescription={editTestCaseDescription}
          setEditTestCaseDescription={setEditTestCaseDescription}
          savingTestPage={saving}
          mappingTestPageIds={mappingTestPageIds}
          mappingStatus={mappingStatus}
          expandedPathId={expandedPathId}
          setExpandedPathId={setExpandedPathId}
          editingPathStep={editingPathStep}
          setEditingPathStep={setEditingPathStep}
          editedPathStepData={editedPathStepData}
          setEditedPathStepData={setEditedPathStepData}
          error={error}
          setError={setError}
          message={message}
          setMessage={setMessage}
          onClose={() => { setShowDetailPanel(false); setSelectedTestPage(null) }}
          onSave={handleSaveTestPage}
          onStartMapping={(id) => startMapping(testPages.find(tp => tp.id === id) || selectedTestPage)}
          onCancelMapping={handleCancelMapping}
          onDeletePath={handleDeletePath}
          onSavePathStep={handleSavePathStep}
          onExportPath={handleExportPath}
          onRefreshPaths={handleRefreshPaths}
          onDeleteTestPage={handleDeleteTestPageFromPanel}
          getTheme={getTheme}
          isLightTheme={isLightTheme}
        />
      ) : (
        <>
          {/* Discovery Section - Collapsible */}
      <div style={{
        background: theme.colors.cardBg,
        border: `1px solid ${theme.colors.cardBorder}`,
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
      }}>
        {/* Discovery Header - Click to expand/collapse */}
        <div 
          onClick={() => !isDiscovering && setIsDiscoveryExpanded(!isDiscoveryExpanded)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            cursor: isDiscovering ? 'default' : 'pointer',
            userSelect: 'none'
          }}
        >
          <div style={{
            fontSize: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '44px',
            height: '44px',
            background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
            borderRadius: '10px',
            boxShadow: '0 2px 6px rgba(37, 99, 235, 0.3)'
          }}>
            <span style={{ fontSize: '22px' }}>🔐</span>
          </div>
          <div style={{ flex: 1 }}>
            <h1 style={{
              margin: 0,
              fontSize: '24px',
              fontWeight: 700,
              color: theme.colors.textPrimary
            }}>Login/Logout Setup</h1>
            <p style={{
              margin: '6px 0 0',
              fontSize: '15px',
              color: theme.colors.textSecondary
            }}>
              {isDiscoveryExpanded 
                ? 'Discover login and logout steps for your test sites before creating test pages'
                : 'Click to expand and set up login/logout for your test sites'}
            </p>
          </div>
          {isDiscovering ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 20px',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              color: theme.colors.statusOnline,
              background: `${theme.colors.statusOnline}15`,
              border: `1px solid ${theme.colors.statusOnline}30`
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: theme.colors.statusOnline,
                animation: 'pulse 1.5s infinite'
              }} />
              <span>Discovery in Progress</span>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: isDiscoveryExpanded 
                ? 'rgba(220, 38, 38, 0.08)'
                : theme.colors.accentPrimary,
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
              color: isDiscoveryExpanded 
                ? '#dc2626'
                : '#fff'
            }}>
              <span style={{ fontSize: '13px' }}>{isDiscoveryExpanded ? '▲' : '▼'}</span>
              {isDiscoveryExpanded ? 'Collapse' : 'Expand'}
            </div>
          )}
        </div>

        {/* Collapsible Content */}
        {(isDiscoveryExpanded || isDiscovering) && (
          networks.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '60px 40px',
              marginTop: '20px',
              background: 'rgba(0,0,0,0.02)',
              borderRadius: '12px',
              border: `1px solid ${theme.colors.cardBorder}`
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🌐</div>
              <h3 style={{ margin: '0 0 12px', fontSize: '20px', color: theme.colors.textPrimary, fontWeight: 600 }}>No Networks Found</h3>
              <p style={{ margin: 0, color: theme.colors.textSecondary, fontSize: '16px' }}>
                Open the <strong style={{ color: theme.colors.textPrimary }}>Test Sites</strong> tab from the sidebar to add your first test site.
              </p>
            </div>
          ) : (
            <>
              {/* Network Selection */}
              <div style={{ 
                marginTop: '20px',
                marginBottom: '16px',
                background: 'rgba(16, 185, 129, 0.06)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(16, 185, 129, 0.15)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <h3 style={{ 
                      margin: 0,
                      fontSize: '20px',
                      fontWeight: 600,
                      color: theme.colors.textPrimary
                    }}>Select Test Sites</h3>
                    <p style={{ 
                      margin: '6px 0 0',
                      fontSize: '15px',
                      color: theme.colors.textSecondary
                    }}>Select QA environment test sites to discover login/logout steps</p>
                  </div>
                  <button 
                    onClick={selectAllNetworks} 
                    style={{
                      background: 'rgba(0,0,0,0.04)',
                      color: theme.colors.textPrimary,
                      border: '1px solid rgba(0,0,0,0.15)',
                      padding: '10px 18px',
                      borderRadius: '6px',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    disabled={isDiscovering}
                  >
                    {selectedNetworkIds.length === qaNetworks.length ? '✓ All Selected' : 'Select All'}
                  </button>
                </div>

                <div style={{ 
                  border: '1px solid rgba(0,0,0,0.12)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  background: 'rgba(242, 246, 250, 0.9)',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
                }}>
                  {qaNetworks.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: theme.colors.textSecondary }}>
                      No QA networks found. Add a QA network in Test Sites first.
                    </div>
                  ) : qaNetworks.map(network => {
                    const colors = getNetworkTypeColors(network.network_type)
                    const isSelected = selectedNetworkIds.includes(network.id)
                    const queueItem = discoveryQueue.find(q => q.networkId === network.id)
                    const hasLoginLogout = loginLogoutData[network.id]?.login_stages?.length > 0
                    
                    return (
                      <div 
                        key={network.id}
                        onClick={() => !isDiscovering && toggleNetworkSelection(network.id)}
                        className="network-card"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '14px',
                          padding: '12px 16px',
                          borderBottom: '1px solid rgba(0,0,0,0.08)',
                          background: isSelected 
                            ? 'rgba(59, 130, 246, 0.08)'
                            : 'transparent',
                          cursor: isDiscovering ? 'not-allowed' : 'pointer',
                          opacity: isDiscovering ? 0.7 : 1,
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <div style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: isSelected 
                            ? theme.colors.accentPrimary
                            : 'transparent',
                          border: isSelected 
                            ? `2px solid ${theme.colors.accentPrimary}` 
                            : '2px solid rgba(0,0,0,0.25)',
                          transition: 'all 0.15s ease',
                          flexShrink: 0
                        }}>
                          {isSelected && <span style={{ color: '#fff', fontSize: '14px', fontWeight: 700 }}>✓</span>}
                        </div>
                        <span style={{ fontWeight: 600, fontSize: '16px', color: theme.colors.textPrimary, minWidth: '150px' }}>
                          {network.name}
                        </span>
                        <span style={{ fontSize: '15px', color: theme.colors.textSecondary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {network.url}
                        </span>
                        {network.login_username && (
                          <span style={{ fontSize: '14px', color: theme.colors.textSecondary, display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>👤</span> {network.login_username}
                          </span>
                        )}
                        {hasLoginLogout && (
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: 600,
                            background: 'rgba(16, 185, 129, 0.15)',
                            color: '#059669',
                            border: '1px solid rgba(16, 185, 129, 0.3)'
                          }}>
                            ✓ Login Ready
                          </span>
                        )}
                        <span style={{
                          padding: '6px 14px',
                          borderRadius: '5px',
                          fontSize: '13px',
                          fontWeight: 600,
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
                            padding: '6px 14px',
                            borderRadius: '5px',
                            fontSize: '13px',
                            fontWeight: 600,
                            background: queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.1)' :
                                       queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' :
                                       queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                            color: queueItem.status === 'running' ? '#f59e0b' :
                                  queueItem.status === 'completed' ? '#10b981' :
                                  queueItem.status === 'failed' ? '#ef4444' :
                                  queueItem.status === 'cancelled' ? '#f59e0b' : theme.colors.textSecondary,
                            border: `1px solid ${
                              queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.3)' :
                              queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.3)' :
                              queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.3)' : getBorderColor('light')
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
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px', 
                    marginTop: '12px',
                    fontSize: '13px'
                  }}>
                    <span style={{
                      background: theme.colors.accentPrimary,
                      color: '#fff',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontWeight: 600,
                      fontSize: '12px'
                    }}>{selectedNetworkIds.length}</span>
                    <span style={{ color: theme.colors.textSecondary }}>
                      network{selectedNetworkIds.length > 1 ? 's' : ''} selected
                    </span>
                  </div>
                )}
              </div>

              {/* Action - Centered */}
              <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0 4px' }}>
                {isDiscovering ? (
                  <button
                    onClick={stopDiscovery}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      background: '#dc2626',
                      color: '#fff',
                      border: 'none',
                      padding: '10px 28px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    <span>⏹</span> Stop Discovery
                  </button>
                ) : (
                  <button
                    onClick={startDiscovery}
                    disabled={selectedNetworkIds.length === 0}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      background: selectedNetworkIds.length === 0 
                        ? '#9ca3af'
                        : 'linear-gradient(135deg, #3b82f6, #2563eb)',
                      color: '#fff',
                      border: 'none',
                      padding: '14px 36px',
                      borderRadius: '8px',
                      fontSize: '16px',
                      fontWeight: 600,
                      cursor: selectedNetworkIds.length === 0 ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s ease',
                      boxShadow: selectedNetworkIds.length === 0 
                        ? 'none' 
                        : '0 4px 12px rgba(37, 99, 235, 0.35)',
                      opacity: selectedNetworkIds.length === 0 ? 0.6 : 1
                    }}
                  >
                    <span style={{ fontSize: '18px' }}>🚀</span> Start Discovery
                  </button>
                )}
              </div>
            </>
          )
        )}
      </div>

      {/* Discovery Progress */}
      {discoveryQueue.length > 0 && (
        <div style={{
          background: theme.colors.cardBg,
          border: `1px solid ${theme.colors.cardBorder}`,
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px',
          position: 'relative'
        }}>
          {!isDiscovering && (
            <button
              onClick={() => setDiscoveryQueue([])}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'rgba(0,0,0,0.05)',
                border: '1px solid rgba(0,0,0,0.1)',
                borderRadius: '8px',
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: '14px',
                color: theme.colors.textSecondary,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>✕</span> Close
            </button>
          )}
          <h2 style={{ marginTop: 0, fontSize: '20px', color: theme.colors.textPrimary, fontWeight: 600, marginBottom: '16px' }}>
            <span style={{ marginRight: '10px' }}>📊</span> Discovery Progress
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {discoveryQueue.map((item, index) => (
              <div key={item.networkId} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                background: item.status === 'running' ? 'rgba(59, 130, 246, 0.08)' : 'rgba(0,0,0,0.02)',
                borderRadius: '8px',
                border: `1px solid ${item.status === 'running' ? 'rgba(59, 130, 246, 0.2)' : theme.colors.cardBorder}`
              }}>
                <span style={{ fontWeight: 600, minWidth: '150px' }}>{item.networkName}</span>
                <span style={{ flex: 1, color: theme.colors.textSecondary, fontSize: '14px' }}>
                  Pages: {item.pagesSearched}
                </span>
                <span style={{
                  padding: '4px 12px',
                  borderRadius: '4px',
                  fontSize: '13px',
                  fontWeight: 600,
                  background: 
                    item.status === 'running' ? 'rgba(245, 158, 11, 0.15)' :
                    item.status === 'completed' ? 'rgba(16, 185, 129, 0.15)' :
                    item.status === 'failed' ? 'rgba(239, 68, 68, 0.15)' :
                    item.status === 'cancelled' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                  color:
                    item.status === 'running' ? '#f59e0b' :
                    item.status === 'completed' ? '#10b981' :
                    item.status === 'failed' ? '#ef4444' :
                    item.status === 'cancelled' ? '#f59e0b' : '#6b7280'
                }}>
                  {item.status === 'running' ? '⏳ Running...' :
                   item.status === 'completed' ? '✅ Completed' :
                   item.status === 'failed' ? '❌ Failed' :
                   item.status === 'cancelled' ? '⏹ Cancelled' : '⏸ Pending'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}


          {/* Header */}
          <div style={{
            background: theme.colors.cardBg,
            borderRadius: '16px',
            padding: '24px 32px',
            marginBottom: '24px',
            border: `1px solid ${theme.colors.cardBorder}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h1 style={{ margin: 0, fontSize: '28px', color: theme.colors.textPrimary, fontWeight: 700 }}>
                <span style={{ marginRight: '12px' }}>🧪</span>Test Pages
              </h1>
              <p style={{ margin: '8px 0 0', color: theme.colors.textSecondary, fontSize: '16px' }}>
                Create and manage dynamic content test pages
              </p>
            </div>
            <button
              onClick={openAddModal}
              style={{
                background: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                padding: '14px 28px',
                fontSize: '16px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                boxShadow: '0 4px 15px rgba(14, 165, 233, 0.3)'
              }}
            >
              <span style={{ fontSize: '20px' }}>+</span> Add Test Page
            </button>
          </div>

          {/* Test Pages Table */}
          <div style={{ marginTop: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '24px', color: theme.colors.textPrimary, fontWeight: 600, letterSpacing: '-0.3px' }}>
                  <span style={{ marginRight: '10px' }}>📋</span>Your Test Pages
                </h2>
                <p style={{ margin: '8px 0 0', fontSize: '16px', color: theme.colors.textSecondary }}>{testPages.length} test pages in this project</p>
              </div>
            </div>

            {loading ? (
              <p style={{ color: theme.colors.textSecondary, marginTop: '24px', fontSize: '18px' }}>Loading test pages...</p>
            ) : testPages.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '100px 60px',
                background: theme.colors.cardBg,
                borderRadius: '20px',
                border: `1px solid ${theme.colors.cardBorder}`
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>🧪</div>
                <p style={{ margin: 0, fontSize: '22px', color: theme.colors.textPrimary, fontWeight: 500 }}>No test pages yet</p>
                <p style={{ margin: '14px 0 0', fontSize: '18px', color: theme.colors.textSecondary }}>Click "Add Test Page" to create your first test</p>
              </div>
            ) : (
              <div style={{
                maxHeight: '700px',
                overflowY: 'auto',
                background: 'linear-gradient(135deg, rgba(242, 246, 250, 0.98) 0%, rgba(242, 246, 250, 0.95) 100%)',
                border: '1px solid rgba(100,116,139,0.25)',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08)'
              }}>
                <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0' }}>
                  <thead>
                    <tr>
                      <th 
                        style={{
                          textAlign: 'left',
                          padding: '18px 24px',
                          borderBottom: '2px solid rgba(0,0,0,0.1)',
                          fontWeight: 600,
                          color: theme.colors.textSecondary,
                          background: getBgColor('header'),
                          position: 'sticky',
                          top: 0,
                          zIndex: 1,
                          fontSize: '15px',
                          textTransform: 'uppercase',
                          letterSpacing: '1px',
                          cursor: 'pointer',
                          userSelect: 'none'
                        }}
                        onClick={() => {
                          if (sortField === 'name') {
                            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                          } else {
                            setSortField('name')
                            setSortDirection('asc')
                          }
                        }}
                      >
                        Test Name {sortField === 'name' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                      </th>
                      <th style={{
                        textAlign: 'left',
                        padding: '18px 24px',
                        borderBottom: '2px solid rgba(0,0,0,0.1)',
                        fontWeight: 600,
                        color: theme.colors.textSecondary,
                        background: getBgColor('header'),
                        position: 'sticky',
                        top: 0,
                        zIndex: 1,
                        fontSize: '15px',
                        textTransform: 'uppercase',
                        letterSpacing: '1px'
                      }}>Status</th>
                      <th style={{
                        textAlign: 'left',
                        padding: '18px 24px',
                        borderBottom: '2px solid rgba(0,0,0,0.1)',
                        fontWeight: 600,
                        color: theme.colors.textSecondary,
                        background: getBgColor('header'),
                        position: 'sticky',
                        top: 0,
                        zIndex: 1,
                        fontSize: '15px',
                        textTransform: 'uppercase',
                        letterSpacing: '1px'
                      }}>URL</th>
                      <th 
                        style={{
                          textAlign: 'left',
                          padding: '18px 24px',
                          borderBottom: '2px solid rgba(0,0,0,0.1)',
                          fontWeight: 600,
                          color: theme.colors.textSecondary,
                          background: getBgColor('header'),
                          position: 'sticky',
                          top: 0,
                          zIndex: 1,
                          fontSize: '15px',
                          textTransform: 'uppercase',
                          letterSpacing: '1px',
                          cursor: 'pointer',
                          userSelect: 'none'
                        }}
                        onClick={() => {
                          if (sortField === 'date') {
                            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                          } else {
                            setSortField('date')
                            setSortDirection('desc')
                          }
                        }}
                      >
                        Created {sortField === 'date' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                      </th>
                      <th style={{
                        textAlign: 'center',
                        padding: '18px 24px',
                        borderBottom: '2px solid rgba(0,0,0,0.1)',
                        fontWeight: 600,
                        color: theme.colors.textSecondary,
                        background: getBgColor('header'),
                        position: 'sticky',
                        top: 0,
                        zIndex: 1,
                        fontSize: '15px',
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        width: '160px'
                      }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedTestPages.map((testPage, index) => (
                      <tr 
                        key={testPage.id}
                        className="table-row"
                        style={{
                          transition: 'all 0.2s ease',
                          cursor: 'pointer',
                          background: index % 2 === 0 ? 'rgba(219, 234, 254, 0.6)' : 'rgba(191, 219, 254, 0.5)'
                        }}
                        onDoubleClick={() => openDetailPanel(testPage)}
                      >
                        <td style={{
                          padding: '20px 24px',
                          borderBottom: '1px solid rgba(100,116,139,0.15)',
                          verticalAlign: 'middle',
                          fontSize: '16px',
                          color: theme.colors.textPrimary
                        }}>
                          <strong style={{ fontSize: '17px', color: theme.colors.textPrimary }}>{testPage.test_name}</strong>
                          <div style={{ 
                            fontSize: '14px', 
                            color: theme.colors.textSecondary, 
                            marginTop: '4px',
                            maxWidth: '300px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {testPage.test_case_description.substring(0, 60)}{testPage.test_case_description.length > 60 ? '...' : ''}
                          </div>
                        </td>
                        <td style={{
                          padding: '20px 24px',
                          borderBottom: '1px solid rgba(100,116,139,0.15)',
                          verticalAlign: 'middle'
                        }}>
                          {getStatusBadge(testPage)}
                        </td>
                        <td style={{ 
                          padding: '20px 24px', 
                          borderBottom: '1px solid rgba(100,116,139,0.15)', 
                          color: '#0369a1',
                          fontSize: '14px',
                          maxWidth: '250px'
                        }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={testPage.url}>
                            {testPage.url}
                          </div>
                        </td>
                        <td style={{ padding: '20px 24px', borderBottom: '1px solid rgba(100,116,139,0.15)', color: theme.colors.textSecondary }}>
                          {testPage.created_at ? (
                            <>
                              {new Date(testPage.created_at).toLocaleDateString()}
                              <div style={{ fontSize: '13px', opacity: 0.7 }}>
                                {new Date(testPage.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </div>
                            </>
                          ) : '-'}
                        </td>
                        <td style={{ padding: '20px 24px', borderBottom: '1px solid rgba(100,116,139,0.15)', textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                            <button 
                              onClick={() => openDetailPanel(testPage)}
                              className="action-btn"
                              style={{
                                background: 'rgba(59, 130, 246, 0.1)',
                                border: '2px solid rgba(59, 130, 246, 0.2)',
                                borderRadius: '12px',
                                padding: '16px 18px',
                                cursor: 'pointer',
                                fontSize: '20px',
                                transition: 'all 0.2s ease'
                              }}
                              title="View test page"
                            >
                              👁️
                            </button>
                            <button 
                              onClick={() => { setTestPageToDelete(testPage); setShowDeleteConfirm(true) }}
                              className="action-btn"
                              style={{
                                background: 'rgba(239, 68, 68, 0.08)',
                                border: '2px solid rgba(239, 68, 68, 0.15)',
                                borderRadius: '12px',
                                padding: '16px 18px',
                                cursor: 'pointer',
                                fontSize: '20px',
                                transition: 'all 0.2s ease'
                              }}
                              title="Delete test page"
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
          {/* Login/Logout Table */}
          {Object.entries(loginLogoutData).some(([_, data]) => (data.login_stages?.length > 0 || data.logout_stages?.length > 0)) && (
            <div style={{ marginTop: '32px' }}>
              <div style={{ marginBottom: '20px' }}>
                <h2 style={{ margin: 0, fontSize: '24px', color: theme.colors.textPrimary, fontWeight: 600, letterSpacing: '-0.3px' }}>
                  <span style={{ marginRight: '10px' }}>🔐</span>Login/Logout Steps
                </h2>
                <p style={{ margin: '8px 0 0', fontSize: '16px', color: theme.colors.textSecondary }}>Discovered authentication steps for your test sites</p>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, rgba(242, 246, 250, 0.98) 0%, rgba(242, 246, 250, 0.95) 100%)',
                border: '1px solid rgba(100,116,139,0.25)',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08)',
                overflow: 'hidden'
              }}>
                {Object.entries(loginLogoutData).filter(([_, data]) => (data.login_stages?.length > 0 || data.logout_stages?.length > 0)).map(([networkId, data]) => (
                  <div key={networkId}>
                    {/* Login Row */}
                    <div
                      onDoubleClick={() => {
                        setViewingSteps({ type: 'login', networkName: data.network_name, steps: data.login_stages || [] })
                        setShowStepsModal(true)
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '16px 24px',
                        background: 'rgba(16, 185, 129, 0.08)',
                        borderBottom: '1px solid rgba(100,116,139,0.15)',
                        borderLeft: '4px solid #10b981',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      className="table-row"
                    >
                      <div style={{ flex: 1 }}>
                        <strong style={{ fontSize: '17px', color: '#10b981' }}>🔐 Login</strong>
                        <div style={{ fontSize: '14px', color: theme.colors.textSecondary, marginTop: '4px' }}>
                          {data.network_name}
                        </div>
                      </div>
                      <span style={{
                        background: 'rgba(107, 114, 128, 0.2)',
                        color: '#6b7280',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        fontSize: '15px',
                        fontWeight: 600,
                        marginRight: '24px'
                      }}>
                        {data.login_stages?.length || 0} steps
                      </span>
                      <div style={{
                        color: '#0369a1',
                        fontSize: '14px',
                        maxWidth: '250px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        marginRight: '24px'
                      }}>
                        {data.url}
                      </div>
                      <div style={{ color: theme.colors.textSecondary, fontSize: '14px' }}>
                        {data.updated_at ? new Date(data.updated_at).toLocaleDateString() : '-'}
                      </div>
                    </div>

                    {/* Logout Row */}
                    <div
                      onDoubleClick={() => {
                        setViewingSteps({ type: 'logout', networkName: data.network_name, steps: data.logout_stages || [] })
                        setShowStepsModal(true)
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '16px 24px',
                        background: 'rgba(239, 68, 68, 0.08)',
                        borderBottom: '1px solid rgba(100,116,139,0.15)',
                        borderLeft: '4px solid #ef4444',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      className="table-row"
                    >
                      <div style={{ flex: 1 }}>
                        <strong style={{ fontSize: '17px', color: '#ef4444' }}>🚪 Logout</strong>
                        <div style={{ fontSize: '14px', color: theme.colors.textSecondary, marginTop: '4px' }}>
                          {data.network_name}
                        </div>
                      </div>
                      <span style={{
                        background: 'rgba(107, 114, 128, 0.2)',
                        color: '#6b7280',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        fontSize: '15px',
                        fontWeight: 600,
                        marginRight: '24px'
                      }}>
                        {data.logout_stages?.length || 0} steps
                      </span>
                      <div style={{
                        color: '#0369a1',
                        fontSize: '14px',
                        maxWidth: '250px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        marginRight: '24px'
                      }}>
                        {data.url}
                      </div>
                      <div style={{ color: theme.colors.textSecondary, fontSize: '14px' }}>
                        {data.updated_at ? new Date(data.updated_at).toLocaleDateString() : '-'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}


      {/* Add/Edit Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '20px',
            width: '100%',
            maxWidth: '600px',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <div style={{
              padding: '24px 28px',
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h2 style={{ margin: 0, fontSize: '22px', color: theme.colors.textPrimary }}>
                {editingTestPage ? '✏️ Edit Test Page' : '➕ Add Test Page'}
              </h2>
              <button
                onClick={() => setShowAddModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#9ca3af'
                }}
              >
                ×
              </button>
            </div>
            
            <div style={{ padding: '28px' }}>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Name *
                </label>
                <input
                  type="text"
                  value={formData.test_name}
                  onChange={(e) => setFormData({ ...formData, test_name: e.target.value })}
                  placeholder="e.g., Search Products Test"
                  style={{
                    width: '100%',
                    padding: '14px 18px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Site (Network) *
                </label>
                <select
                  value={formData.network_id}
                  onChange={(e) => setFormData({ ...formData, network_id: parseInt(e.target.value) })}
                  style={{
                    width: '100%',
                    padding: '14px 18px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    background: 'white'
                  }}
                >
                  <option value={0}>Select a test site...</option>
                  {networks.map(network => (
                    <option key={network.id} value={network.id}>
                      {network.name} - {network.url}
                    </option>
                  ))}
                </select>
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: theme.colors.textSecondary }}>
                  Select the test site with login credentials. Run discovery above if needed.
                </p>
              </div>
              
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Page URL *
                </label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="https://example.com/page"
                  style={{
                    width: '100%',
                    padding: '14px 18px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Case Description *
                </label>
                <textarea
                  value={formData.test_case_description}
                  onChange={(e) => setFormData({ ...formData, test_case_description: e.target.value })}
                  placeholder={`Describe what the test should do in natural language, e.g.:
1. Search for 'laptop' in the search box
2. Click on the first search result
3. Verify the product page shows price and description
4. Add to cart and verify cart count increases`}
                  rows={6}
                  style={{
                    width: '100%',
                    padding: '14px 18px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    resize: 'vertical',
                    fontFamily: 'inherit'
                  }}
                />
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: theme.colors.textSecondary }}>
                  Write clear steps in natural language. AI will generate the automation steps.
                </p>
              </div>
            </div>
            
            <div style={{
              padding: '20px 28px',
              borderTop: '1px solid #e5e7eb',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px'
            }}>
              <button
                onClick={() => setShowAddModal(false)}
                style={{
                  background: '#f3f4f6',
                  color: theme.colors.textPrimary,
                  border: 'none',
                  borderRadius: '10px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  background: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.7 : 1
                }}
              >
                {saving ? 'Saving...' : editingTestPage ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Steps View Modal */}
      {showStepsModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '20px',
            width: '100%',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <div style={{
              padding: '24px 28px',
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: viewingSteps.type === 'login' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
            }}>
              <h2 style={{ margin: 0, fontSize: '22px', color: theme.colors.textPrimary }}>
                {viewingSteps.type === 'login' ? '🔐 Login Steps' : '🚪 Logout Steps'} - {viewingSteps.networkName}
              </h2>
              <button
                onClick={() => setShowStepsModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#9ca3af'
                }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '28px' }}>
              {viewingSteps.steps.length === 0 ? (
                <p style={{ textAlign: 'center', color: theme.colors.textSecondary }}>No steps recorded</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {viewingSteps.steps.map((step: any, idx: number) => (
                    <div key={idx} style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                      padding: '12px 16px',
                      background: 'rgba(0,0,0,0.03)',
                      borderRadius: '8px',
                      border: '1px solid rgba(0,0,0,0.08)'
                    }}>
                      <span style={{
                        background: viewingSteps.type === 'login' ? '#10b981' : '#ef4444',
                        color: 'white',
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '14px',
                        fontWeight: 600,
                        flexShrink: 0
                      }}>
                        {idx + 1}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: theme.colors.textPrimary, fontSize: '15px' }}>
                          {step.action}
                        </div>
                        {step.selector && (
                          <div style={{ fontSize: '13px', color: theme.colors.textSecondary, marginTop: '4px', fontFamily: 'monospace' }}>
                            {step.selector}
                          </div>
                        )}
                        {step.description && (
                          <div style={{ fontSize: '13px', color: theme.colors.textSecondary, marginTop: '4px' }}>
                            {step.description}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {showDeleteConfirm && testPageToDelete && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '20px',
            width: '100%',
            maxWidth: '450px',
            padding: '28px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '20px', color: theme.colors.textPrimary }}>
              🗑️ Delete Test Page?
            </h3>
            <p style={{ color: theme.colors.textSecondary, margin: '0 0 24px' }}>
              Are you sure you want to delete "<strong>{testPageToDelete.test_name}</strong>"? 
              This will also delete all mapped paths.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => { setShowDeleteConfirm(false); setTestPageToDelete(null) }}
                style={{
                  background: '#f3f4f6',
                  color: theme.colors.textPrimary,
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px 24px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                style={{
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px 24px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: deleting ? 'not-allowed' : 'pointer',
                  opacity: deleting ? 0.7 : 1
                }}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CSS for hover effects */}
      <style jsx global>{`
        .table-row:hover {
          background: rgba(59, 130, 246, 0.15) !important;
        }
        .action-btn:hover {
          transform: scale(1.05);
        }
        .network-card:hover {
          background: rgba(59, 130, 246, 0.06) !important;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
        </>
      )}
    </div>
  )
}
