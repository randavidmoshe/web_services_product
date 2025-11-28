'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface Project {
  id: number
  name: string
  description: string | null
  network_count: number
  form_page_count: number
  created_by_user_id: number
}

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
  login_password: string | null
  created_at: string
}

interface NetworksByType {
  qa: Network[]
  staging: Network[]
  production: Network[]
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  
  // Active project
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  
  // Project dropdown
  const [showProjectDropdown, setShowProjectDropdown] = useState(false)
  
  // Projects modal (for managing projects)
  const [showProjectsModal, setShowProjectsModal] = useState(false)
  const [showAddProjectModal, setShowAddProjectModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [addingProject, setAddingProject] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  const [deletingProject, setDeletingProject] = useState(false)
  
  // Networks modal
  const [showNetworksModal, setShowNetworksModal] = useState(false)
  const [networks, setNetworks] = useState<NetworksByType>({ qa: [], staging: [], production: [] })
  const [loadingNetworks, setLoadingNetworks] = useState(false)
  const [collapsedSections, setCollapsedSections] = useState({ qa: false, staging: true, production: true })
  
  // Add/Edit Network
  const [showAddNetworkModal, setShowAddNetworkModal] = useState(false)
  const [addNetworkType, setAddNetworkType] = useState<'qa' | 'staging' | 'production'>('qa')
  const [networkName, setNetworkName] = useState('')
  const [networkUrl, setNetworkUrl] = useState('')
  const [networkUsername, setNetworkUsername] = useState('')
  const [networkPassword, setNetworkPassword] = useState('')
  const [savingNetwork, setSavingNetwork] = useState(false)
  const [editingNetwork, setEditingNetwork] = useState<Network | null>(null)
  
  // Delete Network
  const [showDeleteNetworkConfirm, setShowDeleteNetworkConfirm] = useState(false)
  const [networkToDelete, setNetworkToDelete] = useState<Network | null>(null)
  const [deletingNetwork, setDeletingNetwork] = useState(false)
  
  // Messages
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Active tab for left sidebar
  const [activeTab, setActiveTab] = useState<string>('form-discovery')

  // Load networks when Networks tab is selected
  useEffect(() => {
    if (activeTab === 'networks' && activeProject && token) {
      loadNetworksForTab()
    }
  }, [activeTab, activeProject])

  const loadNetworksForTab = async () => {
    if (!activeProject || !token) return
    setLoadingNetworks(true)
    try {
      const response = await fetch(
        `/api/projects/${activeProject.id}/networks`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (response.ok) {
        const data = await response.json()
        setNetworks(data)
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    const storedCompanyId = localStorage.getItem('company_id')
    const storedUserRole = localStorage.getItem('userType')
    
    if (!storedToken) {
      window.location.href = '/login'
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
    setCompanyId(storedCompanyId)
    setUserRole(storedUserRole)
    
    if (storedCompanyId) {
      loadProjects(storedCompanyId, storedToken)
    }
  }, [])

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('.project-dropdown')) {
        setShowProjectDropdown(false)
      }
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  const loadProjects = async (companyId: string, authToken: string) => {
    setLoadingProjects(true)
    try {
      const response = await fetch(
        `/api/projects/?company_id=${companyId}`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setProjects(data)
        
        // Load active project from localStorage or set first project
        const storedActiveProjectId = localStorage.getItem('active_project_id')
        if (storedActiveProjectId) {
          const activeProj = data.find((p: Project) => p.id === parseInt(storedActiveProjectId))
          if (activeProj) {
            setActiveProject(activeProj)
          } else if (data.length > 0) {
            setActiveProject(data[0])
            localStorage.setItem('active_project_id', data[0].id.toString())
            localStorage.setItem('active_project_name', data[0].name)
          }
        } else if (data.length > 0) {
          setActiveProject(data[0])
          localStorage.setItem('active_project_id', data[0].id.toString())
          localStorage.setItem('active_project_name', data[0].name)
        }
      }
    } catch (err) {
      console.error('Failed to load projects:', err)
    } finally {
      setLoadingProjects(false)
    }
  }

  const selectProject = (project: Project) => {
    setActiveProject(project)
    localStorage.setItem('active_project_id', project.id.toString())
    localStorage.setItem('active_project_name', project.name)
    setShowProjectDropdown(false)
    // Trigger page refresh to load new project data
    window.dispatchEvent(new CustomEvent('activeProjectChanged', { detail: project }))
  }

  const handleAddProject = async () => {
    if (!newProjectName.trim()) {
      setError('Project name is required')
      return
    }
    
    setAddingProject(true)
    setError(null)
    
    try {
      const response = await fetch(
        '/api/projects/',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: newProjectName.trim(),
            description: newProjectDescription.trim() || null,
            company_id: parseInt(companyId!),
            product_id: 1,
            user_id: parseInt(userId!)
          })
        }
      )
      
      if (response.ok) {
        const newProject = await response.json()
        setMessage('Project created successfully!')
        setShowAddProjectModal(false)
        setNewProjectName('')
        setNewProjectDescription('')
        loadProjects(companyId!, token!)
        // Auto-select the new project
        selectProject(newProject)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to create project')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setAddingProject(false)
    }
  }

  const handleDeleteProject = async () => {
    if (!projectToDelete) return
    
    setDeletingProject(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectToDelete.id}?user_id=${userId}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Project deleted successfully!')
        setShowDeleteConfirm(false)
        setProjectToDelete(null)
        
        // If deleted project was active, clear it
        if (activeProject?.id === projectToDelete.id) {
          setActiveProject(null)
          localStorage.removeItem('active_project_id')
          localStorage.removeItem('active_project_name')
        }
        
        loadProjects(companyId!, token!)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete project')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingProject(false)
    }
  }

  const openNetworksModal = async () => {
    if (!activeProject) {
      setError('Please select a project first')
      return
    }
    
    setShowNetworksModal(true)
    setLoadingNetworks(true)
    
    try {
      const response = await fetch(
        `/api/projects/${activeProject.id}/networks`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setNetworks(data)
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const toggleSection = (section: 'qa' | 'staging' | 'production') => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const openAddNetworkModal = (type: 'qa' | 'staging' | 'production') => {
    setAddNetworkType(type)
    setNetworkName('')
    setNetworkUrl('')
    setNetworkUsername('')
    setNetworkPassword('')
    setEditingNetwork(null)
    setShowAddNetworkModal(true)
  }

  const openEditNetworkModal = (network: Network) => {
    setEditingNetwork(network)
    setAddNetworkType(network.network_type as 'qa' | 'staging' | 'production')
    setNetworkName(network.name)
    setNetworkUrl(network.url)
    setNetworkUsername(network.login_username || '')
    setNetworkPassword(network.login_password || '')
    setShowAddNetworkModal(true)
  }

  const handleSaveNetwork = async () => {
    if (!networkName.trim() || !networkUrl.trim()) {
      setError('Network name and URL are required')
      return
    }
    
    setSavingNetwork(true)
    setError(null)
    
    try {
      const url = editingNetwork
        ? `/api/projects/${activeProject!.id}/networks/${editingNetwork.id}`
        : `/api/projects/${activeProject!.id}/networks?user_id=${userId}`
      
      const response = await fetch(url, {
        method: editingNetwork ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: networkName.trim(),
          url: networkUrl.trim(),
          network_type: addNetworkType,
          login_username: networkUsername.trim() || null,
          login_password: networkPassword.trim() || null
        })
      })
      
      if (response.ok) {
        setMessage(editingNetwork ? 'Network updated!' : 'Network added!')
        setShowAddNetworkModal(false)
        setCollapsedSections(prev => ({ ...prev, [addNetworkType]: false }))
        // Reload networks
        openNetworksModal()
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to save network')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setSavingNetwork(false)
    }
  }

  const handleDeleteNetwork = async () => {
    if (!networkToDelete) return
    
    setDeletingNetwork(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${activeProject!.id}/networks/${networkToDelete.id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Network deleted!')
        setShowDeleteNetworkConfirm(false)
        setNetworkToDelete(null)
        openNetworksModal()
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

  const handleLogout = () => {
    localStorage.clear()
    window.location.href = '/login'
  }

  // Clear messages after 3 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [message])

  if (!token) return <p>Loading...</p>

  return (
    <div style={{ minHeight: '100vh', background: '#ddd5c8' }}>
      {/* Top Bar */}
      <div style={topBarStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* QUATHERA Logo */}
          <div style={logoStyle}>
            <span style={{ fontSize: '28px', marginRight: '8px' }}>🔬</span>
            <span style={logoTextStyle}>QUATHERA</span>
          </div>
          
          <div style={dividerStyle} />
          
          {/* Project Selector */}
          <div className="project-dropdown" style={{ position: 'relative' }}>
            <button
              onClick={(e) => { e.stopPropagation(); setShowProjectDropdown(!showProjectDropdown) }}
              style={projectButtonStyle}
            >
              📁 {activeProject ? activeProject.name : 'Select Project'} ▼
            </button>
            
            {showProjectDropdown && (
              <div style={dropdownMenuStyle}>
                <div style={dropdownHeaderStyle}>Switch Project</div>
                {projects.length === 0 ? (
                  <div style={dropdownItemStyle}>No projects yet</div>
                ) : (
                  projects.map(project => (
                    <div
                      key={project.id}
                      onClick={() => selectProject(project)}
                      style={{
                        ...dropdownItemStyle,
                        background: activeProject?.id === project.id ? '#e3f2fd' : 'transparent'
                      }}
                    >
                      {project.name}
                      <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>
                        ({project.network_count} networks)
                      </span>
                    </div>
                  ))
                )}
                <div style={dropdownDividerStyle} />
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowAddProjectModal(true) }}
                  style={{ ...dropdownItemStyle, color: '#0070f3' }}
                >
                  + Add Project
                </div>
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowProjectsModal(true) }}
                  style={dropdownItemStyle}
                >
                  ⚙️ Manage Projects
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Download Agent */}
          <button
            onClick={() => window.open('/api/installer/download/linux', '_blank')}
            style={topBarButtonStyle}
          >
            🤖 Download Agent
          </button>
          
          {/* Logout */}
          <button onClick={handleLogout} style={logoutButtonStyle}>
            Logout
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div style={{ ...messageStyle, background: '#ffebee', color: '#c62828' }}>
          ❌ {error}
          <button onClick={() => setError(null)} style={closeButtonStyle}>×</button>
        </div>
      )}
      {message && (
        <div style={{ ...messageStyle, background: '#e8f5e9', color: '#2e7d32' }}>
          ✅ {message}
        </div>
      )}

      {/* Main Layout with Sidebar */}
      <div style={{ display: 'flex', minHeight: 'calc(100vh - 60px)' }}>
        {/* Left Sidebar - Light clean theme */}
        <div style={sidebarStyle}>
          <div style={sidebarHeaderStyle}>
            <span>MENU</span>
          </div>
          
          <div style={{ padding: '0 12px' }}>
            <div 
              onClick={() => setActiveTab('form-discovery')}
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'form-discovery' ? 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)' : 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
                border: activeTab === 'form-discovery' ? '1px solid #667eea' : '1px solid #b8c4d0',
                borderBottom: activeTab === 'form-discovery' ? '3px solid #667eea' : '3px solid #a8b4c0',
                boxShadow: activeTab === 'form-discovery' ? '0 4px 12px rgba(102,126,234,0.25), inset 0 1px 0 rgba(255,255,255,0.5)' : '0 2px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'form-discovery' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#c8d1dc'
              }}>
                <span style={{ filter: activeTab === 'form-discovery' ? 'brightness(10)' : 'none' }}>🔍</span>
              </div>
              <span style={{ color: activeTab === 'form-discovery' ? '#5a67d8' : '#3d4852', fontWeight: 600, fontSize: '17px' }}>Form Pages Discovery</span>
            </div>
            
            <div 
              onClick={() => setActiveTab('test-scenarios')}
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'test-scenarios' ? 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)' : 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
                border: activeTab === 'test-scenarios' ? '1px solid #667eea' : '1px solid #b8c4d0',
                borderBottom: activeTab === 'test-scenarios' ? '3px solid #667eea' : '3px solid #a8b4c0',
                boxShadow: activeTab === 'test-scenarios' ? '0 4px 12px rgba(102,126,234,0.25), inset 0 1px 0 rgba(255,255,255,0.5)' : '0 2px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'test-scenarios' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#c8d1dc'
              }}>
                <span style={{ filter: activeTab === 'test-scenarios' ? 'brightness(10)' : 'none' }}>📝</span>
              </div>
              <span style={{ color: activeTab === 'test-scenarios' ? '#5a67d8' : '#3d4852', fontWeight: 600, fontSize: '17px' }}>Test Scenarios</span>
            </div>
            
            <div 
              onClick={() => setActiveTab('run-tests')}
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'run-tests' ? 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)' : 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
                border: activeTab === 'run-tests' ? '1px solid #667eea' : '1px solid #b8c4d0',
                borderBottom: activeTab === 'run-tests' ? '3px solid #667eea' : '3px solid #a8b4c0',
                boxShadow: activeTab === 'run-tests' ? '0 4px 12px rgba(102,126,234,0.25), inset 0 1px 0 rgba(255,255,255,0.5)' : '0 2px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'run-tests' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#c8d1dc'
              }}>
                <span style={{ filter: activeTab === 'run-tests' ? 'brightness(10)' : 'none' }}>▶️</span>
              </div>
              <span style={{ color: activeTab === 'run-tests' ? '#5a67d8' : '#3d4852', fontWeight: 600, fontSize: '17px' }}>Run Tests</span>
            </div>
            
            <div 
              onClick={() => setActiveTab('form-mapping')}
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'form-mapping' ? 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)' : 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
                border: activeTab === 'form-mapping' ? '1px solid #667eea' : '1px solid #b8c4d0',
                borderBottom: activeTab === 'form-mapping' ? '3px solid #667eea' : '3px solid #a8b4c0',
                boxShadow: activeTab === 'form-mapping' ? '0 4px 12px rgba(102,126,234,0.25), inset 0 1px 0 rgba(255,255,255,0.5)' : '0 2px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'form-mapping' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#c8d1dc'
              }}>
                <span style={{ filter: activeTab === 'form-mapping' ? 'brightness(10)' : 'none' }}>🗺️</span>
              </div>
              <span style={{ color: activeTab === 'form-mapping' ? '#5a67d8' : '#3d4852', fontWeight: 600, fontSize: '17px' }}>Form Page Mapping</span>
            </div>
            
            <div style={{ height: '1px', background: '#b8c4d0', margin: '16px 8px' }} />
            
            <div 
              onClick={() => setActiveTab('networks')}
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'networks' ? 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)' : 'linear-gradient(180deg, #e8edf3 0%, #dce3eb 100%)',
                border: activeTab === 'networks' ? '1px solid #667eea' : '1px solid #b8c4d0',
                borderBottom: activeTab === 'networks' ? '3px solid #667eea' : '3px solid #a8b4c0',
                boxShadow: activeTab === 'networks' ? '0 4px 12px rgba(102,126,234,0.25), inset 0 1px 0 rgba(255,255,255,0.5)' : '0 2px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'networks' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#c8d1dc'
              }}>
                <span style={{ filter: activeTab === 'networks' ? 'brightness(10)' : 'none' }}>🌐</span>
              </div>
              <span style={{ color: activeTab === 'networks' ? '#5a67d8' : '#3d4852', fontWeight: 600, fontSize: '17px' }}>Networks</span>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ flex: 1, padding: '28px 40px', background: '#ddd5c8' }}>
          {activeTab === 'form-discovery' && children}
          
          {activeTab === 'test-scenarios' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>📝</div>
              <h2 style={{ margin: '0 0 12px', color: '#1a1a2e', fontSize: '28px', fontWeight: 600 }}>Test Scenarios</h2>
              <p style={{ color: '#666', margin: 0, fontSize: '16px' }}>Coming soon - Define and manage your test scenarios here.</p>
            </div>
          )}
          
          {activeTab === 'run-tests' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>▶️</div>
              <h2 style={{ margin: '0 0 12px', color: '#1a1a2e', fontSize: '28px', fontWeight: 600 }}>Run Tests</h2>
              <p style={{ color: '#666', margin: 0 }}>Coming soon - Execute your test scenarios and view results.</p>
            </div>
          )}
          
          {activeTab === 'form-mapping' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>🗺️</div>
              <h2 style={{ margin: '0 0 12px', color: '#1a1a2e', fontSize: '28px', fontWeight: 600 }}>Form Page Mapping</h2>
              <p style={{ color: '#666', margin: 0, fontSize: '16px' }}>Coming soon - Visualize relationships between form pages.</p>
            </div>
          )}
          
          {activeTab === 'networks' && (
            <div style={networksTabContentStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ margin: '0 0 4px', fontSize: '24px', color: '#333' }}>🌐 Networks</h2>
                  <p style={{ margin: 0, color: '#666', fontSize: '15px' }}>Manage your network environments for {activeProject?.name || 'this project'}</p>
                </div>
              </div>
              
              {loadingNetworks ? (
                <p style={{ color: '#666' }}>Loading networks...</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* QA Networks */}
                  <div style={networkSectionStyle}>
                    <div style={networkSectionHeaderStyle} onClick={() => toggleSection('qa')}>
                      <span style={{ fontWeight: 600 }}>🧪 QA Environment ({networks.qa.length})</span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('qa') }} style={addButtonSmallStyle}>+</button>
                        <span>{collapsedSections.qa ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.qa && (
                      <div style={{ padding: '16px' }}>
                        {networks.qa.length === 0 ? (
                          <p style={emptyTextStyle}>No QA networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                            {networks.qa.map(network => (
                              <NetworkCard 
                                key={network.id} 
                                network={network} 
                                onEdit={() => openEditNetworkModal(network)}
                                onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Staging Networks */}
                  <div style={networkSectionStyle}>
                    <div style={networkSectionHeaderStyle} onClick={() => toggleSection('staging')}>
                      <span style={{ fontWeight: 600 }}>🚀 Staging Environment ({networks.staging.length})</span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('staging') }} style={addButtonSmallStyle}>+</button>
                        <span>{collapsedSections.staging ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.staging && (
                      <div style={{ padding: '16px' }}>
                        {networks.staging.length === 0 ? (
                          <p style={emptyTextStyle}>No Staging networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                            {networks.staging.map(network => (
                              <NetworkCard 
                                key={network.id} 
                                network={network} 
                                onEdit={() => openEditNetworkModal(network)}
                                onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Production Networks */}
                  <div style={networkSectionStyle}>
                    <div style={networkSectionHeaderStyle} onClick={() => toggleSection('production')}>
                      <span style={{ fontWeight: 600 }}>🏭 Production Environment ({networks.production.length})</span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('production') }} style={addButtonSmallStyle}>+</button>
                        <span>{collapsedSections.production ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.production && (
                      <div style={{ padding: '16px' }}>
                        {networks.production.length === 0 ? (
                          <p style={emptyTextStyle}>No Production networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                            {networks.production.map(network => (
                              <NetworkCard 
                                key={network.id} 
                                network={network} 
                                onEdit={() => openEditNetworkModal(network)}
                                onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add Project Modal */}
      {showAddProjectModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0 }}>Create New Project</h2>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Project Name *</label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Enter project name"
                style={inputStyle}
                autoFocus
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Description (optional)</label>
              <textarea
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
                placeholder="Enter project description"
                style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowAddProjectModal(false); setNewProjectName(''); setNewProjectDescription('') }}
                style={secondaryButtonStyle}
              >
                Cancel
              </button>
              <button
                onClick={handleAddProject}
                style={primaryButtonStyle}
                disabled={addingProject || !newProjectName.trim()}
              >
                {addingProject ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Projects Modal */}
      {showProjectsModal && (
        <div style={modalOverlayStyle}>
          <div style={{ ...modalContentStyle, maxWidth: '600px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>Manage Projects</h2>
              <button onClick={() => setShowProjectsModal(false)} style={closeButtonStyle}>×</button>
            </div>
            
            {projects.length === 0 ? (
              <p style={{ color: '#666', textAlign: 'center', padding: '20px' }}>No projects yet</p>
            ) : (
              <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                {projects.map(project => (
                  <div key={project.id} style={projectListItemStyle}>
                    <div>
                      <strong>{project.name}</strong>
                      {project.description && <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#666' }}>{project.description}</p>}
                      <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
                        {project.network_count} networks · {project.form_page_count} form pages
                      </div>
                    </div>
                    <button
                      onClick={() => { setProjectToDelete(project); setShowDeleteConfirm(true) }}
                      style={deleteIconButtonStyle}
                      title="Delete project"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
              <button
                onClick={() => { setShowProjectsModal(false); setShowAddProjectModal(true) }}
                style={primaryButtonStyle}
              >
                + Add New Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Project Confirmation */}
      {showDeleteConfirm && projectToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0, color: '#c62828' }}>⚠️ Delete Project?</h2>
            <p>Are you sure you want to delete <strong>{projectToDelete.name}</strong>?</p>
            <div style={warningBoxStyle}>
              <strong>This will permanently delete:</strong>
              <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                <li>{projectToDelete.network_count} network(s)</li>
                <li>{projectToDelete.form_page_count} form page(s)</li>
              </ul>
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => { setShowDeleteConfirm(false); setProjectToDelete(null) }} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button onClick={handleDeleteProject} style={dangerButtonStyle} disabled={deletingProject}>
                {deletingProject ? 'Deleting...' : 'Delete Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Networks Modal */}
      {showNetworksModal && (
        <div style={modalOverlayStyle}>
          <div style={{ ...modalContentStyle, maxWidth: '900px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>🌐 Networks - {activeProject?.name}</h2>
              <button onClick={() => setShowNetworksModal(false)} style={closeButtonStyle}>×</button>
            </div>
            
            {loadingNetworks ? (
              <p style={{ textAlign: 'center', padding: '40px' }}>Loading networks...</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                {/* QA Networks */}
                <div style={networkColumnStyle}>
                  <div style={columnHeaderStyle} onClick={() => toggleSection('qa')}>
                    <span>{collapsedSections.qa ? '▶' : '▼'} QA ({networks.qa.length})</span>
                    <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('qa') }} style={addButtonSmallStyle}>+</button>
                  </div>
                  {!collapsedSections.qa && (
                    <div style={networkListStyle}>
                      {networks.qa.length === 0 ? (
                        <p style={emptyTextStyle}>No QA networks</p>
                      ) : (
                        networks.qa.map(network => (
                          <NetworkCard
                            key={network.id}
                            network={network}
                            onEdit={() => openEditNetworkModal(network)}
                            onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                          />
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Staging Networks */}
                <div style={networkColumnStyle}>
                  <div style={columnHeaderStyle} onClick={() => toggleSection('staging')}>
                    <span>{collapsedSections.staging ? '▶' : '▼'} Staging ({networks.staging.length})</span>
                    <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('staging') }} style={addButtonSmallStyle}>+</button>
                  </div>
                  {!collapsedSections.staging && (
                    <div style={networkListStyle}>
                      {networks.staging.length === 0 ? (
                        <p style={emptyTextStyle}>No Staging networks</p>
                      ) : (
                        networks.staging.map(network => (
                          <NetworkCard
                            key={network.id}
                            network={network}
                            onEdit={() => openEditNetworkModal(network)}
                            onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                          />
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Production Networks */}
                <div style={networkColumnStyle}>
                  <div style={columnHeaderStyle} onClick={() => toggleSection('production')}>
                    <span>{collapsedSections.production ? '▶' : '▼'} Production ({networks.production.length})</span>
                    <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('production') }} style={addButtonSmallStyle}>+</button>
                  </div>
                  {!collapsedSections.production && (
                    <div style={networkListStyle}>
                      {networks.production.length === 0 ? (
                        <p style={emptyTextStyle}>No Production networks</p>
                      ) : (
                        networks.production.map(network => (
                          <NetworkCard
                            key={network.id}
                            network={network}
                            onEdit={() => openEditNetworkModal(network)}
                            onDelete={() => { setNetworkToDelete(network); setShowDeleteNetworkConfirm(true) }}
                          />
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add/Edit Network Modal */}
      {showAddNetworkModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0 }}>{editingNetwork ? 'Edit' : 'Add'} {addNetworkType.toUpperCase()} Network</h2>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Network Name *</label>
              <input
                type="text"
                value={networkName}
                onChange={(e) => setNetworkName(e.target.value)}
                placeholder="e.g., My Test Server"
                style={inputStyle}
                autoFocus
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>URL *</label>
              <input
                type="text"
                value={networkUrl}
                onChange={(e) => setNetworkUrl(e.target.value)}
                placeholder="e.g., https://myapp.example.com"
                style={inputStyle}
              />
            </div>
            
            {editingNetwork && (
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Network Type *</label>
                <select
                  value={addNetworkType}
                  onChange={(e) => setAddNetworkType(e.target.value as 'qa' | 'staging' | 'production')}
                  style={inputStyle}
                >
                  <option value="qa">QA</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                </select>
              </div>
            )}
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Login Username (optional)</label>
              <input
                type="text"
                value={networkUsername}
                onChange={(e) => setNetworkUsername(e.target.value)}
                placeholder="Test user username"
                style={inputStyle}
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Login Password (optional)</label>
              <input
                type="password"
                value={networkPassword}
                onChange={(e) => setNetworkPassword(e.target.value)}
                placeholder="Test user password"
                style={inputStyle}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAddNetworkModal(false)} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button
                onClick={handleSaveNetwork}
                style={primaryButtonStyle}
                disabled={savingNetwork || !networkName.trim() || !networkUrl.trim()}
              >
                {savingNetwork ? 'Saving...' : editingNetwork ? 'Save Changes' : 'Add Network'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Network Confirmation */}
      {showDeleteNetworkConfirm && networkToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0, color: '#c62828' }}>⚠️ Delete Network?</h2>
            <p>Are you sure you want to delete <strong>{networkToDelete.name}</strong>?</p>
            <p style={{ fontSize: '14px', color: '#666' }}>{networkToDelete.url}</p>
            <div style={warningBoxStyle}>
              All form pages discovered through this network will also be deleted.
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => { setShowDeleteNetworkConfirm(false); setNetworkToDelete(null) }} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button onClick={handleDeleteNetwork} style={dangerButtonStyle} disabled={deletingNetwork}>
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
function NetworkCard({ network, onEdit, onDelete }: { network: Network; onEdit: () => void; onDelete: () => void }) {
  return (
    <div style={networkCardStyle}>
      <div style={{ marginBottom: '6px' }}><strong>{network.name}</strong></div>
      <div style={{ fontSize: '12px', color: '#666', wordBreak: 'break-all' }}>{network.url}</div>
      {network.login_username && (
        <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>👤 {network.login_username}</div>
      )}
      <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
        <button onClick={onEdit} style={iconButtonStyle}>✏️</button>
        <button onClick={onDelete} style={iconButtonStyle}>🗑️</button>
      </div>
    </div>
  )
}

// Styles
const topBarStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '14px 40px',
  background: '#c8d1dc',
  borderBottom: '1px solid #b8c2cf',
  position: 'sticky',
  top: 0,
  zIndex: 100
}

const logoStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center'
}

const logoTextStyle: React.CSSProperties = {
  fontSize: '26px',
  fontWeight: 700,
  color: '#1a1a2e',
  letterSpacing: '2px'
}

const logoDotStyle: React.CSSProperties = {
  fontSize: '26px',
  fontWeight: 700,
  color: '#667eea',
  letterSpacing: '2px'
}
const dividerStyle: React.CSSProperties = {
  width: '1px',
  height: '30px',
  background: '#e8eef3',
  margin: '0 10px'
}

const projectButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  border: 'none',
  borderRadius: '10px',
  padding: '14px 24px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  color: '#fff',
  boxShadow: '0 2px 8px rgba(102,126,234,0.3)'
}

const topBarButtonStyle: React.CSSProperties = {
  background: '#d8dde4',
  border: '1px solid #c5ced9',
  borderRadius: '10px',
  padding: '14px 24px',
  fontSize: '17px',
  fontWeight: 500,
  cursor: 'pointer',
  color: '#3d4852',
  transition: 'all 0.2s'
}

const logoutButtonStyle: React.CSSProperties = {
  background: '#fee2e2',
  color: '#dc2626',
  border: '1px solid #fecaca',
  borderRadius: '10px',
  padding: '14px 24px',
  fontSize: '17px',
  fontWeight: 500,
  cursor: 'pointer'
}

const dropdownMenuStyle: React.CSSProperties = {
  position: 'absolute',
  top: '100%',
  left: 0,
  marginTop: '4px',
  background: 'white',
  border: '1px solid #ddd',
  borderRadius: '8px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
  minWidth: '250px',
  zIndex: 1000
}

const dropdownHeaderStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: '12px',
  color: '#888',
  borderBottom: '1px solid #eee'
}

const dropdownItemStyle: React.CSSProperties = {
  padding: '12px 16px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  color: '#333'
}

const dropdownDividerStyle: React.CSSProperties = {
  height: '1px',
  background: '#eee',
  margin: '4px 0'
}

const messageStyle: React.CSSProperties = {
  padding: '12px 40px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  fontSize: '24px',
  cursor: 'pointer',
  padding: '0',
  lineHeight: 1,
  color: 'inherit'
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

const warningBoxStyle: React.CSSProperties = {
  background: '#fff3e0',
  color: '#e65100',
  padding: '16px',
  borderRadius: '6px',
  marginTop: '16px'
}

const projectListItemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px',
  borderBottom: '1px solid #eee'
}

const deleteIconButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid #ddd',
  borderRadius: '4px',
  padding: '8px 12px',
  cursor: 'pointer',
  fontSize: '16px'
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
  padding: '12px'
}

const networkCardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #ddd',
  borderRadius: '6px',
  padding: '12px',
  marginBottom: '8px'
}

const addButtonSmallStyle: React.CSSProperties = {
  background: '#0070f3',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  width: '28px',
  height: '28px',
  fontSize: '18px',
  cursor: 'pointer'
}

const iconButtonStyle: React.CSSProperties = {
  background: '#f5f5f5',
  border: '1px solid #ddd',
  borderRadius: '4px',
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: '14px'
}

const emptyTextStyle: React.CSSProperties = {
  color: '#888',
  fontSize: '14px',
  textAlign: 'center',
  padding: '16px 0'
}

const sidebarStyle: React.CSSProperties = {
  width: '260px',
  background: '#d4dbe4',
  flexShrink: 0,
  borderRight: '1px solid #c5ced9'
}

const sidebarHeaderStyle: React.CSSProperties = {
  padding: '24px 24px 16px',
  fontSize: '11px',
  fontWeight: 700,
  color: '#9ca3af',
  textTransform: 'uppercase',
  letterSpacing: '1.2px'
}

const sidebarItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  padding: '14px 18px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 500,
  transition: 'all 0.2s ease',
  borderRadius: '12px',
  margin: '4px 12px',
  border: '1px solid transparent'
}

const sidebarIconStyle: React.CSSProperties = {
  width: '40px',
  height: '40px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: '12px',
  fontSize: '18px'
}

const placeholderCardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: '20px',
  padding: '80px 60px',
  textAlign: 'center',
  boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
  border: '1px solid rgba(0,0,0,0.04)'
}

const placeholderIconStyle: React.CSSProperties = {
  width: '80px',
  height: '80px',
  background: 'linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%)',
  borderRadius: '20px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '36px',
  margin: '0 auto 24px'
}

const networksTabContentStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: '20px',
  padding: '32px',
  boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
  border: '1px solid rgba(0,0,0,0.04)'
}

const networkSectionStyle: React.CSSProperties = {
  background: '#f9f9f9',
  borderRadius: '12px',
  overflow: 'hidden',
  border: '1px solid #e8e8e8'
}

const networkSectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px 20px',
  background: 'linear-gradient(90deg, #f5f5f5 0%, #fafafa 100%)',
  cursor: 'pointer'
}
