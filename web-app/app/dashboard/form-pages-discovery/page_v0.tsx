'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import React from "react"

import { useRouter } from 'next/navigation'
import UserProvidedInputsSection from './UserProvidedInputsSection'
import FormPageEditPanel from './FormPageEditPanel'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

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
  test_scenario_id?: number
  test_scenario_name?: string
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

interface LoginLogoutData {
  login_stages: NavigationStep[]
  logout_stages: NavigationStep[]
  network_name: string
  url: string
  updated_at: string | null
}

export default function DashboardPage() {
  const router = useRouter()
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
  
  // Completed Paths state
  const [completedPaths, setCompletedPaths] = useState<CompletedPath[]>([])
  const [loadingPaths, setLoadingPaths] = useState(false)
  const [expandedPathId, setExpandedPathId] = useState<number | null>(null)
  const [editingPathStep, setEditingPathStep] = useState<{ pathId: number; stepIndex: number } | null>(null)
  const [editedPathStepData, setEditedPathStepData] = useState<any>({})
  
  // Discovery section collapse state (collapsed by default when forms exist)
  const [isDiscoveryExpanded, setIsDiscoveryExpanded] = useState(false)
  
  // Rediscover form page state
  const [rediscoverMessage, setRediscoverMessage] = useState<string | null>(null)
  
  // Test Template Selection state
  const [testTemplates, setTestTemplates] = useState<{id: number, name: string, display_name: string, test_cases: any[]}[]>([])
  const [showMapModal, setShowMapModal] = useState(false)
  const [selectedFormForMapping, setSelectedFormForMapping] = useState<FormPage | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  
  // Login/Logout stages state
  const [loginLogoutData, setLoginLogoutData] = useState<Record<number, LoginLogoutData>>({})
  const [editingLoginLogout, setEditingLoginLogout] = useState<{
    networkId: number
    type: 'login' | 'logout'
    steps: NavigationStep[]
    networkName: string
    url: string
  } | null>(null)

  // Theme configuration - Pearl White only (fixed theme, synced with layout.tsx)
  const theme = {
    name: 'Pearl White',
    colors: {
      bgGradient: 'linear-gradient(180deg, #dbe5f0 0%, #c8d8e8 50%, #b4c8dc 100%)',
      headerBg: 'rgba(248, 250, 252, 0.98)',
      sidebarBg: 'rgba(241, 245, 249, 0.95)',
      cardBg: 'rgba(242, 246, 250, 0.98)',
      cardBorder: 'rgba(100, 116, 139, 0.3)',
      cardGlow: 'none',
      accentPrimary: '#0369a1',
      accentSecondary: '#0ea5e9',
      accentGlow: 'none',
      iconGlow: 'none',
      buttonGlow: 'none',
      textPrimary: '#1e293b',
      textSecondary: '#475569',
      textGlow: 'none',
      statusOnline: '#16a34a',
      statusGlow: '0 0 8px rgba(22, 163, 74, 0.5)',
      borderGlow: 'none'
    }
  }

  // Get current theme colors
  const getTheme = () => theme

  // Always light theme
  const isLightTheme = () => true

  // Get contrasting background for elements (darker on light themes)
  const getContrastBg = (opacity: number = 0.1) => {
    return `rgba(0, 0, 0, ${opacity})`
  }

  // Systematic background colors for consistency (light theme only)
  const getBgColor = (level: 'card' | 'section' | 'input' | 'header' | 'hover' | 'muted') => {
    switch (level) {
      case 'card': return 'rgba(255, 255, 255, 0.95)'
      case 'section': return 'rgba(0, 0, 0, 0.03)'
      case 'input': return 'rgba(255, 255, 255, 0.9)'
      case 'header': return 'rgba(0, 0, 0, 0.04)'
      case 'hover': return 'rgba(0, 0, 0, 0.06)'
      case 'muted': return 'rgba(0, 0, 0, 0.02)'
      default: return 'rgba(255, 255, 255, 0.95)'
    }
  }

  // Systematic border colors (light theme only)
  const getBorderColor = (emphasis: 'normal' | 'strong' | 'subtle' | 'light' = 'normal') => {
    switch (emphasis) {
      case 'strong': return 'rgba(0, 0, 0, 0.15)'
      case 'subtle': return 'rgba(0, 0, 0, 0.06)'
      case 'light': return 'rgba(0, 0, 0, 0.08)'
      default: return 'rgba(0, 0, 0, 0.1)'
    }
  }

  // Fetch test templates on mount
  useEffect(() => {
    const fetchTestTemplates = async () => {
      try {
        const response = await fetchWithAuth('/api/test-templates')
        if (response.ok) {
          const data = await response.json()
          setTestTemplates(data.templates || [])
          // Auto-select first template
          if (data.templates?.length > 0) {
            setSelectedTemplateId(data.templates[0].id)
          }
        }
      } catch (err) {
        console.error('Failed to fetch test templates:', err)
      }
    }
    fetchTestTemplates()
  }, [])

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
    const storedUserId = localStorage.getItem('user_id')
    const storedProjectId = localStorage.getItem('active_project_id')
    const storedProjectName = localStorage.getItem('active_project_name')

    // Verify auth via API (cookie sent automatically)
    fetchWithAuth('/api/auth/me')
      .then(res => {
        if (!res.ok) {
          window.location.href = '/login'
          return null
        }
        return res.json()
      })
      .then(data => {
        if (!data) return

        setUserId(String(data.user_id))
        setActiveProjectId(storedProjectId)
        setActiveProjectName(storedProjectName)

        if (storedProjectId) {
          loadNetworks(storedProjectId)
          loadFormPages(storedProjectId)
          checkActiveSessions(storedProjectId)
        }
      })
      .catch(() => {
        window.location.href = '/login'
      })
  }, [])

  // Check for active/running sessions on page load
  const checkActiveSessions = async (projectId: string) => {
    try {
      const response = await fetchWithAuth(
        `/api/form-pages/projects/${projectId}/active-sessions`
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
      loadNetworks(project.id.toString())
      loadFormPages(project.id.toString())
    }

    window.addEventListener('activeProjectChanged', handleProjectChange as EventListener)
    return () => window.removeEventListener('activeProjectChanged', handleProjectChange as EventListener)
  }, [])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // Fetch login/logout stages when formPages change
  useEffect(() => {
    if (formPages.length > 0) {
      // Get unique network IDs from form pages
      const networkIds = [...new Set(formPages.map(fp => fp.network_id))] as number[]
      fetchLoginLogoutStages(networkIds)
    }
  }, [formPages])

  const loadNetworks = async (projectId: string) => {
    setLoadingNetworks(true)
    try {
      const response = await fetchWithAuth(
          `/api/projects/${projectId}/networks`
        )
      
      if (response.ok) {
        const data = await response.json()
        const allNetworks = [
          ...data.qa.map((n: Network) => ({ ...n, network_type: 'qa' })),
          ...data.staging.map((n: Network) => ({ ...n, network_type: 'staging' })),
          ...data.production.map((n: Network) => ({ ...n, network_type: 'production' }))
        ]
        setNetworks(allNetworks)
      } else if (response.status === 401 || response.status === 403) {
        const errData = await response.json().catch(() => ({}))
        console.error('Auth error:', errData.detail)
        const detailStr = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail)
        if (detailStr && detailStr.toLowerCase().includes('token')) {
          setError(detailStr)
        }
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const loadFormPages = async (projectId: string) => {
    setLoadingFormPages(true)
    try {
      const response = await fetchWithAuth(
        `/api/projects/${projectId}/form-pages`
      )

      if (response.ok) {
        const data = await response.json()

        // Fetch paths counts for all form pages
        if (data.length > 0) {
          const ids = data.map((fp: any) => fp.id).join(',')
          const countsResponse = await fetchWithAuth(
              `/api/form-mapper/routes/paths-counts?form_page_route_ids=${ids}`
          )
          if (countsResponse.ok) {
            const counts = await countsResponse.json()
            setFormPages(data.map((fp: any) => ({
              ...fp,
              paths_count: counts[String(fp.id)] || 0
            })))
          } else {
            setFormPages(data)
          }
        } else {
          setFormPages(data)
        }

        // Check for active mapping sessions after loading form pages
        checkActiveMappingSessions()
      } else if (response.status === 401 || response.status === 403) {
        const errData = await response.json().catch(() => ({}))
        console.error('Auth error:', errData.detail)
        const detailStr = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail)
        if (detailStr && detailStr.toLowerCase().includes('token')) {
          setError(detailStr)
        }
      }
    } catch (err) {
      console.error('Failed to load form pages:', err)
    } finally {
      setLoadingFormPages(false)
    }
  }

  // Check for active mapping sessions and restore UI state
  const checkActiveMappingSessions = async () => {
    try {
      const response = await fetchWithAuth('/api/form-mapper/active-sessions')
      
      if (response.ok) {
        const activeSessions = await response.json()
        // activeSessions is array of { form_page_route_id, session_id, status }
        
        const newMappingIds = new Set<number>()
        const newMappingStatus: Record<number, { status: string; sessionId?: number }> = {}
        
        for (const session of activeSessions) {
          const activeStatuses = ['running', 'initializing', 'pending', 'logging_in', 'navigating', 'extracting_initial_dom', 'getting_initial_screenshot', 'ai_analyzing', 'executing_step', 'waiting_for_dom', 'waiting_for_screenshot']
          if (activeStatuses.includes(session.status)) {
            newMappingIds.add(session.form_page_route_id)
            newMappingStatus[session.form_page_route_id] = {
              status: 'mapping',
              sessionId: session.session_id
            }
            // Resume polling for this session
            startMappingStatusPolling(session.form_page_route_id, session.session_id)
          }
        }
        
        if (newMappingIds.size > 0) {
          setMappingFormIds(newMappingIds)
          setMappingStatus(prev => ({ ...prev, ...newMappingStatus }))
        }
      }
    } catch (err) {
      console.error('Failed to check active mapping sessions:', err)
    }
  }

  // Fetch login/logout stages for networks
  const fetchLoginLogoutStages = async (networkIds: number[]) => {
    const results: Record<number, LoginLogoutData> = {}

    for (const networkId of networkIds) {
      try {
        const response = await fetchWithAuth(
          `/api/form-pages/networks/${networkId}/login-logout-stages`
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

  // Open login/logout edit panel - creates a "fake" FormPage for reusing FormPageEditPanel
  const openLoginLogoutEditPanel = (networkId: number, type: 'login' | 'logout') => {
    const data = loginLogoutData[networkId]
    if (!data) return
    
    // Create a fake FormPage object with special negative ID
    // Login IDs: -1000 - networkId (e.g., -1001 for network 1)
    // Logout IDs: -2000 - networkId (e.g., -2001 for network 1)
    const fakeFormPage: FormPage = {
      id: type === 'login' ? (-1000 - networkId) : (-2000 - networkId),
      form_name: type === 'login' ? `🔐 Login - ${data.network_name}` : `🚪 Logout - ${data.network_name}`,
      url: data.url,
      network_id: networkId,
      navigation_steps: type === 'login' ? [...data.login_stages] : [...data.logout_stages],
      is_root: true,
      parent_form_id: null,
      created_at: data.updated_at || new Date().toISOString()
    }
    
    setEditingLoginLogout({
      networkId,
      type,
      steps: type === 'login' ? [...data.login_stages] : [...data.logout_stages],
      networkName: data.network_name,
      url: data.url
    })
    setEditingFormPage(fakeFormPage)
    setEditFormName(fakeFormPage.form_name)
    setEditNavigationSteps(type === 'login' ? [...data.login_stages] : [...data.logout_stages])
    setExpandedSteps(new Set())
    setCompletedPaths([])  // No paths for login/logout
    setShowEditPanel(true)
  }

  // Save login/logout steps
  const saveLoginLogoutSteps = async () => {
    if (!editingLoginLogout) return

    setSavingFormPage(true)
    try {
      const endpoint = editingLoginLogout.type === 'login'
        ? `/api/form-pages/networks/${editingLoginLogout.networkId}/login-stages`
        : `/api/form-pages/networks/${editingLoginLogout.networkId}/logout-stages`

      const body = editingLoginLogout.type === 'login'
        ? { login_stages: editNavigationSteps }
        : { logout_stages: editNavigationSteps }

      const response = await fetchWithAuth(endpoint, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        setMessage(`${editingLoginLogout.type === 'login' ? 'Login' : 'Logout'} steps updated successfully!`)
        
        // Update local state
        setLoginLogoutData(prev => ({
          ...prev,
          [editingLoginLogout.networkId]: {
            ...prev[editingLoginLogout.networkId],
            [editingLoginLogout.type === 'login' ? 'login_stages' : 'logout_stages']: editNavigationSteps
          }
        }))
        
        setShowEditPanel(false)
        setEditingLoginLogout(null)
      } else {
        setError('Failed to save steps')
      }
    } catch (err) {
      setError('Failed to save steps')
    } finally {
      setSavingFormPage(false)
    }
  }

  // ============================================
  // FORM MAPPING FUNCTIONS
  // ============================================
  
  const startFormMapping = async (formPage: FormPage) => {
    if (!userId) return

    // Check if agent is online first
    try {
      const agentResponse = await fetchWithAuth('/api/agent/status')
      if (agentResponse.ok) {
        const agentData = await agentResponse.json()
        if (agentData.status !== 'online') {
          setError('⚠️ Agent is offline. Please start your desktop agent before mapping.')
          return
        }
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
      // Continue anyway if check fails
    }

    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPage.id))
    setMappingStatus(prev => ({
      ...prev,
      [formPage.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetchWithAuth('/api/form-mapper/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_page_route_id: formPage.id,
          network_id: formPage.network_id,
          test_cases: []
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
      console.error('Failed to start mapping:', err.message)
      setError(`Failed to start mapping`)

    }
  }

  const openMapModal = (formPage: FormPage) => {
    setSelectedFormForMapping(formPage)
    setShowMapModal(true)
  }

  const startMappingWithTemplate = async () => {
    if (!selectedFormForMapping || !selectedTemplateId || !userId) return
    
    const template = testTemplates.find(t => t.id === selectedTemplateId)
    if (!template) return
    
    // Check if agent is online first
    try {
      const agentResponse = await fetchWithAuth('/api/agent/status')
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

    setShowMapModal(false)
    
    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(selectedFormForMapping.id))
    setMappingStatus(prev => ({
      ...prev,
      [selectedFormForMapping.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetchWithAuth('/api/form-mapper/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_page_route_id: selectedFormForMapping.id,
          network_id: selectedFormForMapping.network_id,
          test_cases: template.test_cases
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [selectedFormForMapping.id]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      startMappingStatusPolling(selectedFormForMapping.id, data.session_id)
      setMessage(`Started mapping: ${selectedFormForMapping.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(selectedFormForMapping.id)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [selectedFormForMapping.id]: { status: 'failed', error: err.message }
      }))
      console.error('Failed to start mapping:', err.message)
      setError(`Failed to start mapping`)
    }
    
    setSelectedFormForMapping(null)
  }

  const startMappingFromEditPanel = async () => {
    if (!editingFormPage || !userId) return
    
    // Warn if paths exist - they will be deleted on remap
    if (completedPaths.length > 0) {
      const confirmed = confirm(`⚠️ This form has ${completedPaths.length} existing path(s). Re-mapping will DELETE all existing paths. Continue?`)
      if (!confirmed) return
    }
    
    // Check if agent is online first
    try {
      const agentResponse = await fetchWithAuth('/api/agent/status')
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

    // Use default template (first one) or create_verify if available
    const defaultTemplate = testTemplates.find(t => t.name === 'create_verify') || testTemplates[0]
    if (!defaultTemplate) {
      console.error('No test template available')
      setError('Mapping failed')
      return
    }
    
    const formPageId = editingFormPage.id
    
    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPageId))
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'starting' }
    }))
    
    try {
      const response = await fetchWithAuth('/api/form-mapper/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_page_route_id: editingFormPage.id,
          network_id: editingFormPage.network_id,
          test_cases: defaultTemplate.test_cases
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      // Clear existing paths (they will be refreshed when mapping completes)
      setCompletedPaths([])
      
      startMappingStatusPolling(formPageId, data.session_id)
      setMessage(`Started mapping: ${editingFormPage.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPageId)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'failed', error: err.message }
      }))
      console.error('Failed to start mapping:', err.message)
      setError(`Failed to start mapping`)
    }
  }

  const startMappingWithScenario = async (formPageId: number, scenarioId: number) => {
    if (!editingFormPage || !userId) return

    // Check if agent is online first
    try {
      const agentResponse = await fetchWithAuth('/api/agent/status')
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

    // Use default template
    const defaultTemplate = testTemplates.find(t => t.name === 'create_verify') || testTemplates[0]
    if (!defaultTemplate) {
      setError('No test template available')
      return
    }

    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPageId))
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'starting' }
    }))

    try {
      const response = await fetchWithAuth('/api/form-mapper/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_page_route_id: formPageId,
          network_id: editingFormPage.network_id,
          test_cases: defaultTemplate.test_cases,
          test_scenario_id: scenarioId
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }

      const data = await response.json()

      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: data.session_id }
      }))

      startMappingStatusPolling(formPageId, data.session_id)
      setMessage(`Started mapping with test scenario`)

    } catch (err: any) {
      console.error('Failed to start mapping with scenario:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPageId)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to start mapping with scenario`)
    }
  }

  const continueMappingFromEditPanel = async () => {
    if (!editingFormPage || !userId) return

    // Must have existing paths to continue
    if (completedPaths.length === 0) {
      setError('No existing paths found. Use "Map Form Page" for initial mapping.')
      return
    }

    // Check if agent is online first
    try {
      const agentResponse = await fetchWithAuth('/api/agent/status')
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

    // Use default template
    const defaultTemplate = testTemplates.find(t => t.name === 'create_verify') || testTemplates[0]
    if (!defaultTemplate) {
      console.error('No test template available')
      setError('Continue mapping failed - no test template')
      return
    }

    const formPageId = editingFormPage.id

    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPageId))
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'evaluating' }
    }))

    try {
      const response = await fetchWithAuth(`/api/form-mapper/routes/${formPageId}/continue-mapping`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            network_id: editingFormPage.network_id,
            test_cases: defaultTemplate.test_cases
          })
        })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to continue mapping')
      }

      const data = await response.json()

      // Check if all paths already complete
      if (data.all_paths_complete) {
        setMappingFormIds(prev => {
          const next = new Set(prev)
          next.delete(formPageId)
          return next
        })
        setMappingStatus(prev => ({
          ...prev,
          [formPageId]: { status: 'completed' }
        }))
        setMessage('All paths already mapped - no additional paths needed!')
        return
      }

      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: data.session_id }
      }))

      startMappingStatusPolling(formPageId, parseInt(data.session_id))
      setMessage(`Continue mapping: ${editingFormPage.form_name} - evaluating for additional paths...`)

    } catch (err: any) {
      console.error('Failed to continue mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPageId)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to continue mapping`)
    }
  }

  const startMappingStatusPolling = (formPageId: number, sessionId: number) => {
    // Clear any existing polling for this form
    if (mappingPollingRef.current[formPageId]) {
      clearInterval(mappingPollingRef.current[formPageId])
    }
    
    const poll = async () => {
      try {
        const response = await fetchWithAuth(`/api/form-mapper/sessions/${sessionId}/status`)
        
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
          
          // Auto-refresh completed paths if edit panel is open for this form (during mapping too)
          if (editingFormPage && editingFormPage.id === formPageId) {
            fetchCompletedPaths(formPageId)
          }

          // Stop polling if completed or failed
          if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled' || data.status === 'no_more_paths') {
            stopMappingStatusPolling(formPageId)
            setMappingFormIds(prev => {
              const next = new Set(prev)
              next.delete(formPageId)
              return next
            })

            if (data.status === 'completed') {
              setMessage(`Mapping completed: ${editingFormPage?.form_name || formPageId}`)
              // Always refresh paths when mapping completes
              fetchCompletedPaths(formPageId)
            } else if (data.status === 'failed') {
              console.error('Mapping failed:', data.error)
              const isAIError = data.error && (
                data.error.includes('API Error') ||
                data.error.includes('API Overloaded') ||
                data.error.includes('credit balance') ||
                data.error.includes('budget exceeded') ||
                data.error.includes('AI parse failed')
              )
              setError(isAIError ? data.error : 'Mapping failed')
            } else if (data.status === 'no_more_paths') {
              setMessage('All form paths have been explored - no additional paths needed!')
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
  
  // Cancel a running mapping session
  const cancelMapping = async (formPageId: number) => {
    const status = mappingStatus[formPageId]
    if (!status?.sessionId) {
      console.error('No session ID found for form page', formPageId)
      return
    }
    
    // Immediately show "Stopping..." state
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'stopping', sessionId: status.sessionId }
    }))
    
    try {
      const response = await fetchWithAuth(`/api/form-mapper/sessions/${status.sessionId}/cancel`, {
          method: 'POST'
        })
      
      if (response.ok) {
        // Stop old polling
        stopMappingStatusPolling(formPageId)
        
        // Store the sessionId we're cancelling
        const cancelledSessionId = status.sessionId
        
        // Start polling until fully stopped (cancelled, failed, or completed)
        const pollUntilStopped = setInterval(async () => {
          try {
            const statusResponse = await fetchWithAuth(`/api/form-mapper/sessions/${cancelledSessionId}/status`)
            if (statusResponse.ok) {
              const data = await statusResponse.json()
              const sessionStatus = data.session?.status || data.status
              
              // Terminal states - fully stopped
              if (['cancelled', 'cancelled_ack', 'failed', 'completed'].includes(sessionStatus)) {
                clearInterval(pollUntilStopped)
                // Only update UI if no new session started for this form
                setMappingStatus(prev => {
                  if (prev[formPageId]?.sessionId === cancelledSessionId) {
                    setMappingFormIds(prevIds => {
                      const next = new Set(prevIds)
                      next.delete(formPageId)
                      return next
                    })
                    setMessage('Mapping stopped')
                    return { ...prev, [formPageId]: { status: 'cancelled', sessionId: cancelledSessionId } }
                  }
                  return prev
                })
              }
            }
          } catch (err) {
            console.error('Error polling for stop status:', err)
          }
        }, 1000)
        
        // Safety timeout - stop polling after 30 seconds regardless
        setTimeout(() => {
          clearInterval(pollUntilStopped)
          // Only update UI if no new session started for this form
          setMappingStatus(prev => {
            if (prev[formPageId]?.sessionId === cancelledSessionId) {
              setMappingFormIds(prevIds => {
                const next = new Set(prevIds)
                next.delete(formPageId)
                return next
              })
              return { ...prev, [formPageId]: { status: 'cancelled', sessionId: cancelledSessionId } }
            }
            return prev
          })
        }, 30000)
        
      } else {
        const errorData = await response.json()
        console.error('Failed to cancel mapping:', errorData.detail)
        // Revert to mapping state on error
        setMappingStatus(prev => ({
          ...prev,
          [formPageId]: { status: 'mapping', sessionId: status.sessionId }
        }))
      }
    } catch (err: any) {
      console.error('Failed to cancel mapping:', err.message)
      // Revert to mapping state on error
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: status.sessionId }
      }))
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
    if (currentSessionId) {
      try {
        await fetchWithAuth(
          `/api/form-pages/sessions/${currentSessionId}/cancel`,
          {
            method: 'POST'
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
      
      const response = await fetchWithAuth(
          `/api/form-pages/networks/${item.networkId}/locate?${params}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
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
          i === index ? { ...q, status: 'failed' as const, errorMessage: typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Discovery failed') } : q
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
        const response = await fetchWithAuth(
          `/api/form-pages/sessions/${sessionId}/status`
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
        console.error('Error:', errorDetails)
      }
    } else {
      setMessage(`Discovery completed! Found ${totalForms} new form pages across ${completed} test site(s).`)
    }
    
    // Reload form pages
    if (activeProjectId) {
      loadFormPages(activeProjectId)
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
    setCompletedPaths([]) // Reset paths
    setExpandedPathId(null)
    setShowEditPanel(true)
    if (formPage.id >= 0) {
      fetchCompletedPaths(formPage.id) // Fetch completed paths for regular forms only
    }
  }

  // Build combined list of all navigable items (login/logout + form pages)
  // This is used for Previous/Next navigation in the edit panel
  // Order matches the table display: Form pages (sorted) → Login → Logout (per network)
  const getAllNavigableItems = (): FormPage[] => {
    const items: FormPage[] = []
    
    // Get all network IDs from both form pages and login/logout data
    const networkIdsFromForms = [...new Set(formPages.map(fp => fp.network_id))]
    const networkIdsFromLoginLogout = Object.keys(loginLogoutData).map(id => parseInt(id))
    const allNetworkIds = [...new Set([...networkIdsFromForms, ...networkIdsFromLoginLogout])]
    
    // Sort network IDs for consistent ordering
    allNetworkIds.sort((a, b) => a - b)
    
    for (const networkId of allNetworkIds) {
      const loginLogout = loginLogoutData[networkId]
      
      // Add form pages for this network first (sorted by name)
      const networkFormPages = formPages
        .filter(fp => fp.network_id === networkId)
        .sort((a, b) => (a.form_name || '').localeCompare(b.form_name || ''))
      items.push(...networkFormPages)
      
      // Add login entry for this network (if exists)
      if (loginLogout && loginLogout.login_stages && loginLogout.login_stages.length > 0) {
        items.push({
          id: -1000 - networkId, // Unique negative ID per network for login
          form_name: `🔐 Login - ${loginLogout.network_name}`,
          url: loginLogout.url,
          network_id: networkId,
          navigation_steps: loginLogout.login_stages,
          is_root: true,
          parent_form_id: null,
          created_at: loginLogout.updated_at || new Date().toISOString()
        })
      }
      
      // Add logout entry for this network (if exists)
      if (loginLogout && loginLogout.logout_stages && loginLogout.logout_stages.length > 0) {
        items.push({
          id: -2000 - networkId, // Unique negative ID per network for logout
          form_name: `🚪 Logout - ${loginLogout.network_name}`,
          url: loginLogout.url,
          network_id: networkId,
          navigation_steps: loginLogout.logout_stages,
          is_root: true,
          parent_form_id: null,
          created_at: loginLogout.updated_at || new Date().toISOString()
        })
      }
    }
    
    return items
  }

  const navigateToPreviousFormPage = () => {
    if (!editingFormPage) return
    const allItems = getAllNavigableItems()
    const currentIndex = allItems.findIndex(fp => fp.id === editingFormPage.id)
    if (currentIndex > 0) {
      const prevItem = allItems[currentIndex - 1]
      // Check if it's a login/logout item (negative ID)
      if (prevItem.id < 0) {
        // Extract network ID from the special ID
        const networkId = prevItem.id <= -2000 ? -(prevItem.id + 2000) : -(prevItem.id + 1000)
        const type = prevItem.id <= -2000 ? 'logout' : 'login'
        openLoginLogoutEditPanel(networkId, type)
      } else {
        openEditPanel(prevItem)
      }
    }
  }

  const navigateToNextFormPage = () => {
    if (!editingFormPage) return
    const allItems = getAllNavigableItems()
    const currentIndex = allItems.findIndex(fp => fp.id === editingFormPage.id)
    if (currentIndex < allItems.length - 1) {
      const nextItem = allItems[currentIndex + 1]
      // Check if it's a login/logout item (negative ID)
      if (nextItem.id < 0) {
        // Extract network ID from the special ID
        const networkId = nextItem.id <= -2000 ? -(nextItem.id + 2000) : -(nextItem.id + 1000)
        const type = nextItem.id <= -2000 ? 'logout' : 'login'
        openLoginLogoutEditPanel(networkId, type)
      } else {
        openEditPanel(nextItem)
      }
    }
  }

  const getCurrentFormPageIndex = () => {
    if (!editingFormPage) return -1
    const allItems = getAllNavigableItems()
    return allItems.findIndex(fp => fp.id === editingFormPage.id)
  }

  const getTotalNavigableItems = () => {
    return getAllNavigableItems().length
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

  // ============ COMPLETED PATHS FUNCTIONS ============
  const fetchCompletedPaths = async (formPageRouteId: number) => {
  try {
    setLoadingPaths(true)
    const response = await fetchWithAuth(
      `/api/form-mapper/routes/${formPageRouteId}/paths`
    )
      if (response.ok) {
        const data = await response.json()
        setCompletedPaths(data.paths || [])
      } else {
        setCompletedPaths([])
      }
    } catch (err) {
      console.error('Failed to fetch completed paths:', err)
      setCompletedPaths([])
    } finally {
      setLoadingPaths(false)
    }
  }

  const handlePathRowDoubleClick = (pathId: number) => {
    setExpandedPathId(expandedPathId === pathId ? null : pathId)
    setEditingPathStep(null)
  }

  const handleEditPathStep = (pathId: number, stepIndex: number, step: any) => {
    setEditingPathStep({ pathId, stepIndex })
    setEditedPathStepData({
      action: step.action,
      selector: step.selector,
      value: step.value || '',
      description: step.description || ''
    })
  }

  const handleSavePathStep = async (pathId: number, stepIndex: number, stepData?: any) => {
      const dataToSave = stepData || editedPathStepData
      try {
        const response = await fetchWithAuth(
          `/api/form-mapper/paths/${pathId}/steps/${stepIndex}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(dataToSave)
            }
          )
      if (response.ok) {
        setCompletedPaths(completedPaths.map(path => {
          if (path.id === pathId) {
            const updatedSteps = [...path.steps]
            updatedSteps[stepIndex] = { ...updatedSteps[stepIndex], ...dataToSave }
            return { ...path, steps: updatedSteps }
          }
          return path
        }))
        setEditingPathStep(null)
        setEditedPathStepData({})
      }
    } catch (err) {
      console.error('Failed to save step:', err)
    }
  }

  const handleCancelPathStepEdit = () => {
    setEditingPathStep(null)
    setEditedPathStepData({})
  }

  const downloadPathJson = (path: CompletedPath) => {
    const jsonData = {
      path_number: path.path_number,
      path_junctions: path.path_junctions,
      steps: path.steps,
      steps_count: path.steps?.length || 0,
      is_verified: path.is_verified,
      created_at: path.created_at,
      form_page: editingFormPage?.form_name || 'unknown'
    }
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `path_${path.path_number}_${editingFormPage?.form_name?.replace(/\s+/g, '_') || 'form'}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getDisplaySteps = (steps: any[]): any[] => {
    return (steps || []).map(step => {
      const { is_junction, junction_info, ...displayStep } = step
      return displayStep
    })
  }

  const saveFormPage = async () => {
    if (!editingFormPage) return

    setSavingFormPage(true)
    try {
      const response = await fetchWithAuth(
        `/api/form-pages/routes/${editingFormPage.id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
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
          loadFormPages(activeProjectId)
        }
      } else {
        const errData = await response.json()
        console.error('Failed to update form page:', errData.detail)
      }
    } catch (err) {
      console.error('Connection error')
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
      const response = await fetchWithAuth(
        `/api/form-pages/routes/${formPageToDelete.id}`,
        {
          method: 'DELETE'
        }
      )
      
      if (response.ok) {
        setMessage('Form page deleted successfully!')
        setShowDeleteModal(false)
        setFormPageToDelete(null)
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId)
        }
      } else {
        const errData = await response.json()
        console.error('Failed to delete form page:', errData.detail)
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingFormPage(false)
    }
  }

  // Rediscover form page - deletes and redirects to main page with discovery expanded
  const rediscoverFormPage = async (formPageId: number) => {

    try {
      const response = await fetchWithAuth(
        `/api/form-pages/routes/${formPageId}`,
        {
          method: 'DELETE'
        }
      )
      
      if (response.ok) {
        // Close edit panel
        setShowEditPanel(false)
        setEditingFormPage(null)
        
        // Expand discovery section
        setIsDiscoveryExpanded(true)
        
        // Show message to user
        setRediscoverMessage('Form page deleted. Select a test site and click "Start Discovery" to rediscover form pages.')
        
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId)
        }
      } else {
        const errData = await response.json()
        console.error('Failed to delete form page:', errData.detail)
      }
    } catch (err) {
      console.error('Connection error')
    }
  }


  // Delete a path
  const deletePath = async (pathId: number) => {

    const confirmed = confirm('Are you sure you want to delete this path?')
    if (!confirmed) return

    try {
      const response = await fetchWithAuth(
        `/api/form-mapper/paths/${pathId}`,
        {
          method: 'DELETE'
        }
      )

      if (response.ok) {
        setMessage('Path deleted successfully!')
        // Refresh paths
        if (editingFormPage) {
          fetchCompletedPaths(editingFormPage.id)
        }
      } else {
        const errData = await response.json()
        setError(typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Failed to delete path'))
      }
    } catch (err) {
      console.error('Connection error')
    }
  }
  // Color system - matching dashboard layout
  const t = {
    pageBg: '#f0f4f8',
    cardBg: '#ffffff',
    mutedBg: '#f1f5f9',
    hoverBg: '#e8f4f8',
    text: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#64748b',
    brand: '#0891b2',
    brandLight: 'rgba(8, 145, 178, 0.15)',
    brandBorder: 'rgba(8, 145, 178, 0.35)',
    border: '#d8e2ec',
    borderLight: '#e8eef4',
    success: '#4a9a8e',
    successBg: '#eef6f4',
    successBorder: '#c4ddd8',
    warning: '#d97706',
    warningBg: '#fef3c7',
    warningBorder: '#fbbf24',
    danger: '#dc2626',
    dangerBg: '#fee2e2',
    dangerBorder: '#fca5a5',
  }

  // No project selected
  if (!activeProjectId) {
    return (
      <div style={{ maxWidth: '520px', margin: '80px auto', animation: 'slideUp 0.4s ease' }}>
        <div style={{
          background: t.cardBg,
          borderRadius: '16px',
          padding: '60px 40px',
          textAlign: 'center',
          border: `1px solid ${t.border}`,
          boxShadow: '0 1px 4px rgba(0,0,0,0.06), 0 8px 32px rgba(0,0,0,0.04)',
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '14px',
            background: `linear-gradient(135deg, ${t.brand}, #06b6d4)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 4px 12px rgba(8, 145, 178, 0.25)',
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <h2 style={{ margin: '0 0 10px', fontSize: '22px', fontWeight: 700, color: t.text, letterSpacing: '-0.01em' }}>Select a Project</h2>
          <p style={{ fontSize: '15px', color: t.textSecondary, margin: 0, lineHeight: 1.5 }}>Choose a project from the top bar to get started with form discovery.</p>
          <p style={{ color: t.textMuted, fontSize: '13px', marginTop: '12px', lineHeight: 1.5 }}>
            {"If you don't have any projects yet, click on the project dropdown and choose \"Add Project\"."}
          </p>
        </div>
      </div>
    )
  }

  const stats = getOverallStats()
  const totalNetworks = discoveryQueue.length
  const completedNetworks = stats.completedCount + stats.failedCount + stats.cancelledCount

  // ============ FULL PAGE EDIT VIEW ============
  if (showEditPanel && editingFormPage) {
    // Determine if this is a login/logout edit (using special negative IDs)
    // Login IDs: -1001, -1002, etc (for network 1, 2, etc)
    // Logout IDs: -2001, -2002, etc (for network 1, 2, etc)
    const isLoginLogoutEdit = editingFormPage.id < 0
    const loginLogoutType = (editingFormPage.id <= -1000 && editingFormPage.id > -2000) 
      ? 'login' 
      : (editingFormPage.id <= -2000 ? 'logout' : null)
    
    return (
      <FormPageEditPanel
        editingFormPage={editingFormPage}
        formPages={getAllNavigableItems()}
        completedPaths={isLoginLogoutEdit ? [] : completedPaths}
        loadingPaths={isLoginLogoutEdit ? false : loadingPaths}
        editFormName={editFormName}
        setEditFormName={setEditFormName}
        editNavigationSteps={editNavigationSteps}
        setEditNavigationSteps={setEditNavigationSteps}
        savingFormPage={savingFormPage}
        expandedSteps={expandedSteps}
        setExpandedSteps={setExpandedSteps}
        mappingFormIds={mappingFormIds}
        mappingStatus={mappingStatus}
        expandedPathId={expandedPathId}
        setExpandedPathId={setExpandedPathId}
        editingPathStep={editingPathStep}
        setEditingPathStep={setEditingPathStep}
        editedPathStepData={editedPathStepData}
        setEditedPathStepData={setEditedPathStepData}
        showDeleteStepConfirm={showDeleteStepConfirm}
        setShowDeleteStepConfirm={setShowDeleteStepConfirm}
        stepToDeleteIndex={stepToDeleteIndex}
        setStepToDeleteIndex={setStepToDeleteIndex}
        error={error}
        setError={setError}
        message={message}
        setMessage={setMessage}
        onClose={() => { 
          setShowEditPanel(false)
          if (isLoginLogoutEdit) {
            setEditingLoginLogout(null)
          }
        }}
        onSave={isLoginLogoutEdit ? saveLoginLogoutSteps : saveFormPage}
        onStartMapping={isLoginLogoutEdit ? () => {} : startMappingFromEditPanel}
        onCancelMapping={cancelMapping}
        onContinueMapping={isLoginLogoutEdit ? () => {} : continueMappingFromEditPanel}
        onOpenEditPanel={openEditPanel}
        onDeletePath={deletePath}
        onSavePathStep={handleSavePathStep}
        onExportPath={downloadPathJson}
        onStartMappingWithScenario={isLoginLogoutEdit ? () => {} : startMappingWithScenario}
        onRefreshPaths={() => !isLoginLogoutEdit && fetchCompletedPaths(editingFormPage.id)}
        onDeleteFormPage={isLoginLogoutEdit ? () => {} : rediscoverFormPage}
        getTheme={getTheme}
        isLightTheme={isLightTheme}
        isLoginLogout={isLoginLogoutEdit}
        loginLogoutType={loginLogoutType}
      />
    )
  }


  // ============ MAIN DISCOVERY PAGE ============
  return (
    <div style={{ width: '100%' }}>
        {/* CSS Animations */}
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          @keyframes slideUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .network-card:hover {
            background: ${t.hoverBg} !important;
          }
          .table-row:hover {
            background: ${t.hoverBg} !important;
            transform: scale(1.001);
          }
          .table-row {
            transition: all 0.15s ease !important;
          }
          .action-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(8, 145, 178, 0.15) !important;
          }
          .stat-card {
            transition: all 0.2s ease;
          }
          .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
          }
          .discovery-header-card {
            transition: all 0.2s ease;
          }
          .discovery-header-card:hover {
            box-shadow: 0 4px 20px rgba(8, 145, 178, 0.12) !important;
          }
        `}</style>

        {error && (
          <div style={{
            background: t.dangerBg,
            color: t.danger,
            padding: '10px 16px',
            borderRadius: '8px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            fontWeight: 500,
            border: `1px solid ${t.dangerBorder}`
          }}>
            <span style={{ flex: 1 }}>{error}</span>
            <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', fontSize: '16px', cursor: 'pointer', color: t.danger, padding: '2px 6px' }}>x</button>
          </div>
        )}
        {message && (
          <div style={{
            background: t.successBg,
            color: t.success,
            padding: '10px 16px',
            borderRadius: '8px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            fontWeight: 500,
            border: `1px solid ${t.successBorder}`
          }}>
            <span style={{ flex: 1 }}>{message}</span>
            <button onClick={() => setMessage(null)} style={{ background: 'none', border: 'none', fontSize: '16px', cursor: 'pointer', color: t.success, padding: '2px 6px' }}>x</button>
          </div>
        )}

        {/* Form Pages Discovery Section - Collapsible */}
        <div 
          className="discovery-header-card"
          style={{
            marginBottom: '24px',
            background: t.cardBg,
            border: `1px solid ${t.border}`,
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            animation: 'slideUp 0.3s ease',
          }}
        >
          {/* Accent bar at top */}
          <div style={{
            height: '3px',
            background: isDiscovering
              ? `linear-gradient(90deg, ${t.success}, ${t.brand}, ${t.success})`
              : `linear-gradient(90deg, ${t.brand}, #06b6d4)`,
            backgroundSize: isDiscovering ? '200% 100%' : '100% 100%',
            animation: isDiscovering ? 'shimmer 2s linear infinite' : 'none',
          }} />
          {/* Clickable Header to expand/collapse */}
          <div 
            onClick={() => !isDiscovering && setIsDiscoveryExpanded(!isDiscoveryExpanded)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              padding: '16px 20px',
              paddingBottom: isDiscoveryExpanded ? '14px' : '16px',
              borderBottom: isDiscoveryExpanded ? `1px solid ${t.border}` : 'none',
              cursor: isDiscovering ? 'default' : 'pointer'
          }}
        >
          {/* Icon with gradient background */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '42px',
            height: '42px',
            background: `linear-gradient(135deg, #0891b2, #0ea5e9)`,
            borderRadius: '10px',
            color: '#fff',
            fontSize: '18px',
            fontWeight: 700,
            flexShrink: 0,
            boxShadow: '0 3px 10px rgba(8, 145, 178, 0.35)',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div style={{ flex: 1 }}>
            <h1 style={{
              margin: 0,
              fontSize: '17px',
              fontWeight: 700,
              color: t.text,
              letterSpacing: '-0.01em',
            }}>Form Pages Discovery</h1>
            <p style={{
              margin: '3px 0 0',
              fontSize: '13px',
              color: t.textSecondary
            }}>
              {isDiscoveryExpanded 
                ? 'Discover form pages using AI-powered crawling'
                : `Click to ${formPages.length > 0 ? 'start a new discovery' : 'begin discovering form pages'}`}
            </p>
          </div>
          {isDiscovering ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 600,
              color: t.success,
              background: t.successBg,
              border: `1px solid ${t.successBorder}`
            }}>
              <div style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: t.success,
                animation: 'pulse 1.5s infinite',
                boxShadow: `0 0 6px ${t.success}`,
              }} />
              <span>In Progress</span>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              background: isDiscoveryExpanded ? t.mutedBg : `linear-gradient(135deg, ${t.brand}, #06b6d4)`,
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 600,
              color: isDiscoveryExpanded ? t.textSecondary : '#fff',
              border: `1px solid ${isDiscoveryExpanded ? t.border : 'transparent'}`,
              boxShadow: isDiscoveryExpanded ? 'none' : '0 2px 8px rgba(8, 145, 178, 0.25)',
              transition: 'all 0.2s ease',
            }}>
              <span style={{ fontSize: '10px', transition: 'transform 0.2s ease', display: 'inline-block', transform: isDiscoveryExpanded ? 'rotate(0)' : 'rotate(180deg)' }}>{'\u25B2'}</span>
              {isDiscoveryExpanded ? 'Collapse' : 'Expand'}
            </div>
          )}
        </div>

        {/* Collapsible Content */}
        {(isDiscoveryExpanded || isDiscovering) && (
          networks.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '48px 40px',
              background: t.mutedBg,
              borderRadius: '10px',
              border: `1px dashed ${t.border}`,
            }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '11px',
                background: t.brandLight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 14px',
                color: t.brand,
              }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="2" y1="12" x2="22" y2="12"/>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                </svg>
              </div>
              <h3 style={{ margin: '0 0 6px', fontSize: '15px', color: t.text, fontWeight: 600 }}>No Test Sites Found</h3>
              <p style={{ margin: 0, color: t.textSecondary, fontSize: '13px', lineHeight: 1.5 }}>
                Open the <strong style={{ color: t.brand }}>Test Sites</strong> tab from the sidebar to add your first test site.
              </p>
            </div>
          ) : (
            <>
              {/* Rediscover Message */}
              {rediscoverMessage && (
                <div style={{
                  background: t.warningBg,
                  border: `1px solid ${t.warningBorder}`,
                  borderRadius: '8px',
                  padding: '10px 16px',
                  marginBottom: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, color: t.warning, fontWeight: 500, fontSize: '13px' }}>
                      {rediscoverMessage}
                    </p>
                  </div>
                  <button
                    onClick={() => setRediscoverMessage(null)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: t.warning,
                      cursor: 'pointer',
                      fontSize: '16px',
                      padding: '2px 6px',
                    }}
                  >
                    x
                  </button>
                </div>
              )}
              
              {/* Network Selection */}
              <div style={{ 
                marginBottom: '14px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div>
                    <h3 style={{ 
                      margin: 0,
                      fontSize: '14px',
                      fontWeight: 600,
                      color: t.text
                    }}>Select Test Sites</h3>
                    <p style={{ 
                      margin: '2px 0 0',
                      fontSize: '12px',
                      color: t.textSecondary
                    }}>Select QA environment test sites to discover form pages</p>
                  </div>
                  <button 
                    onClick={selectAllNetworks} 
                    style={{
                      background: t.mutedBg,
                      color: t.textSecondary,
                      border: `1px solid ${t.border}`,
                      padding: '5px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    disabled={isDiscovering}
                  >
                    {selectedNetworkIds.length === qaNetworks.length ? 'All Selected' : 'Select All'}
                  </button>
                </div>

                <div style={{ 
                  border: `1px solid ${t.border}`,
                  borderRadius: '8px',
                  overflow: 'hidden',
                  background: t.cardBg,
                }}>
                  {qaNetworks.map(network => {
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
                          gap: '10px',
                          padding: '8px 14px',
                          borderBottom: `1px solid ${t.borderLight}`,
                          background: isSelected ? t.brandLight : 'transparent',
                          cursor: isDiscovering ? 'not-allowed' : 'pointer',
                          opacity: isDiscovering ? 0.6 : 1,
                          transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{
                        width: '16px',
                        height: '16px',
                        borderRadius: '3px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: isSelected ? t.brand : 'transparent',
                        border: isSelected ? `1.5px solid ${t.brand}` : `1.5px solid ${t.textMuted}`,
                        transition: 'all 0.15s ease',
                        flexShrink: 0
                      }}>
                        {isSelected && <span style={{ color: '#fff', fontSize: '11px', fontWeight: 700 }}>{'✓'}</span>}
                      </div>
                      <span style={{ fontWeight: 500, fontSize: '13px', color: t.text, minWidth: '120px' }}>
                        {network.name}
                      </span>
                      <span style={{ fontSize: '12px', color: t.textMuted, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {network.url}
                      </span>
                      {network.login_username && (
                        <span style={{ fontSize: '12px', color: t.textMuted }}>
                          {network.login_username}
                        </span>
                      )}
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        background: t.successBg,
                        color: t.success,
                        border: `1px solid ${t.successBorder}`,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        {getNetworkTypeLabel(network.network_type)}
                      </span>
                      {queueItem && (
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 500,
                          background: queueItem.status === 'running' ? t.warningBg :
                                     queueItem.status === 'completed' ? t.successBg :
                                     queueItem.status === 'failed' ? t.dangerBg : t.mutedBg,
                          color: queueItem.status === 'running' ? t.warning :
                                queueItem.status === 'completed' ? t.success :
                                queueItem.status === 'failed' ? t.danger :
                                queueItem.status === 'cancelled' ? t.warning : t.textMuted,
                          border: `1px solid ${
                            queueItem.status === 'running' ? t.warningBorder :
                            queueItem.status === 'completed' ? t.successBorder :
                            queueItem.status === 'failed' ? t.dangerBorder : t.border
                          }`
                        }}
                        title={queueItem.status === 'failed' && queueItem.errorMessage ? queueItem.errorMessage : undefined}
                        >
                          {queueItem.status === 'running' ? 'Running' :
                           queueItem.status === 'completed' ? 'Done' :
                           queueItem.status === 'failed' ? 'Failed' :
                           queueItem.status === 'cancelled' ? 'Cancelled' : 'Pending'}
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
                  gap: '6px', 
                  marginTop: '8px',
                  fontSize: '12px'
                }}>
                  <span style={{
                    background: t.brand,
                    color: '#fff',
                    padding: '1px 6px',
                    borderRadius: '3px',
                    fontWeight: 600,
                    fontSize: '11px'
                  }}>{selectedNetworkIds.length}</span>
                  <span style={{ color: t.textMuted }}>
                    network{selectedNetworkIds.length > 1 ? 's' : ''} selected
                  </span>
                </div>
              )}
            </div>

            {/* Action - Centered */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
              {isDiscovering ? (
                <button
                  onClick={stopDiscovery}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: t.danger,
                    color: '#fff',
                    border: 'none',
                    padding: '8px 20px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer'
                  }}
                >
                  Stop Discovery
                </button>
              ) : (
                <button
                  onClick={startDiscovery}
                  disabled={selectedNetworkIds.length === 0}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: selectedNetworkIds.length === 0 ? t.textMuted : t.brand,
                    color: '#fff',
                    border: 'none',
                    padding: '8px 24px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: selectedNetworkIds.length === 0 ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                    opacity: selectedNetworkIds.length === 0 ? 0.5 : 1
                  }}
                >
                  Start Discovery
                </button>
              )}
            </div>
          </>
          )
        )}
      </div>

      {/* Discovery Status */}
      {discoveryQueue.length > 0 && (
        <div style={{
          background: t.cardBg,
          border: `1px solid ${t.border}`,
          borderRadius: '10px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          marginTop: '20px',
          position: 'relative'
        }}>
          {/* Close button - only show when not discovering */}
          {!isDiscovering && (
            <button
              onClick={() => setDiscoveryQueue([])}
              style={{
                position: 'absolute',
                top: '14px',
                right: '14px',
                background: t.mutedBg,
                border: `1px solid ${t.border}`,
                borderRadius: '6px',
                padding: '4px 10px',
                cursor: 'pointer',
                fontSize: '12px',
                color: t.textSecondary,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
              title="Close discovery progress"
            >
              x Close
            </button>
          )}
          <h2 style={{ marginTop: 0, fontSize: '15px', color: t.text, fontWeight: 600, marginBottom: '16px' }}>
            Discovery Progress
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
            <div style={{
              background: t.mutedBg,
              padding: '14px',
              borderRadius: '8px',
              border: `1px solid ${t.borderLight}`
            }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: t.textMuted, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Test Sites</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: t.text }}>{completedNetworks} / {totalNetworks}</div>
            </div>
            <div style={{
              background: t.mutedBg,
              padding: '14px',
              borderRadius: '8px',
              border: `1px solid ${t.borderLight}`
            }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: t.textMuted, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>New Forms Found</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: t.success }}>{stats.totalFormsFound}</div>
            </div>
            <div style={{
              background: t.mutedBg,
              padding: '14px',
              borderRadius: '8px',
              border: `1px solid ${t.borderLight}`
            }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: t.textMuted, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Current</div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: stats.runningCount > 0 ? t.warning : t.textMuted }}>
                {stats.runningCount > 0 
                  ? discoveryQueue.find(q => q.status === 'running')?.networkName || '-'
                  : 'None'}
              </div>
            </div>
            <div style={{
              background: t.mutedBg,
              padding: '14px',
              borderRadius: '8px',
              border: `1px solid ${t.borderLight}`
            }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: t.textMuted, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Status</div>
              <div style={{ 
                fontSize: '13px',
                fontWeight: 600,
                color: isDiscovering ? t.warning : 
                       stats.cancelledCount > 0 ? t.warning :
                       stats.failedCount > 0 ? t.danger : t.success
              }}>
                {isDiscovering ? 'IN PROGRESS' : 
                 stats.cancelledCount > 0 ? 'CANCELLED' :
                 stats.failedCount > 0 ? 'WITH ERRORS' : 'COMPLETED'}
              </div>
            </div>
          </div>

          {totalNetworks > 0 && (
            <div style={{ marginTop: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '11px', color: t.textMuted }}>
                <span>Overall Progress</span>
                <span style={{ fontWeight: 600 }}>{Math.round((completedNetworks / totalNetworks) * 100)}%</span>
              </div>
              <div style={{ background: t.borderLight, borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                <div style={{
                  background: t.brand,
                  height: '100%',
                  width: `${(completedNetworks / totalNetworks) * 100}%`,
                  transition: 'width 0.4s ease',
                  borderRadius: '4px'
                }} />
              </div>
            </div>
          )}

          {/* Network Queue Status */}
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: t.textMuted, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Test Site Queue</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {discoveryQueue.map((item, idx) => (
                <div 
                  key={item.networkId}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    background: item.status === 'running' ? t.warningBg : 
                               item.status === 'completed' ? t.successBg :
                               item.status === 'failed' ? t.dangerBg : t.mutedBg,
                    borderRadius: '6px',
                    border: `1px solid ${
                      item.status === 'running' ? t.warningBorder :
                      item.status === 'completed' ? t.successBorder :
                      item.status === 'failed' ? t.dangerBorder : t.borderLight
                    }`
                  }}
                >
                  <span style={{ 
                    width: '22px', 
                    height: '22px', 
                    borderRadius: '50%', 
                    background: item.status === 'running' ? t.warning :
                               item.status === 'completed' ? t.success :
                               item.status === 'failed' ? t.danger : t.textMuted,
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '11px',
                    fontWeight: 700,
                    flexShrink: 0
                  }}>
                    {idx + 1}
                  </span>
                  <span style={{ flex: 1, fontWeight: 500, fontSize: '13px', color: t.text }}>
                    {item.networkName}
                  </span>
                  <span style={{ 
                    fontSize: '12px',
                    fontWeight: 500,
                    color: item.status === 'running' ? t.warning :
                          item.status === 'completed' ? t.success :
                          item.status === 'failed' ? t.danger :
                          item.status === 'cancelled' ? t.warning : t.textMuted
                  }}
                  title={item.status === 'failed' && item.errorMessage ? item.errorMessage : undefined}
                  >
                    {item.status === 'running' ? 'Running...' :
                     item.status === 'completed' ? 'Completed' :
                     item.status === 'failed' ? 'Failed' :
                     item.status === 'cancelled' ? 'Cancelled' : 'Waiting'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {formPages.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '14px',
          marginTop: '20px',
          marginBottom: '20px',
          animation: 'slideUp 0.4s ease',
        }}>
          {[
            {
              label: 'Total Forms',
              value: formPages.length,
              icon: (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              ),
              color: '#0891b2',
              bg: '#cffafe',
            },
            {
              label: 'Mapped',
              value: formPages.filter(f => (f as any).paths_count > 0).length,
              icon: (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 11 12 14 22 4"/>
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                </svg>
              ),
              color: '#4a9a8e',
              bg: '#eef6f4',
            },
            {
              label: 'Unmapped',
              value: formPages.filter(f => !(f as any).paths_count || (f as any).paths_count === 0).length,
              icon: (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              ),
              color: '#d97706',
              bg: '#fef3c7',
            },
            {
              label: 'Test Sites',
              value: new Set(formPages.map(f => f.network_id)).size,
              icon: (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="2" y1="12" x2="22" y2="12"/>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                </svg>
              ),
              color: '#7c3aed',
              bg: '#ede9fe',
            },
          ].map((stat, idx) => (
            <div 
              key={idx}
              className="stat-card"
              style={{
                background: t.cardBg,
                border: `1px solid ${t.border}`,
                borderLeft: `3px solid ${stat.color}`,
                borderRadius: '10px',
                padding: '16px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.05)',
              }}
            >
              <div style={{
                width: '38px',
                height: '38px',
                borderRadius: '9px',
                background: stat.bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: stat.color,
                flexShrink: 0,
              }}>
                {stat.icon}
              </div>
              <div>
                <div style={{ fontSize: '22px', fontWeight: 700, color: t.text, lineHeight: 1.1 }}>{stat.value}</div>
                <div style={{ fontSize: '12px', color: t.textMuted, fontWeight: 500, marginTop: '2px' }}>{stat.label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Pages Table */}
      <div style={{
        marginTop: formPages.length > 0 ? '0' : '20px',
        animation: 'slideUp 0.5s ease',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '4px',
              height: '24px',
              background: `linear-gradient(180deg, ${t.brand}, #06b6d4)`,
              borderRadius: '2px',
            }} />
            <div>
              <h2 style={{ margin: 0, fontSize: '17px', color: t.text, fontWeight: 700, letterSpacing: '-0.01em' }}>
                Discovered Form Pages
              </h2>
              <p style={{ margin: '2px 0 0', fontSize: '13px', color: t.textSecondary }}>{formPages.length} forms found in this project</p>
            </div>
          </div>
          {formPages.length > 10 && (
            <span style={{ fontSize: '12px', color: t.textMuted, background: t.mutedBg, padding: '4px 10px', borderRadius: '4px', border: `1px solid ${t.border}` }}>
              Showing {formPages.length} forms
            </span>
          )}
        </div>
        
        {loadingFormPages ? (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            background: t.cardBg,
            borderRadius: '12px',
            border: `1px solid ${t.border}`,
          }}>
            <div style={{
              width: '32px',
              height: '32px',
              border: `3px solid ${t.border}`,
              borderTopColor: t.brand,
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 12px',
            }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <p style={{ color: t.textSecondary, fontSize: '14px', fontWeight: 500, margin: 0 }}>Loading form pages...</p>
          </div>
        ) : formPages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '60px 40px',
            background: t.cardBg,
            borderRadius: '12px',
            border: `1px solid ${t.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              background: t.brandLight,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              color: t.brand,
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </div>
            <p style={{ margin: 0, fontSize: '16px', color: t.text, fontWeight: 600 }}>No form pages discovered yet</p>
            <p style={{ margin: '8px 0 0', fontSize: '14px', color: t.textSecondary, maxWidth: '360px', marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.5 }}>
              Expand the discovery section above to crawl your test sites and find form pages automatically.
            </p>
            <button
              onClick={() => setIsDiscoveryExpanded(true)}
              style={{
                marginTop: '20px',
                padding: '10px 24px',
                background: `linear-gradient(135deg, ${t.brand}, #06b6d4)`,
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(8, 145, 178, 0.25)',
                transition: 'all 0.2s ease',
              }}
            >
              Start Discovery
            </button>
          </div>
        ) : (
          <div style={{
            maxHeight: '700px',
            overflowY: 'auto',
            background: t.cardBg,
            border: `1px solid ${t.border}`,
            borderRadius: '12px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.03)',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0' }}>
              <thead>
                <tr>
                  <th 
                    style={{
                      textAlign: 'left',
                      padding: '12px 16px',
                      borderBottom: `2px solid ${t.border}`,
                      fontWeight: 700,
                      color: '#475569',
                      background: '#eef2f7',
                      position: 'sticky',
                      top: 0,
                      zIndex: 1,
                      fontSize: '11px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.6px',
                      cursor: 'pointer',
                      userSelect: 'none',
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
                    {'Form Name'} {sortField === 'name' ? (sortDirection === 'asc' ? '\u2191' : '\u2193') : ''}
                  </th>
                  <th style={{
                    textAlign: 'left',
                    padding: '12px 16px',
                    borderBottom: `2px solid ${t.border}`,
                    fontWeight: 700,
                    color: '#475569',
                    background: '#eef2f7',
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px'
                  }}>Paths</th>
                  <th style={{
                    textAlign: 'left',
                    padding: '12px 16px',
                    borderBottom: `2px solid ${t.border}`,
                    fontWeight: 700,
                    color: '#475569',
                    background: '#eef2f7',
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px'
                  }}>Test Site URL</th>
                  <th 
                    style={{
                      textAlign: 'left',
                      padding: '12px 16px',
                      borderBottom: `2px solid ${t.border}`,
                      fontWeight: 700,
                      color: '#475569',
                      background: '#eef2f7',
                      position: 'sticky',
                      top: 0,
                      zIndex: 1,
                      fontSize: '11px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.6px',
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
                    {'Discovered'} {sortField === 'date' ? (sortDirection === 'asc' ? '\u2191' : '\u2193') : ''}
                  </th>
                  <th style={{
                    textAlign: 'center',
                    padding: '12px 16px',
                    borderBottom: `2px solid ${t.border}`,
                    fontWeight: 700,
                    color: '#475569',
                    background: '#eef2f7',
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px',
                    width: '120px'
                  }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {/* Group form pages by network_id, then show login/logout at end of each group */}
                {(() => {
                  // Get unique network IDs from form pages
                  const networkIdsFromForms = [...new Set(formPages.map(fp => fp.network_id))]
                  // Get network IDs from login/logout data
                  const networkIdsFromLoginLogout = Object.keys(loginLogoutData).map(id => parseInt(id))
                  // Combine and deduplicate
                  const allNetworkIds = [...new Set([...networkIdsFromForms, ...networkIdsFromLoginLogout])]
                  
                  // Sort form pages
                  const sortedFormPages = [...formPages].sort((a, b) => {
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
                  })
                  
                  let rowIndex = 0
                  
                  return allNetworkIds.map(networkId => {
                    const networkForms = sortedFormPages.filter(fp => fp.network_id === networkId)
                    const loginLogout = loginLogoutData[networkId]
                    
                    return (
                      <React.Fragment key={networkId}>
                        {/* Form pages for this network */}
                        {networkForms.map((form) => {
                          const currentIndex = rowIndex++
                          return (
                            <tr 
                              key={form.id} 
                              className="table-row"
                              style={{
                                transition: 'background 0.15s ease',
                                cursor: 'pointer',
                                background: currentIndex % 2 === 0 ? t.cardBg : '#f5f8fb'
                              }}
                              onDoubleClick={() => openEditPanel(form)}
                            >
                              <td style={{
                                padding: '12px 16px',
                                borderBottom: `1px solid ${t.borderLight}`,
                                verticalAlign: 'middle',
                                fontSize: '13px',
                                color: t.text
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <div style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '8px',
                                    background: `linear-gradient(135deg, #0891b2, #06b6d4)`,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                    color: '#ffffff',
                                    fontSize: '13px',
                                    fontWeight: 700,
                                    boxShadow: '0 2px 4px rgba(8, 145, 178, 0.3)',
                                  }}>
                                    {(form.form_name || 'F').charAt(0).toUpperCase()}
                                  </div>
                                  <div>
                                    <strong style={{ fontSize: '14px', fontWeight: 600, color: t.text }}>{form.form_name}</strong>
                                    {form.parent_form_name && (
                                      <div style={{ fontSize: '11px', color: t.textMuted, marginTop: '2px' }}>
                                        Parent: {form.parent_form_name}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                              <td style={{
                                padding: '12px 16px',
                                borderBottom: `1px solid ${t.borderLight}`,
                                verticalAlign: 'middle',
                              }}>
                                <span style={{
                                  background: (form as any).paths_count > 0 ? t.successBg : mappingFormIds.has(form.id) ? t.warningBg : t.mutedBg,
                                  color: (form as any).paths_count > 0 ? t.success : mappingFormIds.has(form.id) ? t.warning : t.textMuted,
                                  padding: '4px 10px',
                                  borderRadius: '20px',
                                  fontSize: '12px',
                                  fontWeight: 600,
                                  border: `1px solid ${(form as any).paths_count > 0 ? t.successBorder : mappingFormIds.has(form.id) ? t.warningBorder : t.border}`,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                }}>
                                  {mappingFormIds.has(form.id) && (
                                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: t.warning, animation: 'pulse 1.5s infinite' }} />
                                  )}
                                  {(form as any).paths_count > 0 && (
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                      <polyline points="20 6 9 17 4 12"/>
                                    </svg>
                                  )}
                                  {(form as any).paths_count > 0
                                      ? `${(form as any).paths_count} path${(form as any).paths_count > 1 ? 's' : ''}`
                                      : (mappingFormIds.has(form.id) ? 'Mapping...' : 'Not mapped')}
                                </span>
                              </td>
                              <td style={{ 
                                padding: '12px 16px', 
                                borderBottom: `1px solid ${t.borderLight}`, 
                                fontSize: '12px',
                                maxWidth: '200px'
                              }}>
                                <div 
                                  style={{ 
                                    overflow: 'hidden', 
                                    textOverflow: 'ellipsis', 
                                    whiteSpace: 'nowrap',
                                    color: t.brand,
                                    background: t.brandLight,
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    fontFamily: 'monospace',
                                    fontSize: '11px',
                                  }} 
                                  title={form.url}
                                >
                                  {form.url}
                                </div>
                              </td>
                              <td style={{ padding: '12px 16px', borderBottom: `1px solid ${t.borderLight}`, color: t.textMuted, fontSize: '12px' }}>
                                {form.created_at ? (
                                  <>
                                    {new Date(form.created_at).toLocaleDateString()}
                                    <div style={{ fontSize: '11px', color: t.textMuted }}>
                                      {new Date(form.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                  </>
                                ) : '-'}
                              </td>
                              <td style={{ padding: '12px 16px', borderBottom: `1px solid ${t.borderLight}`, textAlign: 'center' }}>
                                <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                  <button 
                                    onClick={() => openEditPanel(form)}
                                    className="action-btn"
                                    style={{
                                      background: `linear-gradient(135deg, ${t.brand}, #06b6d4)`,
                                      border: 'none',
                                      borderRadius: '6px',
                                      padding: '6px 14px',
                                      cursor: 'pointer',
                                      fontSize: '12px',
                                      color: '#ffffff',
                                      fontWeight: 600,
                                      transition: 'all 0.2s ease',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '4px',
                                      boxShadow: '0 2px 4px rgba(8, 145, 178, 0.25)',
                                    }}
                                    title="View form page"
                                  >
                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                      <circle cx="12" cy="12" r="3"/>
                                    </svg>
                                    View
                                  </button>
                                  <button 
                                    onClick={() => openDeleteModal(form)}
                                    className="action-btn"
                                    style={{
                                      background: 'transparent',
                                      border: `1px solid ${t.border}`,
                                      borderRadius: '6px',
                                      padding: '6px 10px',
                                      cursor: 'pointer',
                                      fontSize: '12px',
                                      color: t.textMuted,
                                      fontWeight: 500,
                                      transition: 'all 0.2s ease',
                                    }}
                                    title="Delete form page"
                                  >
                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <polyline points="3 6 5 6 21 6"/>
                                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                                    </svg>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                        
                        {/* Login/Logout rows at end of each network group */}
                        {loginLogout && (
                          <>
                            {/* Login Row */}
                            <tr 
                              key={`login-${networkId}`}
                              className="table-row"
                              style={{
                                transition: 'background 0.15s ease',
                                cursor: 'pointer',
                                background: t.successBg,
                                borderLeft: `3px solid ${t.success}`
                              }}
                              onDoubleClick={() => openLoginLogoutEditPanel(networkId, 'login')}
                            >
                              <td style={{
                                padding: '12px 16px',
                                borderBottom: `1px solid ${t.successBorder}`,
                                verticalAlign: 'middle',
                                fontSize: '13px',
                                color: t.text
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <div style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '8px',
                                    background: '#dff0ec',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                    color: '#5a9e92',
                                  }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                                      <polyline points="10 17 15 12 10 7"/>
                                      <line x1="15" y1="12" x2="3" y2="12"/>
                                    </svg>
                                  </div>
                                  <div>
                                    <strong style={{ fontSize: '14px', fontWeight: 600, color: '#4a9a8e' }}>Login</strong>
                                    <div style={{ fontSize: '11px', color: t.textMuted, marginTop: '2px' }}>
                                      {loginLogout.network_name}
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}` }}>
                                <span style={{
                                  background: t.mutedBg,
                                  color: t.textMuted,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  fontWeight: 500,
                                  border: `1px solid ${t.border}`
                                }}>
                                  {loginLogout.login_stages.length} steps
                                </span>
                              </td>
                              <td style={{ 
                                padding: '10px 16px', 
                                borderBottom: `1px solid ${t.successBorder}`, 
                                color: t.brand,
                                fontSize: '12px',
                                maxWidth: '200px'
                              }}>
                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={loginLogout.url}>
                                  {loginLogout.url}
                                </div>
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}`, color: t.textMuted, fontSize: '12px' }}>
                                {loginLogout.updated_at ? new Date(loginLogout.updated_at).toLocaleDateString() : '-'}
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}`, textAlign: 'center' }}>
                                <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                <button
                                  onClick={() => openLoginLogoutEditPanel(networkId, 'login')}
                                  className="action-btn"
                                  style={{
                                    background: t.successBg,
                                    border: `1px solid ${t.successBorder}`,
                                    borderRadius: '6px',
                                    padding: '6px 10px',
                                    cursor: 'pointer',
                                    fontSize: '12px',
                                    color: t.success,
                                    fontWeight: 500,
                                    transition: 'all 0.15s ease'
                                  }}
                                  title="View login steps"
                                >
                                  View
                                </button>
                                </div>
                              </td>
                            </tr>
                            
                            {/* Logout Row */}
                            <tr 
                              key={`logout-${networkId}`}
                              className="table-row"
                              style={{
                                transition: 'background 0.15s ease',
                                cursor: 'pointer',
                                background: t.successBg,
                                borderLeft: `3px solid ${t.success}`
                              }}
                              onDoubleClick={() => openLoginLogoutEditPanel(networkId, 'logout')}
                            >
                              <td style={{
                                padding: '12px 16px',
                                borderBottom: `1px solid ${t.successBorder}`,
                                verticalAlign: 'middle',
                                fontSize: '13px',
                                color: t.text
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <div style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '8px',
                                    background: '#dff0ec',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                    color: '#5a9e92',
                                  }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                                      <polyline points="16 17 21 12 16 7"/>
                                      <line x1="21" y1="12" x2="9" y2="12"/>
                                    </svg>
                                  </div>
                                  <div>
                                    <strong style={{ fontSize: '14px', fontWeight: 600, color: '#4a9a8e' }}>Logout</strong>
                                    <div style={{ fontSize: '11px', color: t.textMuted, marginTop: '2px' }}>
                                      {loginLogout.network_name}
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}` }}>
                                <span style={{
                                  background: t.mutedBg,
                                  color: t.textMuted,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  fontWeight: 500,
                                  border: `1px solid ${t.border}`
                                }}>
                                  {loginLogout.logout_stages.length} steps
                                </span>
                              </td>
                              <td style={{ 
                                padding: '10px 16px', 
                                borderBottom: `1px solid ${t.successBorder}`, 
                                color: t.brand,
                                fontSize: '12px',
                                maxWidth: '200px'
                              }}>
                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={loginLogout.url}>
                                  {loginLogout.url}
                                </div>
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}`, color: t.textMuted, fontSize: '12px' }}>
                                {loginLogout.updated_at ? new Date(loginLogout.updated_at).toLocaleDateString() : '-'}
                              </td>
                              <td style={{ padding: '10px 16px', borderBottom: `1px solid ${t.successBorder}`, textAlign: 'center' }}>
                                <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                                <button
                                  onClick={() => openLoginLogoutEditPanel(networkId, 'logout')}
                                  className="action-btn"
                                  style={{
                                    background: t.successBg,
                                    border: `1px solid ${t.successBorder}`,
                                    borderRadius: '6px',
                                    padding: '6px 10px',
                                    cursor: 'pointer',
                                    fontSize: '12px',
                                    color: t.success,
                                    fontWeight: 500,
                                    transition: 'all 0.15s ease'
                                  }}
                                  title="View logout steps"
                                >
                                  View
                                </button>
                                </div>
                              </td>
                            </tr>
                          </>
                        )}
                      </React.Fragment>
                    )
                  })
                })()}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Form Page Modal */}
      {showDeleteModal && formPageToDelete && (
        <div style={modalOverlayStyle}>
          <div style={{
            background: t.cardBg,
            borderRadius: '16px',
            width: '460px',
            padding: '28px',
            border: `1px solid ${t.dangerBorder}`,
            boxShadow: '0 8px 32px rgba(0,0,0,0.15), 0 2px 8px rgba(0,0,0,0.08)',
            animation: 'slideUp 0.2s ease',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                background: t.dangerBg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: t.danger,
                flexShrink: 0,
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  <line x1="10" y1="11" x2="10" y2="17"/>
                  <line x1="14" y1="11" x2="14" y2="17"/>
                </svg>
              </div>
              <h2 style={{ margin: 0, color: t.danger, fontSize: '18px', fontWeight: 700 }}>
                Delete Form Page?
              </h2>
            </div>
            
            <p style={{ fontSize: '14px', margin: '12px 0', color: t.text }}>
              Are you sure you want to delete <strong style={{ color: t.danger }}>{'"'}{formPageToDelete.form_name}{'"'}</strong>?
            </p>

            <div style={{
              background: t.dangerBg,
              border: `1px solid ${t.dangerBorder}`,
              padding: '14px',
              borderRadius: '8px',
              marginTop: '12px'
            }}>
              <strong style={{ fontSize: '13px', color: t.danger }}>Warning - This will permanently delete:</strong>
              <ul style={{ margin: '8px 0 0', fontSize: '13px', color: t.textSecondary, paddingLeft: '18px', lineHeight: '1.6' }}>
                <li>All discovered <strong style={{ color: t.danger }}>paths</strong> for this form</li>
                <li>All <strong style={{ color: t.danger }}>navigation steps</strong> leading to this form</li>
                <li>The form page entry itself</li>
              </ul>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
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

const secondaryButtonStyle: React.CSSProperties = {
  background: '#f8fafc',
  color: '#475569',
  padding: '9px 18px',
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
}

const dangerButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #dc2626, #ef4444)',
  color: 'white',
  padding: '9px 18px',
  border: 'none',
  borderRadius: '8px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  boxShadow: '0 2px 8px rgba(220, 38, 38, 0.25)',
}

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.4)',
  backdropFilter: 'blur(4px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '24px'
}
