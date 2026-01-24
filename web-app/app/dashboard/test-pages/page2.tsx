'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'

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

interface CompletedPath {
  id: number
  path_number: number
  steps_count: number
  steps: any[]
  created_at: string
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
    
    // Also check on focus (for same-tab changes)
    const checkProjectChange = () => {
      const currentProjectId = localStorage.getItem('active_project_id')
      if (currentProjectId !== activeProjectId && currentProjectId && token) {
        setActiveProjectId(currentProjectId)
        loadNetworks(currentProjectId, token)
        loadTestPages(currentProjectId, token)
      }
    }
    window.addEventListener('focus', checkProjectChange)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('focus', checkProjectChange)
    }
  }, [activeProjectId, token])

  const loadNetworks = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/networks`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
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

  // Enrich test pages with network names when networks load
  useEffect(() => {
    if (networks.length > 0 && testPages.length > 0) {
      setTestPages(prev => prev.map(tp => ({
        ...tp,
        network_name: networks.find(n => n.id === tp.network_id)?.name || 'Unknown'
      })))
    }
  }, [networks])

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
    setExpandedPathId(null)
    
    // Load paths for this test page
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

  const startMapping = async (testPage: TestPage) => {
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
        
        // Update local state
        setTestPages(prev => prev.map(tp => 
          tp.id === testPage.id ? { ...tp, status: 'mapping' as const } : tp
        ))
        
        // Start polling for status
        startPolling(testPage.id, data.session_id)
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

  const startPolling = (testPageId: number, sessionId: number) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/form-mapper/status/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const data = await response.json()
          const status = data.session?.status
          
          if (status === 'completed' || status === 'failed') {
            clearInterval(interval)
            delete mappingPollingRef.current[testPageId]
            
            setMappingTestPageIds(prev => {
              const next = new Set(prev)
              next.delete(testPageId)
              return next
            })
            
            loadTestPages(activeProjectId!, token!)
            
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
    if (message || error) {
      const timer = setTimeout(() => {
        setMessage(null)
        setError(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [message, error])

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
      
      {error && (
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

      {/* Detail Panel or Main View */}
      {showDetailPanel && selectedTestPage ? (
        // Detail Panel View
        <div>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ fontSize: '32px' }}>📋</span>
              <div>
                <h1 style={{ margin: 0, fontSize: '24px', color: theme.colors.textPrimary, fontWeight: 600 }}>
                  Test Page: <span style={{ color: theme.colors.accentPrimary }}>{selectedTestPage.test_name}</span>
                </h1>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              {(selectedTestPage.status === 'not_mapped' || selectedTestPage.status === 'failed') && !mappingTestPageIds.has(selectedTestPage.id) && (
                <button
                  onClick={() => startMapping(selectedTestPage)}
                  style={{
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '12px 24px',
                    fontSize: '15px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  ▶️ Start Mapping
                </button>
              )}
              <button
                onClick={() => { setShowDetailPanel(false); setSelectedTestPage(null) }}
                style={{
                  background: 'rgba(0,0,0,0.05)',
                  color: theme.colors.textPrimary,
                  border: `1px solid ${theme.colors.cardBorder}`,
                  borderRadius: '10px',
                  padding: '12px 24px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Back
              </button>
            </div>
          </div>

          {/* Detail Content */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Left Column - Info */}
            <div>
              {/* URL Section */}
              <div style={{
                background: 'rgba(16, 185, 129, 0.08)',
                borderRadius: '12px',
                padding: '20px 24px',
                marginBottom: '16px'
              }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#10b981', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>URL</div>
                <a href={selectedTestPage.url} target="_blank" rel="noopener noreferrer" style={{ color: theme.colors.accentPrimary, textDecoration: 'none', fontSize: '15px' }}>
                  {selectedTestPage.url}
                </a>
              </div>
              
              {/* Network Section */}
              <div style={{
                background: 'rgba(14, 165, 233, 0.08)',
                borderRadius: '12px',
                padding: '20px 24px',
                marginBottom: '16px'
              }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#0ea5e9', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Site (Network)</div>
                <div style={{ fontSize: '15px', color: theme.colors.textPrimary }}>
                  {selectedTestPage.network_name || networks.find(n => n.id === selectedTestPage.network_id)?.name || 'Unknown'}
                </div>
              </div>

              {/* Test Case Description */}
              <div style={{
                background: theme.colors.cardBg,
                borderRadius: '12px',
                padding: '20px 24px',
                border: `1px solid ${theme.colors.cardBorder}`
              }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: theme.colors.textSecondary, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Case Description</div>
                <pre style={{ 
                  margin: 0, 
                  fontSize: '14px', 
                  color: theme.colors.textPrimary, 
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  lineHeight: 1.6
                }}>
                  {selectedTestPage.test_case_description}
                </pre>
              </div>
            </div>

            {/* Right Column - Completed Paths */}
            <div style={{
              background: theme.colors.cardBg,
              borderRadius: '16px',
              padding: '24px',
              border: `1px solid ${theme.colors.cardBorder}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <span style={{ fontSize: '24px' }}>📊</span>
                <h3 style={{ margin: 0, fontSize: '18px', color: theme.colors.textPrimary, fontWeight: 600 }}>
                  Completed Mapping Paths
                </h3>
                <span style={{
                  background: theme.colors.accentPrimary,
                  color: 'white',
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: 600
                }}>
                  {paths.length}
                </span>
              </div>

              {loadingPaths ? (
                <div style={{ textAlign: 'center', padding: '40px', color: theme.colors.textSecondary }}>
                  Loading paths...
                </div>
              ) : paths.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                  <p style={{ margin: 0, color: theme.colors.textSecondary, fontSize: '16px' }}>No completed paths yet.</p>
                  <p style={{ margin: '8px 0 0', color: theme.colors.textSecondary, fontSize: '14px' }}>Click "Start Mapping" to discover paths through this test.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {paths.map(path => (
                    <div key={path.id}>
                      <div
                        onClick={() => setExpandedPathId(expandedPathId === path.id ? null : path.id)}
                        style={{
                          background: expandedPathId === path.id ? 'rgba(14, 165, 233, 0.1)' : 'rgba(0,0,0,0.03)',
                          border: `1px solid ${expandedPathId === path.id ? 'rgba(14, 165, 233, 0.3)' : theme.colors.cardBorder}`,
                          borderRadius: '12px',
                          padding: '16px 20px',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontWeight: 600, color: theme.colors.textPrimary, fontSize: '16px' }}>
                              Path #{path.path_number}
                            </div>
                            <div style={{ fontSize: '13px', color: theme.colors.textSecondary, marginTop: '4px' }}>
                              {path.steps_count} steps • {new Date(path.created_at).toLocaleDateString()}
                            </div>
                          </div>
                          <span style={{ fontSize: '18px', color: theme.colors.textSecondary }}>
                            {expandedPathId === path.id ? '▼' : '▶'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Expanded Steps */}
                      {expandedPathId === path.id && path.steps && (
                        <div style={{
                          marginTop: '8px',
                          marginLeft: '20px',
                          padding: '16px',
                          background: 'rgba(0,0,0,0.02)',
                          borderRadius: '8px',
                          border: `1px solid ${theme.colors.cardBorder}`
                        }}>
                          {path.steps.map((step: any, idx: number) => (
                            <div key={idx} style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '12px',
                              padding: '10px 0',
                              borderBottom: idx < path.steps.length - 1 ? `1px solid ${theme.colors.cardBorder}` : 'none'
                            }}>
                              <span style={{
                                background: theme.colors.accentPrimary,
                                color: 'white',
                                width: '24px',
                                height: '24px',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '12px',
                                fontWeight: 600,
                                flexShrink: 0
                              }}>
                                {idx + 1}
                              </span>
                              <div>
                                <div style={{ fontWeight: 500, color: theme.colors.textPrimary, fontSize: '14px' }}>
                                  {step.description || step.action}
                                </div>
                                <div style={{ fontSize: '12px', color: theme.colors.textSecondary, marginTop: '2px' }}>
                                  {step.action}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        // Main List View
        <>
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
                  Select the test site with login credentials. Create one in "Test Sites" if needed.
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
      `}</style>
    </div>
  )
}
