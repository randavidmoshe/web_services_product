'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
  login_password: string | null
  created_by_user_id: number
  created_at: string
  updated_at: string
}

interface FormPage {
  id: number
  form_name: string
  url: string
  network_id: number
  navigation_steps: any[]
  is_root: boolean
  created_at: string
}

interface Project {
  id: number
  name: string
  description: string | null
  company_id: number
  product_id: number
  created_by_user_id: number
  created_at: string
  updated_at: string
  networks: {
    qa: Network[]
    staging: Network[]
    production: Network[]
  }
  form_pages: FormPage[]
}

export default function ProjectDetailPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params.id as string
  
  const [userId, setUserId] = useState<string | null>(null)
  
  // Project data
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Collapsed sections (staging and production collapsed by default)
  const [collapsedSections, setCollapsedSections] = useState({
    qa: false,
    staging: true,
    production: true
  })
  
  // Add Network Modal
  const [showAddNetworkModal, setShowAddNetworkModal] = useState(false)
  const [addNetworkType, setAddNetworkType] = useState<'qa' | 'staging' | 'production'>('qa')
  const [newNetworkName, setNewNetworkName] = useState('')
  const [newNetworkUrl, setNewNetworkUrl] = useState('')
  const [newNetworkUsername, setNewNetworkUsername] = useState('')
  const [newNetworkPassword, setNewNetworkPassword] = useState('')
  const [addingNetwork, setAddingNetwork] = useState(false)
  
  // Edit Network Modal
  const [showEditNetworkModal, setShowEditNetworkModal] = useState(false)
  const [editingNetwork, setEditingNetwork] = useState<Network | null>(null)
  const [editNetworkName, setEditNetworkName] = useState('')
  const [editNetworkUrl, setEditNetworkUrl] = useState('')
  const [editNetworkType, setEditNetworkType] = useState<'qa' | 'staging' | 'production'>('qa')
  const [editNetworkUsername, setEditNetworkUsername] = useState('')
  const [editNetworkPassword, setEditNetworkPassword] = useState('')
  const [savingNetwork, setSavingNetwork] = useState(false)
  
  // Delete Network Modal
  const [showDeleteNetworkModal, setShowDeleteNetworkModal] = useState(false)
  const [networkToDelete, setNetworkToDelete] = useState<Network | null>(null)
  const [deletingNetwork, setDeletingNetwork] = useState(false)

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id')
    
    fetch('/api/auth/me', { credentials: 'include' })
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
        loadProject(projectId)
      })
      .catch(() => {
        window.location.href = '/login'
      })
    
    if (projectId) {
      loadProject(projectId, storedToken)
    }
  }, [projectId])

  const loadProject = async (id: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${id}`,
        { credentials: 'include' }
      )
      
      if (response.ok) {
        const data = await response.json()
        setProject(data)
      } else if (response.status === 404) {
        setError('Project not found')
      } else {
        setError('Failed to load project')
      }
    } catch (err) {
      setError('Connection error. Is the server running?')
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (section: 'qa' | 'staging' | 'production') => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const openAddNetworkModal = (type: 'qa' | 'staging' | 'production') => {
    setAddNetworkType(type)
    setNewNetworkName('')
    setNewNetworkUrl('')
    setNewNetworkUsername('')
    setNewNetworkPassword('')
    setShowAddNetworkModal(true)
  }

  const handleAddNetwork = async () => {
    if (!newNetworkName.trim() || !newNetworkUrl.trim()) {
      setError('Network name and URL are required')
      return
    }
    
    setAddingNetwork(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks?user_id=${userId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            name: newNetworkName.trim(),
            url: newNetworkUrl.trim(),
            network_type: addNetworkType,
            login_username: newNetworkUsername.trim() || null,
            login_password: newNetworkPassword.trim() || null
          })
        }
      )
      
      if (response.ok) {
        setMessage('Network added successfully!')
        setShowAddNetworkModal(false)
        // Expand the section where network was added
        setCollapsedSections(prev => ({ ...prev, [addNetworkType]: false }))
        loadProject(projectId)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to add network')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setAddingNetwork(false)
    }
  }

  const openEditNetworkModal = (network: Network) => {
    setEditingNetwork(network)
    setEditNetworkName(network.name)
    setEditNetworkUrl(network.url)
    setEditNetworkType(network.network_type as 'qa' | 'staging' | 'production')
    setEditNetworkUsername(network.login_username || '')
    setEditNetworkPassword(network.login_password || '')
    setShowEditNetworkModal(true)
  }

  const handleSaveNetwork = async () => {
    if (!editingNetwork) return
    if (!editNetworkName.trim() || !editNetworkUrl.trim()) {
      setError('Network name and URL are required')
      return
    }
    
    setSavingNetwork(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks/${editingNetwork.id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            name: editNetworkName.trim(),
            url: editNetworkUrl.trim(),
            network_type: editNetworkType,
            login_username: editNetworkUsername.trim() || null,
            login_password: editNetworkPassword.trim() || null
          })
        }
      )
      
      if (response.ok) {
        setMessage('Network updated successfully!')
        setShowEditNetworkModal(false)
        setEditingNetwork(null)
        loadProject(projectId)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to update network')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setSavingNetwork(false)
    }
  }

  const openDeleteNetworkModal = (network: Network) => {
    setNetworkToDelete(network)
    setShowDeleteNetworkModal(true)
  }

  const handleDeleteNetwork = async () => {
    if (!networkToDelete) return
    
    setDeletingNetwork(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks/${networkToDelete.id}`,
        {
          method: 'DELETE',
          credentials: 'include'
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setMessage(`Network deleted. ${data.deleted.form_pages_deleted} form page(s) removed.`)
        setShowDeleteNetworkModal(false)
        setNetworkToDelete(null)
        loadProject(projectId)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete network')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingNetwork(false)
    }
  }

  const handleStartDiscovery = (networkId: number) => {
    router.push(`/dashboard/form-pages-discovery?project_id=${projectId}&network_id=${networkId}`)
  }

  if (loading) return <p>Loading...</p>

  return (
    <div style={{ padding: '40px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header with Project Name */}
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h1 style={{ margin: 0 }}>📁 {project?.name || 'Loading...'}</h1>
          {project?.description && (
            <span style={{ color: '#666', fontSize: '14px' }}>— {project.description}</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={() => router.push('/dashboard/projects')}
            style={secondaryButtonStyle}
          >
            ← Back to Projects
          </button>
        </div>
      </div>

      {/* Error/Message Display */}
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

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Loading project...</p>
        </div>
      )}

      {/* Project Content */}
      {!loading && project && (
        <>
          {/* Networks Section */}
          <div style={sectionStyle}>
            <h2 style={{ marginTop: 0 }}>🌐 Networks</h2>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
              {/* QA Networks */}
              <div style={networkColumnStyle}>
                <div 
                  style={columnHeaderStyle}
                  onClick={() => toggleSection('qa')}
                >
                  <span>{collapsedSections.qa ? '▶' : '▼'} QA Networks ({project.networks.qa.length})</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); openAddNetworkModal('qa') }}
                    style={addButtonSmallStyle}
                    title="Add QA Network"
                  >
                    +
                  </button>
                </div>
                {!collapsedSections.qa && (
                  <div style={networkListStyle}>
                    {project.networks.qa.length === 0 ? (
                      <p style={emptyTextStyle}>No QA networks yet</p>
                    ) : (
                      project.networks.qa.map(network => (
                        <NetworkCard
                          key={network.id}
                          network={network}
                          onEdit={() => openEditNetworkModal(network)}
                          onDelete={() => openDeleteNetworkModal(network)}
                          onStartDiscovery={() => handleStartDiscovery(network.id)}
                        />
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Staging Networks */}
              <div style={networkColumnStyle}>
                <div 
                  style={columnHeaderStyle}
                  onClick={() => toggleSection('staging')}
                >
                  <span>{collapsedSections.staging ? '▶' : '▼'} Staging Networks ({project.networks.staging.length})</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); openAddNetworkModal('staging') }}
                    style={addButtonSmallStyle}
                    title="Add Staging Network"
                  >
                    +
                  </button>
                </div>
                {!collapsedSections.staging && (
                  <div style={networkListStyle}>
                    {project.networks.staging.length === 0 ? (
                      <p style={emptyTextStyle}>No Staging networks yet</p>
                    ) : (
                      project.networks.staging.map(network => (
                        <NetworkCard
                          key={network.id}
                          network={network}
                          onEdit={() => openEditNetworkModal(network)}
                          onDelete={() => openDeleteNetworkModal(network)}
                          onStartDiscovery={() => handleStartDiscovery(network.id)}
                        />
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Production Networks */}
              <div style={networkColumnStyle}>
                <div 
                  style={columnHeaderStyle}
                  onClick={() => toggleSection('production')}
                >
                  <span>{collapsedSections.production ? '▶' : '▼'} Production Networks ({project.networks.production.length})</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); openAddNetworkModal('production') }}
                    style={addButtonSmallStyle}
                    title="Add Production Network"
                  >
                    +
                  </button>
                </div>
                {!collapsedSections.production && (
                  <div style={networkListStyle}>
                    {project.networks.production.length === 0 ? (
                      <p style={emptyTextStyle}>No Production networks yet</p>
                    ) : (
                      project.networks.production.map(network => (
                        <NetworkCard
                          key={network.id}
                          network={network}
                          onEdit={() => openEditNetworkModal(network)}
                          onDelete={() => openDeleteNetworkModal(network)}
                          onStartDiscovery={() => handleStartDiscovery(network.id)}
                        />
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Form Pages Section */}
          <div style={sectionStyle}>
            <h2 style={{ marginTop: 0 }}>📄 Discovered Form Pages ({project.form_pages.length})</h2>
            
            {project.form_pages.length === 0 ? (
              <div style={emptyStateStyle}>
                <p>No form pages discovered yet.</p>
                <p style={{ color: '#666', fontSize: '14px' }}>Add a network and start discovery to find form pages.</p>
              </div>
            ) : (
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Form Name</th>
                    <th style={thStyle}>URL</th>
                    <th style={thStyle}>Steps</th>
                    <th style={thStyle}>Type</th>
                    <th style={thStyle}>Discovered</th>
                  </tr>
                </thead>
                <tbody>
                  {project.form_pages.map(formPage => (
                    <tr key={formPage.id}>
                      <td style={tdStyle}>
                        <strong>{formPage.form_name}</strong>
                      </td>
                      <td style={tdStyle}>
                        <a href={formPage.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>
                          {formPage.url.length > 50 ? formPage.url.substring(0, 50) + '...' : formPage.url}
                        </a>
                      </td>
                      <td style={tdStyle}>{formPage.navigation_steps?.length || 0}</td>
                      <td style={tdStyle}>
                        <span style={{
                          background: formPage.is_root ? '#e3f2fd' : '#fff3e0',
                          color: formPage.is_root ? '#1565c0' : '#e65100',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '12px'
                        }}>
                          {formPage.is_root ? 'Root' : 'Child'}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        {formPage.created_at ? new Date(formPage.created_at).toLocaleString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* Add Network Modal */}
      {showAddNetworkModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0 }}>Add {addNetworkType.toUpperCase()} Network</h2>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Network Name *</label>
              <input
                type="text"
                value={newNetworkName}
                onChange={(e) => setNewNetworkName(e.target.value)}
                placeholder="e.g., My Test Server"
                style={inputStyle}
                autoFocus
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>URL *</label>
              <input
                type="text"
                value={newNetworkUrl}
                onChange={(e) => setNewNetworkUrl(e.target.value)}
                placeholder="e.g., https://myapp.example.com"
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Login Username (optional)</label>
              <input
                type="text"
                value={newNetworkUsername}
                onChange={(e) => setNewNetworkUsername(e.target.value)}
                placeholder="Test user username"
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Login Password (optional)</label>
              <input
                type="password"
                value={newNetworkPassword}
                onChange={(e) => setNewNetworkPassword(e.target.value)}
                placeholder="Test user password"
                style={inputStyle}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowAddNetworkModal(false)}
                style={secondaryButtonStyle}
                disabled={addingNetwork}
              >
                Cancel
              </button>
              <button
                onClick={handleAddNetwork}
                style={primaryButtonStyle}
                disabled={addingNetwork || !newNetworkName.trim() || !newNetworkUrl.trim()}
              >
                {addingNetwork ? 'Adding...' : 'Add Network'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Network Modal */}
      {showEditNetworkModal && editingNetwork && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0 }}>Edit Network</h2>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Network Name *</label>
              <input
                type="text"
                value={editNetworkName}
                onChange={(e) => setEditNetworkName(e.target.value)}
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>URL *</label>
              <input
                type="text"
                value={editNetworkUrl}
                onChange={(e) => setEditNetworkUrl(e.target.value)}
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Network Type *</label>
              <select
                value={editNetworkType}
                onChange={(e) => setEditNetworkType(e.target.value as 'qa' | 'staging' | 'production')}
                style={inputStyle}
              >
                <option value="qa">QA</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Login Username (optional)</label>
              <input
                type="text"
                value={editNetworkUsername}
                onChange={(e) => setEditNetworkUsername(e.target.value)}
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Login Password (optional)</label>
              <input
                type="password"
                value={editNetworkPassword}
                onChange={(e) => setEditNetworkPassword(e.target.value)}
                style={inputStyle}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowEditNetworkModal(false); setEditingNetwork(null) }}
                style={secondaryButtonStyle}
                disabled={savingNetwork}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNetwork}
                style={primaryButtonStyle}
                disabled={savingNetwork || !editNetworkName.trim() || !editNetworkUrl.trim()}
              >
                {savingNetwork ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Network Modal */}
      {showDeleteNetworkModal && networkToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0, color: '#c62828' }}>⚠️ Delete Network?</h2>
            
            <p>Are you sure you want to delete <strong>{networkToDelete.name}</strong>?</p>
            <p style={{ color: '#666', fontSize: '14px' }}>{networkToDelete.url}</p>
            
            <div style={warningBoxStyle}>
              <p style={{ margin: 0 }}>All form pages discovered through this network will also be deleted.</p>
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button
                onClick={() => { setShowDeleteNetworkModal(false); setNetworkToDelete(null) }}
                style={secondaryButtonStyle}
                disabled={deletingNetwork}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteNetwork}
                style={dangerButtonStyle}
                disabled={deletingNetwork}
              >
                {deletingNetwork ? 'Deleting...' : 'Delete Network'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Network Card Component
function NetworkCard({ 
  network, 
  onEdit, 
  onDelete, 
  onStartDiscovery 
}: { 
  network: Network
  onEdit: () => void
  onDelete: () => void
  onStartDiscovery: () => void
}) {
  return (
    <div style={networkCardStyle}>
      <div style={{ marginBottom: '8px' }}>
        <strong>{network.name}</strong>
      </div>
      <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', wordBreak: 'break-all' }}>
        {network.url}
      </div>
      {network.login_username && (
        <div style={{ fontSize: '12px', color: '#888', marginBottom: '8px' }}>
          👤 {network.login_username}
        </div>
      )}
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button onClick={onStartDiscovery} style={discoveryButtonStyle} title="Start Discovery">
          🔍
        </button>
        <button onClick={onEdit} style={iconButtonStyle} title="Edit">
          ✏️
        </button>
        <button onClick={onDelete} style={iconButtonStyle} title="Delete">
          🗑️
        </button>
      </div>
    </div>
  )
}

// Styles
const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '30px',
  paddingBottom: '20px',
  borderBottom: '1px solid #e0e0e0'
}

const sectionStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: '8px',
  padding: '24px',
  marginBottom: '24px'
}

const networkColumnStyle: React.CSSProperties = {
  background: '#f9f9f9',
  borderRadius: '8px',
  overflow: 'hidden'
}

const columnHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  background: '#e8e8e8',
  cursor: 'pointer',
  fontWeight: 600
}

const networkListStyle: React.CSSProperties = {
  padding: '16px'
}

const networkCardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #ddd',
  borderRadius: '6px',
  padding: '12px',
  marginBottom: '12px'
}

const addButtonSmallStyle: React.CSSProperties = {
  background: '#0070f3',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  width: '28px',
  height: '28px',
  fontSize: '18px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}

const iconButtonStyle: React.CSSProperties = {
  background: '#f5f5f5',
  border: '1px solid #ddd',
  borderRadius: '4px',
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: '14px'
}

const discoveryButtonStyle: React.CSSProperties = {
  background: '#e3f2fd',
  border: '1px solid #90caf9',
  borderRadius: '4px',
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: '14px'
}

const emptyTextStyle: React.CSSProperties = {
  color: '#888',
  fontSize: '14px',
  textAlign: 'center',
  padding: '20px 0'
}

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '40px 20px',
  color: '#666'
}

const primaryButtonStyle: React.CSSProperties = {
  background: '#0070f3',
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: '#f5f5f5',
  color: '#333',
  padding: '10px 20px',
  border: '1px solid #ddd',
  borderRadius: '6px',
  fontSize: '14px',
  cursor: 'pointer'
}

const dangerButtonStyle: React.CSSProperties = {
  background: '#c62828',
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '0 0 0 10px'
}

const errorBoxStyle: React.CSSProperties = {
  background: '#ffebee',
  color: '#c62828',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
}

const successBoxStyle: React.CSSProperties = {
  background: '#e8f5e9',
  color: '#2e7d32',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
}

const warningBoxStyle: React.CSSProperties = {
  background: '#fff3e0',
  color: '#e65100',
  padding: '16px',
  borderRadius: '6px',
  marginTop: '16px'
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
  zIndex: 1000
}

const modalContentStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '8px',
  padding: '24px',
  width: '100%',
  maxWidth: '500px',
  maxHeight: '90vh',
  overflow: 'auto'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '6px',
  fontWeight: 500,
  color: '#333'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  fontSize: '14px',
  boxSizing: 'border-box'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '12px',
  borderBottom: '2px solid #e0e0e0',
  fontWeight: 600,
  color: '#333'
}

const tdStyle: React.CSSProperties = {
  padding: '12px',
  borderBottom: '1px solid #f0f0f0'
}
