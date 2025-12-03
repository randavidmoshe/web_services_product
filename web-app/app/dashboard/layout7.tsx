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
  const [showPassword, setShowPassword] = useState(false)
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
  
  // Agent status
  const [agentStatus, setAgentStatus] = useState<'online' | 'offline' | 'unknown'>('unknown')
  const [agentLastSeen, setAgentLastSeen] = useState<string | null>(null)
  
  // AI usage (for admin only)
  const [aiUsed, setAiUsed] = useState<number | null>(null)
  const [aiBudget, setAiBudget] = useState<number | null>(null)
  const [isByok, setIsByok] = useState<boolean>(false)

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

  // Check agent status
  const checkAgentStatus = async () => {
    if (!userId || !token) return
    
    try {
      const response = await fetch(
        `/api/agent/status?user_id=${userId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.status === 'online') {
          setAgentStatus('online')
        } else if (data.status === 'offline') {
          setAgentStatus('offline')
        } else {
          setAgentStatus('unknown')
        }
        setAgentLastSeen(data.last_heartbeat)
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
      setAgentStatus('unknown')
    }
  }

  // Poll agent status every 30 seconds
  useEffect(() => {
    if (userId && token) {
      checkAgentStatus()
      const interval = setInterval(checkAgentStatus, 30000)
      return () => clearInterval(interval)
    }
  }, [userId, token, companyId])

  // Check AI usage (for admin only)
  const checkAiUsage = async () => {
    if (!companyId || !token || userRole !== 'admin') return
    
    try {
      const response = await fetch(
        `/api/form-pages/ai-usage?company_id=${companyId}&product_id=1`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setIsByok(data.is_byok)
        
        if (!data.is_byok) {
          setAiUsed(data.used)
          setAiBudget(data.budget)
        }
      }
    } catch (err) {
      console.error('Failed to check AI usage:', err)
    }
  }

  // Fetch AI usage on load and every 60 seconds (for admin only)
  useEffect(() => {
    if (userRole === 'admin' && companyId && token) {
      checkAiUsage()
      const interval = setInterval(checkAiUsage, 60000)
      return () => clearInterval(interval)
    }
  }, [userRole, companyId, token])

  useEffect(() => {
    // Check URL params first (coming from marketing site login)
    const urlParams = new URLSearchParams(window.location.search)
    const urlToken = urlParams.get('token')
    const urlUserId = urlParams.get('user_id')
    const urlCompanyId = urlParams.get('company_id')
    const urlUserType = urlParams.get('type')
    
    // If token in URL, store it and clean URL
    if (urlToken && urlUserId && urlCompanyId) {
      localStorage.setItem('token', urlToken)
      localStorage.setItem('user_id', urlUserId)
      localStorage.setItem('company_id', urlCompanyId)
      localStorage.setItem('userType', urlUserType || 'user')
      
      // Clean URL (remove params)
      window.history.replaceState({}, '', '/dashboard')
      
      setToken(urlToken)
      setUserId(urlUserId)
      setCompanyId(urlCompanyId)
      setUserRole(urlUserType || 'user')
      
      loadProjects(urlCompanyId, urlToken)
      return
    }
    
    // Otherwise check localStorage
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
    setShowPassword(false)
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
    setShowPassword(false)
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

  // Network Card Component
  const NetworkCard = ({ network, onEdit, onDelete }: { network: Network; onEdit: () => void; onDelete: () => void }) => (
    <div style={networkCardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div style={{ fontWeight: 600, fontSize: '15px', color: '#1e293b' }}>{network.name}</div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button onClick={onEdit} style={iconButtonStyle} title="Edit">✏️</button>
          <button onClick={onDelete} style={{ ...iconButtonStyle, borderColor: 'rgba(239, 68, 68, 0.3)' }} title="Delete">🗑️</button>
        </div>
      </div>
      <div style={{ fontSize: '13px', color: '#64748b', wordBreak: 'break-all', marginBottom: '8px' }}>{network.url}</div>
      {network.login_username && (
        <div style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>👤</span> {network.login_username}
        </div>
      )}
    </div>
  )

  if (!token) return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ color: '#94a3b8', fontSize: '16px' }}>Loading...</div>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #1e293b 0%, #334155 50%, #1e293b 100%)' }}>
      {/* CSS Animations */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .sidebar-item:hover {
          transform: translateX(4px);
        }
        .top-btn:hover {
          background: rgba(255,255,255,0.15) !important;
          transform: translateY(-1px);
        }
        .dropdown-item:hover {
          background: rgba(99, 102, 241, 0.1) !important;
        }
      `}</style>
      
      {/* Top Bar - Sleek Dark Glass Design */}
      <div style={topBarStyle}>
        {/* Left side - Logo only */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '52px',
            height: '52px',
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            borderRadius: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(0, 187, 249, 0.35)'
          }}>
            <span style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>Q</span>
          </div>
          <span style={{ 
            fontSize: '32px', 
            fontWeight: 700, 
            background: 'linear-gradient(135deg, #fff 0%, #cbd5e1 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.5px'
          }}>
            Quathera
          </span>
        </div>
        
        {/* Right side - Project selector + all controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Project Selector */}
          <div className="project-dropdown" style={{ position: 'relative' }}>
            <button
              onClick={(e) => { e.stopPropagation(); setShowProjectDropdown(!showProjectDropdown) }}
              style={projectButtonStyle}
            >
              <span style={{ 
                background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
                padding: '10px 14px',
                borderRadius: '10px',
                marginRight: '14px',
                fontSize: '18px'
              }}>📁</span>
              <span style={{ fontSize: '17px' }}>{activeProject ? activeProject.name : 'Select Project'}</span>
              <span style={{ marginLeft: '12px', opacity: 0.7, fontSize: '14px' }}>▼</span>
            </button>
            
            {showProjectDropdown && (
              <div style={dropdownMenuStyle}>
                <div style={dropdownHeaderStyle}>SWITCH PROJECT</div>
                {projects.length === 0 ? (
                  <div style={{ ...dropdownItemStyle, color: '#64748b' }}>No projects yet</div>
                ) : (
                  projects.map(project => (
                    <div
                      key={project.id}
                      onClick={() => selectProject(project)}
                      className="dropdown-item"
                      style={{
                        ...dropdownItemStyle,
                        background: activeProject?.id === project.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent'
                      }}
                    >
                      <span style={{ flex: 1, fontSize: '16px' }}>{project.name}</span>
                      <span style={{ fontSize: '15px', color: '#64748b' }}>
                        {project.network_count} sites
                      </span>
                    </div>
                  ))
                )}
                <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '12px 0' }} />
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowAddProjectModal(true) }}
                  className="dropdown-item"
                  style={{ ...dropdownItemStyle, color: '#00BBF9', fontSize: '16px' }}
                >
                  <span>＋</span> Add Project
                </div>
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowProjectsModal(true) }}
                  className="dropdown-item"
                  style={{ ...dropdownItemStyle, fontSize: '16px' }}
                >
                  <span>⚙️</span> Manage Projects
                </div>
              </div>
            )}
          </div>
          
          <div style={{ width: '1px', height: '40px', background: 'rgba(255,255,255,0.15)' }} />
          
          {/* AI Usage Indicator */}
          {userRole === 'admin' && !isByok && aiUsed !== null && aiBudget !== null && (
            <div style={topBarBadgeStyle} title={`AI Usage: $${aiUsed} / $${aiBudget}`}>
              <span style={{ 
                fontSize: '16px',
                background: 'linear-gradient(135deg, #a855f7, #6366f1)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: 600
              }}>AI:</span>
              <span style={{ 
                color: aiUsed >= aiBudget ? '#ef4444' : aiUsed >= aiBudget * 0.8 ? '#f59e0b' : '#10b981',
                fontWeight: 700,
                fontSize: '16px'
              }}>
                {Math.round(aiUsed)} / {aiBudget}
              </span>
            </div>
          )}
          
          {/* Agent Status - Strong Indicator */}
          <div 
            style={{
              ...topBarBadgeStyle,
              background: agentStatus === 'online' 
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(52, 211, 153, 0.2))'
                : 'rgba(255,255,255,0.05)',
              border: agentStatus === 'online' 
                ? '2px solid rgba(16, 185, 129, 0.6)'
                : '1px solid rgba(255,255,255,0.08)',
              padding: '14px 22px'
            }}
            title={agentLastSeen ? `Last seen: ${new Date(agentLastSeen + 'Z').toLocaleString()}` : 'No agent connected'}
          >
            <div style={{
              width: '14px',
              height: '14px',
              borderRadius: '50%',
              background: agentStatus === 'online' 
                ? '#22c55e' 
                : '#6b7280',
              boxShadow: agentStatus === 'online' ? '0 0 20px rgba(34, 197, 94, 0.8), 0 0 40px rgba(34, 197, 94, 0.4)' : 'none',
              animation: agentStatus === 'online' ? 'pulse 1.5s infinite' : 'none'
            }} />
            <span style={{ 
              color: agentStatus === 'online' ? '#22c55e' : '#9ca3af', 
              fontWeight: 700, 
              fontSize: '16px',
              textShadow: agentStatus === 'online' ? '0 0 10px rgba(34, 197, 94, 0.5)' : 'none'
            }}>
              Agent {agentStatus === 'online' ? 'Online' : 'Offline'}
            </span>
          </div>
          
          {/* Download Agent */}
          <button
            onClick={() => window.open('/api/installer/download/linux', '_blank')}
            className="top-btn"
            style={topBarButtonStyle}
          >
            <span>⬇️</span> Download Agent
          </button>
          
          {/* Logout */}
          <button onClick={handleLogout} className="top-btn" style={topBarButtonStyle}>
            Logout
          </button>
        </div>
      </div>

      {/* Messages - Floating Toast Style */}
      {error && (
        <div style={errorToastStyle}>
          <span>❌</span> {error}
          <button onClick={() => setError(null)} style={toastCloseStyle}>×</button>
        </div>
      )}
      {message && (
        <div style={successToastStyle}>
          <span>✅</span> {message}
        </div>
      )}

      {/* Main Layout */}
      <div style={{ display: 'flex', minHeight: 'calc(100vh - 70px)' }}>
        {/* Sidebar - Modern Glass Design */}
        <div style={sidebarStyle}>
          <div style={sidebarHeaderStyle}>
            <span>MENU</span>
          </div>
          
          <div style={{ padding: '0 16px' }}>
            {[
              { id: 'form-discovery', icon: '🔍', label: 'Form Pages Discovery' },
              { id: 'test-scenarios', icon: '📝', label: 'Test Scenarios' },
              { id: 'run-tests', icon: '▶️', label: 'Run Tests' },
              { id: 'form-mapping', icon: '🗺️', label: 'Form Page Mapping' },
            ].map((item, index) => (
              <div 
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className="sidebar-item"
                style={{
                  ...sidebarItemStyle,
                  background: activeTab === item.id 
                    ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)'
                    : 'rgba(255, 255, 255, 0.03)',
                  borderColor: activeTab === item.id ? 'rgba(99, 102, 241, 0.5)' : 'transparent',
                  animation: `slideIn 0.3s ease ${index * 0.05}s both`
                }}
              >
                <div style={{
                  ...sidebarIconStyle,
                  background: activeTab === item.id 
                    ? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
                    : 'rgba(255, 255, 255, 0.1)',
                  boxShadow: activeTab === item.id ? '0 4px 15px rgba(99, 102, 241, 0.3)' : 'none'
                }}>
                  <span>{item.icon}</span>
                </div>
                <span style={{ 
                  color: activeTab === item.id ? '#fff' : '#94a3b8',
                  fontWeight: activeTab === item.id ? 600 : 500
                }}>{item.label}</span>
              </div>
            ))}
            
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '20px 8px' }} />
            
            <div 
              onClick={() => setActiveTab('networks')}
              className="sidebar-item"
              style={{
                ...sidebarItemStyle,
                background: activeTab === 'networks' 
                  ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)'
                  : 'rgba(255, 255, 255, 0.03)',
                borderColor: activeTab === 'networks' ? 'rgba(99, 102, 241, 0.5)' : 'transparent'
              }}
            >
              <div style={{
                ...sidebarIconStyle,
                background: activeTab === 'networks' 
                  ? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
                  : 'rgba(255, 255, 255, 0.1)'
              }}>
                <span>🌐</span>
              </div>
              <span style={{ 
                color: activeTab === 'networks' ? '#fff' : '#94a3b8',
                fontWeight: activeTab === 'networks' ? 600 : 500
              }}>Test Sites</span>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ flex: 1, padding: '32px 40px', overflowY: 'auto' }}>
          {activeTab === 'form-discovery' && children}
          
          {activeTab === 'test-scenarios' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>📝</div>
              <h2 style={{ margin: '0 0 16px', color: '#fff', fontSize: '32px', fontWeight: 700, letterSpacing: '-0.5px' }}>Test Scenarios</h2>
              <p style={{ color: '#94a3b8', margin: 0, fontSize: '18px', lineHeight: 1.6 }}>Coming soon - Define and manage your test scenarios here.</p>
            </div>
          )}
          
          {activeTab === 'run-tests' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>▶️</div>
              <h2 style={{ margin: '0 0 16px', color: '#fff', fontSize: '32px', fontWeight: 700, letterSpacing: '-0.5px' }}>Run Tests</h2>
              <p style={{ color: '#94a3b8', margin: 0, fontSize: '18px', lineHeight: 1.6 }}>Coming soon - Execute your test scenarios and view results.</p>
            </div>
          )}
          
          {activeTab === 'form-mapping' && (
            <div style={placeholderCardStyle}>
              <div style={placeholderIconStyle}>🗺️</div>
              <h2 style={{ margin: '0 0 16px', color: '#fff', fontSize: '32px', fontWeight: 700, letterSpacing: '-0.5px' }}>Form Page Mapping</h2>
              <p style={{ color: '#94a3b8', margin: 0, fontSize: '18px', lineHeight: 1.6 }}>Coming soon - Visualize relationships between form pages.</p>
            </div>
          )}
          
          {activeTab === 'networks' && (
            <div style={contentCardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div>
                  <h2 style={{ margin: '0 0 10px', fontSize: '32px', fontWeight: 700, color: '#fff', letterSpacing: '-0.5px' }}>
                    <span style={{ marginRight: '14px' }}>🌐</span>Test Sites
                  </h2>
                  <p style={{ margin: 0, color: '#94a3b8', fontSize: '17px' }}>
                    Manage your test site environments for {activeProject?.name || 'this project'}
                  </p>
                </div>
              </div>
              
              {/* Environment Info Banner */}
              <div style={infoBannerStyle}>
                <div style={{ fontSize: '32px' }}>💡</div>
                <div>
                  <strong style={{ color: '#00BBF9', fontSize: '18px' }}>Environment Usage Guide</strong>
                  <p style={{ margin: '10px 0 0', color: '#94a3b8', fontSize: '16px', lineHeight: '1.7' }}>
                    <strong style={{ color: '#fff' }}>Form Pages Discovery & Mapping</strong> are performed exclusively in the <strong style={{ color: '#10b981' }}>QA environment</strong> to safely explore your application. 
                    When <strong style={{ color: '#fff' }}>running tests</strong>, you can target any environment based on your testing needs.
                  </p>
                </div>
              </div>
              
              {loadingNetworks ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Loading networks...</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* QA Networks */}
                  <div style={networkSectionStyle}>
                    <div style={networkSectionHeaderStyle} onClick={() => toggleSection('qa')}>
                      <span style={{ fontWeight: 600, color: '#fff' }}>
                        <span style={{ color: '#10b981', marginRight: '8px' }}>🧪</span>
                        QA Environment ({networks.qa.length})
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('qa') }} style={addBtnStyle}>＋</button>
                        <span style={{ color: '#64748b' }}>{collapsedSections.qa ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.qa && (
                      <div style={{ padding: '20px' }}>
                        {networks.qa.length === 0 ? (
                          <p style={emptyTextStyle}>No QA networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
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
                      <span style={{ fontWeight: 600, color: '#fff' }}>
                        <span style={{ color: '#f59e0b', marginRight: '8px' }}>🚀</span>
                        Staging Environment ({networks.staging.length})
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('staging') }} style={addBtnStyle}>＋</button>
                        <span style={{ color: '#64748b' }}>{collapsedSections.staging ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.staging && (
                      <div style={{ padding: '20px' }}>
                        {networks.staging.length === 0 ? (
                          <p style={emptyTextStyle}>No Staging networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
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
                      <span style={{ fontWeight: 600, color: '#fff' }}>
                        <span style={{ color: '#ef4444', marginRight: '8px' }}>🏭</span>
                        Production Environment ({networks.production.length})
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('production') }} style={addBtnStyle}>＋</button>
                        <span style={{ color: '#64748b' }}>{collapsedSections.production ? '▼' : '▲'}</span>
                      </div>
                    </div>
                    {!collapsedSections.production && (
                      <div style={{ padding: '20px' }}>
                        {networks.production.length === 0 ? (
                          <p style={emptyTextStyle}>No Production networks configured</p>
                        ) : (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
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
            <div style={modalHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: '22px', color: '#fff', fontWeight: 700 }}>
                <span style={{ marginRight: '10px' }}>📁</span>Create New Project
              </h2>
            </div>
            
            <div style={{ padding: '28px' }}>
              <div style={{ marginBottom: '20px' }}>
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
              
              <div style={{ marginBottom: '8px' }}>
                <label style={labelStyle}>Description (optional)</label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  placeholder="Enter project description"
                  style={{ ...inputStyle, minHeight: '100px', resize: 'vertical' }}
                />
              </div>
            </div>
            
            <div style={modalFooterStyle}>
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
            <div style={{ ...modalHeaderStyle, justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0, fontSize: '22px', color: '#fff', fontWeight: 700 }}>Manage Projects</h2>
              <button onClick={() => setShowProjectsModal(false)} style={modalCloseStyle}>×</button>
            </div>
            
            <div style={{ padding: '0', maxHeight: '400px', overflow: 'auto' }}>
              {projects.length === 0 ? (
                <p style={{ color: '#94a3b8', textAlign: 'center', padding: '40px' }}>No projects yet</p>
              ) : (
                projects.map(project => (
                  <div key={project.id} style={projectListItemStyle}>
                    <div>
                      <strong style={{ color: '#fff', fontSize: '16px' }}>{project.name}</strong>
                      {project.description && <p style={{ margin: '6px 0 0', fontSize: '14px', color: '#94a3b8' }}>{project.description}</p>}
                      <div style={{ fontSize: '13px', color: '#64748b', marginTop: '6px' }}>
                        {project.network_count} networks · {project.form_page_count} form pages
                      </div>
                    </div>
                    <button
                      onClick={() => { setProjectToDelete(project); setShowDeleteConfirm(true) }}
                      style={deleteIconBtnStyle}
                      title="Delete project"
                    >
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>
            
            <div style={modalFooterStyle}>
              <button
                onClick={() => { setShowProjectsModal(false); setShowAddProjectModal(true) }}
                style={primaryButtonStyle}
              >
                ＋ Add New Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Project Confirmation */}
      {showDeleteConfirm && projectToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <div style={{ ...modalHeaderStyle, background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.2))' }}>
              <h2 style={{ margin: 0, fontSize: '22px', color: '#ef4444', fontWeight: 700 }}>
                ⚠️ Delete Project?
              </h2>
            </div>
            <div style={{ padding: '28px' }}>
              <p style={{ color: '#e2e8f0', fontSize: '16px', margin: '0 0 20px' }}>
                Are you sure you want to delete <strong style={{ color: '#fff' }}>{projectToDelete.name}</strong>?
              </p>
              <div style={warningBoxStyle}>
                <strong style={{ color: '#f59e0b' }}>This will permanently delete:</strong>
                <ul style={{ margin: '12px 0 0', paddingLeft: '20px', color: '#94a3b8' }}>
                  <li>{projectToDelete.network_count} network(s)</li>
                  <li>{projectToDelete.form_page_count} form page(s)</li>
                </ul>
              </div>
            </div>
            <div style={modalFooterStyle}>
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

      {/* Add/Edit Network Modal */}
      {showAddNetworkModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <div style={modalHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: '22px', color: '#fff', fontWeight: 700 }}>
                {editingNetwork ? '✏️ Edit Network' : '🌐 Add Network'}
              </h2>
            </div>
            
            <div style={{ padding: '28px' }}>
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>Environment</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  {(['qa', 'staging', 'production'] as const).map(type => (
                    <button
                      key={type}
                      onClick={() => !editingNetwork && setAddNetworkType(type)}
                      style={{
                        flex: 1,
                        padding: '12px',
                        border: addNetworkType === type ? '2px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '10px',
                        background: addNetworkType === type 
                          ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2))' 
                          : 'rgba(255,255,255,0.03)',
                        color: addNetworkType === type ? '#fff' : '#94a3b8',
                        cursor: editingNetwork ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                        fontSize: '14px',
                        textTransform: 'capitalize',
                        opacity: editingNetwork && addNetworkType !== type ? 0.5 : 1
                      }}
                    >
                      {type === 'qa' ? '🧪' : type === 'staging' ? '🚀' : '🏭'} {type}
                    </button>
                  ))}
                </div>
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>Network Name *</label>
                <input
                  type="text"
                  value={networkName}
                  onChange={(e) => setNetworkName(e.target.value)}
                  placeholder="e.g., Main App, Admin Portal"
                  style={inputStyle}
                />
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>URL *</label>
                <input
                  type="text"
                  value={networkUrl}
                  onChange={(e) => setNetworkUrl(e.target.value)}
                  placeholder="https://example.com"
                  style={inputStyle}
                />
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>Login Username (optional)</label>
                <input
                  type="text"
                  value={networkUsername}
                  onChange={(e) => setNetworkUsername(e.target.value)}
                  placeholder="Username for auto-login"
                  style={inputStyle}
                />
              </div>
              
              <div>
                <label style={labelStyle}>Login Password (optional)</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={networkPassword}
                    onChange={(e) => setNetworkPassword(e.target.value)}
                    placeholder="Password for auto-login"
                    style={{ ...inputStyle, paddingRight: '50px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: '#64748b',
                      cursor: 'pointer',
                      fontSize: '16px'
                    }}
                  >
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>
            </div>
            
            <div style={modalFooterStyle}>
              <button onClick={() => setShowAddNetworkModal(false)} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button
                onClick={handleSaveNetwork}
                style={primaryButtonStyle}
                disabled={savingNetwork || !networkName.trim() || !networkUrl.trim()}
              >
                {savingNetwork ? 'Saving...' : editingNetwork ? 'Update Network' : 'Add Network'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Network Confirmation */}
      {showDeleteNetworkConfirm && networkToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <div style={{ ...modalHeaderStyle, background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.2))' }}>
              <h2 style={{ margin: 0, fontSize: '22px', color: '#ef4444', fontWeight: 700 }}>
                ⚠️ Delete Network?
              </h2>
            </div>
            <div style={{ padding: '28px' }}>
              <p style={{ color: '#e2e8f0', fontSize: '16px', margin: 0 }}>
                Are you sure you want to delete <strong style={{ color: '#fff' }}>{networkToDelete.name}</strong>?
              </p>
              <p style={{ color: '#94a3b8', fontSize: '14px', marginTop: '12px' }}>
                This will also delete all form pages discovered from this network.
              </p>
            </div>
            <div style={modalFooterStyle}>
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

// ============================================
// STYLES
// ============================================

const topBarStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px 36px',
  background: 'rgba(30, 41, 59, 0.95)',
  backdropFilter: 'blur(20px)',
  borderBottom: '1px solid rgba(255,255,255,0.08)',
  position: 'sticky',
  top: 0,
  zIndex: 100,
  boxShadow: '0 4px 30px rgba(0,0,0,0.2)'
}

const projectButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15))',
  border: '1px solid rgba(99, 102, 241, 0.3)',
  borderRadius: '14px',
  padding: '12px 20px',
  color: '#fff',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  transition: 'all 0.2s ease'
}

const dropdownMenuStyle: React.CSSProperties = {
  position: 'absolute',
  top: 'calc(100% + 10px)',
  left: 0,
  background: 'rgba(30, 41, 59, 0.98)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '18px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  minWidth: '320px',
  zIndex: 1000,
  overflow: 'hidden',
  animation: 'fadeIn 0.2s ease'
}

const dropdownHeaderStyle: React.CSSProperties = {
  padding: '16px 22px',
  fontSize: '12px',
  fontWeight: 700,
  color: '#64748b',
  letterSpacing: '1.5px',
  borderBottom: '1px solid rgba(255,255,255,0.05)'
}

const dropdownItemStyle: React.CSSProperties = {
  padding: '16px 22px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  color: '#e2e8f0',
  fontSize: '16px',
  transition: 'all 0.15s ease'
}

const topBarBadgeStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px 18px',
  background: 'rgba(255,255,255,0.05)',
  borderRadius: '12px',
  border: '1px solid rgba(255,255,255,0.08)',
  fontSize: '15px'
}

const topBarButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  padding: '12px 22px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  color: '#e2e8f0',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  transition: 'all 0.2s ease'
}

const errorToastStyle: React.CSSProperties = {
  position: 'fixed',
  top: '90px',
  right: '32px',
  background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(185, 28, 28, 0.95))',
  color: '#fff',
  padding: '16px 24px',
  borderRadius: '12px',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  zIndex: 1000,
  boxShadow: '0 10px 40px rgba(239, 68, 68, 0.3)',
  animation: 'fadeIn 0.3s ease',
  fontSize: '14px',
  fontWeight: 500
}

const successToastStyle: React.CSSProperties = {
  position: 'fixed',
  top: '90px',
  right: '32px',
  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.95), rgba(5, 150, 105, 0.95))',
  color: '#fff',
  padding: '16px 24px',
  borderRadius: '12px',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  zIndex: 1000,
  boxShadow: '0 10px 40px rgba(16, 185, 129, 0.3)',
  animation: 'fadeIn 0.3s ease',
  fontSize: '14px',
  fontWeight: 500
}

const toastCloseStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.2)',
  border: 'none',
  color: '#fff',
  width: '24px',
  height: '24px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '16px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginLeft: '8px'
}

const sidebarStyle: React.CSSProperties = {
  width: '320px',
  background: 'rgba(30, 41, 59, 0.7)',
  backdropFilter: 'blur(20px)',
  borderRight: '1px solid rgba(255,255,255,0.08)',
  flexShrink: 0
}

const sidebarHeaderStyle: React.CSSProperties = {
  padding: '36px 28px 24px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#64748b',
  letterSpacing: '2.5px',
  textTransform: 'uppercase'
}

const sidebarItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '18px',
  padding: '20px 24px',
  cursor: 'pointer',
  fontSize: '18px',
  fontWeight: 500,
  transition: 'all 0.2s ease',
  borderRadius: '14px',
  margin: '8px 0',
  border: '1px solid transparent',
  color: '#e2e8f0'
}

const sidebarIconStyle: React.CSSProperties = {
  width: '52px',
  height: '52px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: '14px',
  fontSize: '24px',
  transition: 'all 0.2s ease'
}

const placeholderCardStyle: React.CSSProperties = {
  background: 'rgba(51, 65, 85, 0.4)',
  backdropFilter: 'blur(20px)',
  borderRadius: '28px',
  padding: '100px 80px',
  textAlign: 'center',
  border: '1px solid rgba(255,255,255,0.08)',
  boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
}

const placeholderIconStyle: React.CSSProperties = {
  width: '110px',
  height: '110px',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2))',
  borderRadius: '28px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '48px',
  margin: '0 auto 28px',
  border: '1px solid rgba(99, 102, 241, 0.3)'
}

const contentCardStyle: React.CSSProperties = {
  background: 'rgba(51, 65, 85, 0.5)',
  backdropFilter: 'blur(20px)',
  borderRadius: '24px',
  padding: '32px',
  border: '1px solid rgba(255,255,255,0.08)',
  boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
}

const infoBannerStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(0, 187, 249, 0.1), rgba(0, 245, 212, 0.1))',
  border: '1px solid rgba(0, 187, 249, 0.2)',
  borderRadius: '16px',
  padding: '20px 24px',
  marginBottom: '28px',
  display: 'flex',
  alignItems: 'flex-start',
  gap: '16px'
}

const networkSectionStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.02)',
  borderRadius: '16px',
  overflow: 'hidden',
  border: '1px solid rgba(255,255,255,0.05)'
}

const networkSectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '18px 24px',
  background: 'rgba(255, 255, 255, 0.03)',
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const addBtnStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  borderRadius: '8px',
  width: '32px',
  height: '32px',
  fontSize: '18px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)'
}

const networkCardStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '14px',
  padding: '18px',
  transition: 'all 0.2s ease'
}

const iconButtonStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '8px',
  padding: '8px 10px',
  cursor: 'pointer',
  fontSize: '14px',
  transition: 'all 0.2s ease'
}

const emptyTextStyle: React.CSSProperties = {
  color: '#64748b',
  fontSize: '14px',
  textAlign: 'center',
  padding: '24px'
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
  padding: '20px',
  animation: 'fadeIn 0.2s ease'
}

const modalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(51, 65, 85, 0.98), rgba(30, 41, 59, 0.98))',
  borderRadius: '24px',
  width: '100%',
  maxWidth: '500px',
  border: '1px solid rgba(255,255,255,0.12)',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  overflow: 'hidden'
}

const modalHeaderStyle: React.CSSProperties = {
  padding: '24px 28px',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15))',
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  display: 'flex',
  alignItems: 'center'
}

const modalCloseStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: 'none',
  color: '#94a3b8',
  width: '36px',
  height: '36px',
  borderRadius: '10px',
  cursor: 'pointer',
  fontSize: '24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.2s ease'
}

const modalFooterStyle: React.CSSProperties = {
  padding: '20px 28px',
  background: 'rgba(255,255,255,0.02)',
  borderTop: '1px solid rgba(255,255,255,0.05)',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '12px'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '10px',
  fontWeight: 600,
  color: '#e2e8f0',
  fontSize: '16px'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '16px 20px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '14px',
  fontSize: '17px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.05)',
  color: '#fff',
  outline: 'none',
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

const warningBoxStyle: React.CSSProperties = {
  background: 'rgba(245, 158, 11, 0.1)',
  border: '1px solid rgba(245, 158, 11, 0.3)',
  padding: '20px',
  borderRadius: '14px'
}

const projectListItemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '22px 30px',
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  transition: 'all 0.2s ease'
}

const deleteIconBtnStyle: React.CSSProperties = {
  background: 'rgba(239, 68, 68, 0.1)',
  border: '1px solid rgba(239, 68, 68, 0.2)',
  borderRadius: '12px',
  padding: '12px 16px',
  cursor: 'pointer',
  fontSize: '18px',
  transition: 'all 0.2s ease'
}
