'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface Network {
  id: number
  name: string
  url: string
  network_type: string
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
  
  // Paths modal
  const [showPathsModal, setShowPathsModal] = useState(false)
  const [selectedTestPage, setSelectedTestPage] = useState<TestPage | null>(null)
  const [paths, setPaths] = useState<CompletedPath[]>([])
  const [loadingPaths, setLoadingPaths] = useState(false)

  // Mapping state
  const [mappingTestPageId, setMappingTestPageId] = useState<number | null>(null)
  const [mappingSessionId, setMappingSessionId] = useState<number | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // Theme (matching layout.tsx)
  const theme = {
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
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [activeProjectId, token])

  const loadNetworks = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/networks`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (response.ok) {
        const data = await response.json()
        // Flatten networks from all types
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
        // Enrich with network names
        const enriched = data.test_pages.map((tp: TestPage) => ({
          ...tp,
          network_name: networks.find(n => n.id === tp.network_id)?.name || 'Unknown'
        }))
        setTestPages(enriched)
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

  // Re-enrich when networks load
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
      } else {
        setError('Failed to delete')
      }
    } catch (err) {
      setError('Failed to delete')
    } finally {
      setDeleting(false)
    }
  }

  const startMapping = async (testPage: TestPage) => {
    setMappingTestPageId(testPage.id)
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
        setMappingSessionId(data.session_id)
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
        setMappingTestPageId(null)
      }
    } catch (err) {
      setError('Failed to start mapping')
      setMappingTestPageId(null)
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
            setMappingTestPageId(null)
            setMappingSessionId(null)
            
            // Reload to get updated status
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
    
    setPollingInterval(interval)
  }

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  const viewPaths = async (testPage: TestPage) => {
    setSelectedTestPage(testPage)
    setShowPathsModal(true)
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

  const getStatusBadge = (status: string) => {
    const styles: Record<string, { bg: string, text: string, label: string }> = {
      'not_mapped': { bg: 'rgba(107, 114, 128, 0.15)', text: '#6b7280', label: 'Not mapped' },
      'mapping': { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', label: 'Mapping...' },
      'mapped': { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', label: 'Mapped' },
      'failed': { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', label: 'Failed' }
    }
    const s = styles[status] || styles['not_mapped']
    
    return (
      <span style={{
        background: s.bg,
        color: s.text,
        padding: '6px 14px',
        borderRadius: '20px',
        fontSize: '13px',
        fontWeight: 600
      }}>
        {s.label}
      </span>
    )
  }

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
      <div style={{ padding: '40px', textAlign: 'center', color: theme.colors.textSecondary }}>
        <h2>No Project Selected</h2>
        <p>Please select a project from the dropdown above.</p>
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

      {/* Header */}
      <div style={{
        background: theme.colors.cardBg,
        borderRadius: '16px',
        padding: '28px 32px',
        marginBottom: '24px',
        border: `1px solid ${theme.colors.cardBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', color: theme.colors.textPrimary, fontWeight: 700 }}>
            🧪 Test Pages
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
      <div style={{
        background: theme.colors.cardBg,
        borderRadius: '16px',
        border: `1px solid ${theme.colors.cardBorder}`,
        overflow: 'hidden'
      }}>
        {/* Table Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 2fr 1fr 1.5fr',
          padding: '18px 28px',
          background: 'rgba(0, 0, 0, 0.03)',
          borderBottom: `1px solid ${theme.colors.cardBorder}`,
          fontSize: '13px',
          fontWeight: 700,
          color: theme.colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          <div>Test Name</div>
          <div>Status</div>
          <div>URL</div>
          <div>Network</div>
          <div>Actions</div>
        </div>

        {/* Table Body */}
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: theme.colors.textSecondary }}>
            Loading...
          </div>
        ) : testPages.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center', color: theme.colors.textSecondary }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🧪</div>
            <p style={{ fontSize: '18px', margin: 0 }}>No test pages yet</p>
            <p style={{ fontSize: '15px', margin: '8px 0 0' }}>Click "Add Test Page" to create your first test</p>
          </div>
        ) : (
          testPages.map(testPage => (
            <div
              key={testPage.id}
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 2fr 1fr 1.5fr',
                padding: '20px 28px',
                borderBottom: `1px solid ${theme.colors.cardBorder}`,
                alignItems: 'center',
                transition: 'background 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.02)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <div>
                <div style={{ fontWeight: 600, color: theme.colors.textPrimary, fontSize: '16px' }}>
                  {testPage.test_name}
                </div>
                <div style={{ 
                  fontSize: '13px', 
                  color: theme.colors.textSecondary, 
                  marginTop: '4px',
                  maxWidth: '300px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {testPage.test_case_description}
                </div>
              </div>
              
              <div>
                {getStatusBadge(testPage.status)}
              </div>
              
              <div>
                <a 
                  href={testPage.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ 
                    color: theme.colors.accentPrimary, 
                    textDecoration: 'none',
                    fontSize: '14px',
                    wordBreak: 'break-all'
                  }}
                >
                  {testPage.url}
                </a>
              </div>
              
              <div style={{ color: theme.colors.textSecondary, fontSize: '14px' }}>
                {testPage.network_name || 'None'}
              </div>
              
              <div style={{ display: 'flex', gap: '8px' }}>
                {testPage.status === 'not_mapped' || testPage.status === 'failed' ? (
                  <button
                    onClick={() => startMapping(testPage)}
                    disabled={mappingTestPageId !== null}
                    style={{
                      background: mappingTestPageId === testPage.id 
                        ? 'rgba(245, 158, 11, 0.2)' 
                        : 'linear-gradient(135deg, #10b981, #059669)',
                      color: mappingTestPageId === testPage.id ? '#f59e0b' : 'white',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '8px 16px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: mappingTestPageId !== null ? 'not-allowed' : 'pointer',
                      opacity: mappingTestPageId !== null && mappingTestPageId !== testPage.id ? 0.5 : 1
                    }}
                  >
                    {mappingTestPageId === testPage.id ? '⏳ Mapping...' : '▶️ Start'}
                  </button>
                ) : testPage.status === 'mapping' ? (
                  <span style={{ 
                    color: '#f59e0b', 
                    fontSize: '13px', 
                    fontWeight: 600,
                    padding: '8px 16px'
                  }}>
                    ⏳ Mapping...
                  </span>
                ) : (
                  <button
                    onClick={() => viewPaths(testPage)}
                    style={{
                      background: 'rgba(14, 165, 233, 0.1)',
                      color: '#0ea5e9',
                      border: '1px solid rgba(14, 165, 233, 0.3)',
                      borderRadius: '8px',
                      padding: '8px 16px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    📋 View Paths
                  </button>
                )}
                
                <button
                  onClick={() => openEditModal(testPage)}
                  style={{
                    background: 'rgba(0, 0, 0, 0.05)',
                    color: theme.colors.textSecondary,
                    border: `1px solid ${theme.colors.cardBorder}`,
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    cursor: 'pointer'
                  }}
                >
                  ✏️
                </button>
                
                <button
                  onClick={() => { setTestPageToDelete(testPage); setShowDeleteConfirm(true) }}
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    cursor: 'pointer'
                  }}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>

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
            {/* Modal Header */}
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
            
            {/* Modal Body */}
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
                  Network (for login)
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
                  <option value={0}>No network (no login required)</option>
                  {networks.map(network => (
                    <option key={network.id} value={network.id}>
                      {network.name} - {network.url}
                    </option>
                  ))}
                </select>
              </div>
              
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: theme.colors.textPrimary }}>
                  Test Case Description *
                </label>
                <textarea
                  value={formData.test_case_description}
                  onChange={(e) => setFormData({ ...formData, test_case_description: e.target.value })}
                  placeholder="Describe what the test should do in natural language, e.g.:
1. Search for 'laptop' in the search box
2. Click on the first search result
3. Verify the product page shows price and description
4. Add to cart and verify cart count increases"
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
            
            {/* Modal Footer */}
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

      {/* Paths Modal */}
      {showPathsModal && selectedTestPage && (
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
              position: 'sticky',
              top: 0,
              background: 'white'
            }}>
              <h2 style={{ margin: 0, fontSize: '20px', color: theme.colors.textPrimary }}>
                📋 Completed Paths - {selectedTestPage.test_name}
              </h2>
              <button
                onClick={() => { setShowPathsModal(false); setSelectedTestPage(null); setPaths([]) }}
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
            
            <div style={{ padding: '24px 28px' }}>
              {loadingPaths ? (
                <div style={{ textAlign: 'center', padding: '40px', color: theme.colors.textSecondary }}>
                  Loading paths...
                </div>
              ) : paths.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: theme.colors.textSecondary }}>
                  No paths found
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {paths.map(path => (
                    <div
                      key={path.id}
                      style={{
                        background: '#f9fafb',
                        border: '1px solid #e5e7eb',
                        borderRadius: '12px',
                        padding: '16px 20px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: theme.colors.textPrimary }}>
                          Path #{path.path_number}
                        </div>
                        <div style={{ fontSize: '13px', color: theme.colors.textSecondary, marginTop: '4px' }}>
                          {path.steps_count} steps • Created {new Date(path.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <span style={{
                        background: 'rgba(16, 185, 129, 0.1)',
                        color: '#10b981',
                        padding: '6px 12px',
                        borderRadius: '20px',
                        fontSize: '12px',
                        fontWeight: 600
                      }}>
                        ✓ Complete
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
