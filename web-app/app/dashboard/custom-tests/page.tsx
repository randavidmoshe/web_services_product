'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import CustomTestEditPanel from './CustomTestEditPanel'

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

export default function CustomTestsPage() {
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

  // Mapping state
  const [mappingTestPageIds, setMappingTestPageIds] = useState<Set<number>>(new Set())
  const mappingPollingRef = useRef<Record<number, NodeJS.Timeout>>({})

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
    
    if (storedProjectId) {
      loadNetworks(storedProjectId, storedToken)
      loadTestPages(storedProjectId, storedToken)
    }
  }, [])

  // Listen for project changes
  useEffect(() => {
    const handleStorageChange = () => {
      const newProjectId = localStorage.getItem('active_project_id')
      if (newProjectId !== activeProjectId) {
        setActiveProjectId(newProjectId)
        if (newProjectId && token) {
          loadNetworks(newProjectId, token)
          loadTestPages(newProjectId, token)
        }
      }
    }
    
    window.addEventListener('storage', handleStorageChange)
    const interval = setInterval(handleStorageChange, 1000)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  }, [activeProjectId, token])

  const loadNetworks = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        const allNetworks = [...(data.qa || []), ...(data.staging || []), ...(data.production || [])]
        setNetworks(allNetworks)
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    }
  }

  const loadTestPages = async (projectId: string, authToken: string) => {
    setLoading(true)
    try {
      const response = await fetch(
        `/api/test-pages?project_id=${projectId}`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setTestPages(data.test_pages || [])

        // Check for active mapping sessions and restore UI state
        checkActiveMappingSessions(authToken)

      }
    } catch (err) {
      setError('Failed to load custom tests')
    } finally {
      setLoading(false)
    }
  }

  // Check for active mapping sessions and restore UI state
  const checkActiveMappingSessions = async (authToken: string) => {
    try {
      const response = await fetch('/api/form-mapper/active-sessions', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      if (response.ok) {
        const activeSessions = await response.json()

        const newMappingIds = new Set<number>()
        const newMappingStatus: Record<number, { status: string; sessionId?: number }> = {}

        for (const session of activeSessions) {
          // Only process test page sessions (not form page sessions)
          if (!session.test_page_route_id) continue

          const activeStatuses = ['running', 'initializing', 'pending', 'logging_in', 'navigating', 'extracting_initial_dom', 'getting_initial_screenshot', 'ai_analyzing', 'executing_step', 'waiting_for_dom', 'waiting_for_screenshot']
          if (activeStatuses.includes(session.status)) {
            newMappingIds.add(session.test_page_route_id)
            newMappingStatus[session.test_page_route_id] = {
              status: 'mapping',
              sessionId: session.session_id
            }
            // Resume polling for this session
            startMappingPolling(session.test_page_route_id, session.session_id)
          }
        }

        if (newMappingIds.size > 0) {
          setMappingTestPageIds(newMappingIds)
          setMappingStatus(prev => ({ ...prev, ...newMappingStatus }))
        }
      }
    } catch (err) {
      console.error('Failed to check active mapping sessions:', err)
    }
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
        setMessage(editingTestPage ? 'Custom test updated' : 'Custom test created')
        setShowAddModal(false)
        loadTestPages(activeProjectId!, token!)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to save')
      }
    } catch (err) {
      setError('Failed to save custom test')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!testPageToDelete) return
    
    setDeleting(true)
    try {
      const response = await fetch(
        `/api/test-pages/${testPageToDelete.id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Custom test deleted')
        setShowDeleteConfirm(false)
        setTestPageToDelete(null)
        loadTestPages(activeProjectId!, token!)
      } else {
        setError('Failed to delete')
      }
    } catch (err) {
      setError('Failed to delete custom test')
    } finally {
      setDeleting(false)
    }
  }

  const openDetailPanel = async (testPage: TestPage) => {
    setSelectedTestPage(testPage)
    setEditTestName(testPage.test_name)
    setEditUrl(testPage.url)
    setEditTestCaseDescription(testPage.test_case_description)
    setShowDetailPanel(true)
    
    // Load paths
    setLoadingPaths(true)
    try {
      const response = await fetch(
        `/api/test-pages/${testPage.id}/paths`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
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
      const response = await fetch(
        `/api/test-pages/${selectedTestPage.id}`,
        {
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
        }
      )
      
      if (response.ok) {
        setMessage('Custom test updated')
        loadTestPages(activeProjectId!, token!)
        setSelectedTestPage({
          ...selectedTestPage,
          test_name: editTestName,
          url: editUrl,
          test_case_description: editTestCaseDescription
        })
      } else {
        setError('Failed to update')
      }
    } catch (err) {
      setError('Failed to update custom test')
    } finally {
      setSaving(false)
    }
  }

  const startMapping = async (testPage: TestPage) => {
    if (!userId) return

    // Warn if paths exist - they will be deleted on remap
    if (paths.length > 0) {
      const confirmed = confirm(`⚠️ This test already has mapping results. Re-mapping will DELETE the existing mapping. Continue?`)
      if (!confirmed) return
    }
    
    setMappingTestPageIds(prev => {
      const next = new Set(prev)
      next.add(testPage.id)
      return next
    })
    
    setMappingStatus(prev => ({
      ...prev,
      [testPage.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetch(
        `/api/test-pages/${testPage.id}/start-mapping`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ user_id: parseInt(userId!) })
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setMappingStatus(prev => ({
          ...prev,
          [testPage.id]: { status: 'mapping', sessionId: data.session_id }
        }))
        
        startMappingPolling(testPage.id, data.session_id)
      } else {
        const errData = await response.json()
        const errorMsg = typeof errData.detail === 'string'
          ? errData.detail
          : (errData.detail?.[0]?.msg || 'Failed to start mapping')
        setError(errorMsg)
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

  const handleCancelMapping = async (testPageId: number) => {
    const status = mappingStatus[testPageId]
    if (!status?.sessionId) return
    
    try {
      await fetch(
        `/api/form-mapper/sessions/${status.sessionId}/cancel`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (mappingPollingRef.current[testPageId]) {
        clearInterval(mappingPollingRef.current[testPageId])
        delete mappingPollingRef.current[testPageId]
      }
      
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
      
      setMessage('Mapping cancelled')
    } catch (err) {
      setError('Failed to cancel mapping')
    }
  }

  const handleDeletePath = async (pathId: number) => {
    try {
      const response = await fetch(
        `/api/form-mapper/paths/${pathId}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setPaths(prev => prev.filter(p => p.id !== pathId))
        setMessage('Path deleted')
        loadTestPages(activeProjectId!, token!)
      } else {
        setError('Failed to delete path')
      }
    } catch (err) {
      setError('Failed to delete path')
    }
  }

  const handleSavePathStep = async (pathId: number, stepIndex: number, stepData?: any) => {
    const path = paths.find(p => p.id === pathId)
    if (!path) return
    
    const dataToSave = stepData || editedPathStepData
    if (!dataToSave) return
    
    const updatedSteps = [...path.steps]
    updatedSteps[stepIndex] = dataToSave
    
    try {
      const response = await fetch(
        `/api/form-mapper/paths/${pathId}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ steps: updatedSteps })
        }
      )
      
      if (response.ok) {
        setPaths(prev => prev.map(p => 
          p.id === pathId ? { ...p, steps: updatedSteps } : p
        ))
        setEditingPathStep(null)
        setEditedPathStepData(null)
        setMessage('Step updated')
      } else {
        setError('Failed to update step')
      }
    } catch (err) {
      setError('Failed to update step')
    }
  }

  const handleExportPath = (path: CompletedPath) => {
    const exportData = {
      test_name: selectedTestPage?.test_name,
      path_number: path.path_number,
      steps: path.steps,
      exported_at: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedTestPage?.test_name || 'test'}_path_${path.path_number}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleRefreshPaths = async () => {
    if (!selectedTestPage) return
    
    setLoadingPaths(true)
    try {
      const response = await fetch(
        `/api/test-pages/${selectedTestPage.id}/paths`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setPaths(data.paths || [])
      }
    } catch (err) {
      console.error('Failed to refresh paths:', err)
    } finally {
      setLoadingPaths(false)
    }
  }

  const handleDeleteTestPageFromPanel = async (testPageId: number) => {
    try {
      const response = await fetch(
        `/api/test-pages/${testPageId}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Custom test deleted')
        setShowDetailPanel(false)
        setSelectedTestPage(null)
        loadTestPages(activeProjectId!, token!)
      } else {
        setError('Failed to delete')
      }
    } catch (err) {
      setError('Failed to delete custom test')
    }
  }

  const startMappingPolling = (testPageId: number, sessionId: number) => {
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

            setMappingStatus(prev => {
              const next = { ...prev }
              delete next[testPageId]
              return next
            })
            
            loadTestPages(activeProjectId!, token!)
            
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
        <CustomTestEditPanel
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
          {/* Custom Tests Header */}
          <div style={{
            background: theme.colors.cardBg,
            border: `1px solid ${theme.colors.cardBorder}`,
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{
                  fontSize: '28px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '44px',
                  height: '44px',
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  borderRadius: '10px',
                  boxShadow: '0 2px 6px rgba(139, 92, 246, 0.3)'
                }}>
                  <span style={{ fontSize: '22px' }}>🧪</span>
                </div>
                <div>
                  <h1 style={{
                    margin: 0,
                    fontSize: '24px',
                    fontWeight: 700,
                    color: theme.colors.textPrimary
                  }}>Custom Tests</h1>
                  <p style={{
                    margin: '6px 0 0',
                    fontSize: '15px',
                    color: theme.colors.textSecondary
                  }}>
                    Create and manage custom test cases for your application
                  </p>
                </div>
              </div>
              
              <button
                onClick={openAddModal}
                style={{
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '14px 24px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 15px rgba(139, 92, 246, 0.3)'
                }}
              >
                <span>+</span> Add Custom Test
              </button>
            </div>
          </div>

          {/* Custom Tests Table */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '24px', color: theme.colors.textPrimary, fontWeight: 600, letterSpacing: '-0.3px' }}>
                  <span style={{ marginRight: '10px' }}>📋</span>Your Custom Tests
                </h2>
                <p style={{ margin: '8px 0 0', fontSize: '16px', color: theme.colors.textSecondary }}>{testPages.length} custom tests in this project</p>
              </div>
            </div>

            {loading ? (
              <p style={{ color: theme.colors.textSecondary, marginTop: '24px', fontSize: '18px' }}>Loading custom tests...</p>
            ) : testPages.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '100px 60px',
                background: theme.colors.cardBg,
                borderRadius: '20px',
                border: `1px solid ${theme.colors.cardBorder}`
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>🧪</div>
                <p style={{ margin: 0, fontSize: '22px', color: theme.colors.textPrimary, fontWeight: 500 }}>No custom tests yet</p>
                <p style={{ margin: '14px 0 0', fontSize: '18px', color: theme.colors.textSecondary }}>Click "Add Custom Test" to create your first test</p>
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
                              title="View custom test"
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
                              title="Delete custom test"
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
        </>
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
                {editingTestPage ? '✏️ Edit Custom Test' : '➕ Add Custom Test'}
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
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Name *
                </label>
                <input
                  type="text"
                  value={formData.test_name}
                  onChange={(e) => setFormData({ ...formData, test_name: e.target.value })}
                  placeholder="e.g., Login Flow Test"
                  style={{
                    width: '100%',
                    padding: '14px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Site *
                </label>
                <select
                  value={formData.network_id}
                  onChange={(e) => setFormData({ ...formData, network_id: parseInt(e.target.value) })}
                  style={{
                    width: '100%',
                    padding: '14px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    boxSizing: 'border-box',
                    background: 'white'
                  }}
                >
                  <option value={0}>Select a test site...</option>
                  {networks.map(network => (
                    <option key={network.id} value={network.id}>
                      {network.name} ({network.url})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Starting URL *
                </label>
                <input
                  type="text"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="e.g., https://myapp.com/login"
                  style={{
                    width: '100%',
                    padding: '14px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
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
                  placeholder="Describe what this test should do. AI will generate steps based on this description.&#10;&#10;Example: Navigate to the login page, enter valid credentials, click login, and verify the dashboard loads successfully."
                  rows={5}
                  style={{
                    width: '100%',
                    padding: '14px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                    fontSize: '16px',
                    boxSizing: 'border-box',
                    resize: 'vertical'
                  }}
                />
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
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
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
              🗑️ Delete Custom Test?
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
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}
