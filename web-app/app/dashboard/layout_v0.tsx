'use client'
import { useEffect, useState } from 'react'
import React from "react"

import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { useRouter, usePathname } from 'next/navigation'

interface Project {
  id: number
  name: string
  description: string | null
  network_count: number
  form_page_count: number
  created_by_user_id: number
  project_type: 'enterprise' | 'dynamic_content'
}

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
  login_password: string | null
  totp_secret: string | null
  has_totp: boolean
  created_at: string
}

interface NetworksByType {
  qa: Network[]
  staging: Network[]
  production: Network[]
}

// ============================================
// COLOR SYSTEM - Single source of truth
// ============================================
const t = {
  // Backgrounds
  pageBg: '#f0f4f8',
  cardBg: '#ffffff',
  sidebarBg: '#0f1b2d',
  headerBg: '#ffffff',
  mutedBg: '#f1f5f9',
  hoverBg: '#e8f4f8',
  // Text
  text: '#0f172a',
  textSecondary: '#475569',
  textMuted: '#94a3b8',
  // Sidebar-specific
  sidebarText: '#94a3b8',
  sidebarTextActive: '#ffffff',
  sidebarHover: 'rgba(255,255,255,0.06)',
  sidebarActiveBg: 'rgba(8, 145, 178, 0.2)',
  sidebarSection: '#64748b',
  // Brand
  brand: '#0891b2',
  brandLight: 'rgba(8, 145, 178, 0.12)',
  brandBorder: 'rgba(8, 145, 178, 0.3)',
  brandText: '#0891b2',
  // Borders
  border: '#e2e8f0',
  borderLight: '#f1f5f9',
  // Status
  success: '#059669',
  successBg: '#ecfdf5',
  successBorder: '#a7f3d0',
  warning: '#d97706',
  warningBg: '#fffbeb',
  warningBorder: '#fde68a',
  danger: '#dc2626',
  dangerBg: '#fef2f2',
  dangerBorder: '#fecaca',
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const [userId, setUserId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  
  // Active project
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  
  // Project dropdown
  const [showProjectDropdown, setShowProjectDropdown] = useState(false)

  // User dropdown
  const [showUserDropdown, setShowUserDropdown] = useState(false)
  
  // Projects modal (for managing projects)
  const [showProjectsModal, setShowProjectsModal] = useState(false)
  const [showAddProjectModal, setShowAddProjectModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [newProjectType, setNewProjectType] = useState<'enterprise' | 'dynamic_content'>('enterprise')
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
  const [totpSecret, setTotpSecret] = useState('')
  const [showTotpSecret, setShowTotpSecret] = useState(false)
  const [credentialsChanged, setCredentialsChanged] = useState({
    username: false,
    password: false,
    totp: false
  })
  const [savingNetwork, setSavingNetwork] = useState(false)
  const [editingNetwork, setEditingNetwork] = useState<Network | null>(null)
  
  // Delete Network
  const [showDeleteNetworkConfirm, setShowDeleteNetworkConfirm] = useState(false)
  const [networkToDelete, setNetworkToDelete] = useState<Network | null>(null)
  const [deletingNetwork, setDeletingNetwork] = useState(false)
  
  // Messages
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Helper to check active route
  const isActiveRoute = (route: string) => pathname?.includes(route) || false
  
  // Agent status
  const [agentStatus, setAgentStatus] = useState<'online' | 'offline' | 'unknown'>('unknown')
  const [agentLastSeen, setAgentLastSeen] = useState<string | null>(null)
  
  // AI usage (for admin only)
  const [aiUsed, setAiUsed] = useState<number | null>(null)
  const [aiBudget, setAiBudget] = useState<number | null>(null)
  const [isByok, setIsByok] = useState<boolean>(false)

  const [accountCategory, setAccountCategory] = useState<string | null>(null)

  // Load networks when Test Sites tab is selected
  useEffect(() => {
    if (pathname?.includes('test-sites') && activeProject) {
      loadNetworksForTab()
    }
  }, [pathname, activeProject])

  const loadNetworksForTab = async () => {
    if (!activeProject) return
    setLoadingNetworks(true)
    try {
      const response = await fetchWithAuth(
        `/api/projects/${activeProject.id}/networks`
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
    if (!userId) return

    try {
      const response = await fetchWithAuth(
        `/api/agent/status`
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
    if (userId) {
      checkAgentStatus()
      const interval = setInterval(checkAgentStatus, 30000)
      return () => clearInterval(interval)
    }
  }, [userId])

  // Check AI usage (for admin only)
  const checkAiUsage = async () => {
    if (userRole !== 'admin') return

    try {
      const response = await fetchWithAuth(
        `/api/company/ai-usage?product_id=1`
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
    if (userRole === 'admin') {
      checkAiUsage()
      const interval = setInterval(checkAiUsage, 60000)
      return () => clearInterval(interval)
    }
  }, [userRole])

  useEffect(() => {
    // URL params no longer used - auth is via HttpOnly cookies
    // Clean any legacy URL params
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.has('token')) {
      window.history.replaceState({}, '', '/dashboard')
    }
    
    // Check localStorage for UI display data
    const storedUserId = localStorage.getItem('user_id')
    const storedUserRole = localStorage.getItem('userType')

    // Verify auth by calling API (cookie will be sent automatically)
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
        setUserRole(data.type)
        localStorage.setItem('user_id', String(data.user_id))
        localStorage.setItem('userType', data.type)

        // Check onboarding status for regular users
        if (data.type !== 'super_admin') {
          fetchWithAuth('/api/onboarding/status')
            .then(res => res.ok ? res.json() : null)
            .then(onboardingData => {
              if (onboardingData && !onboardingData.onboarding_completed) {
                window.location.href = '/onboarding'
              }
              if (onboardingData && onboardingData.account_category) {
                setAccountCategory(onboardingData.account_category)
              }
            })
            .catch(err => console.error('Failed to check onboarding:', err))
        }

        loadProjects()
      })
      .catch(() => {
        window.location.href = '/login'
      })
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

  const loadProjects = async () => {
    setLoadingProjects(true)
    try {
      const response = await fetchWithAuth(
        '/api/projects/'
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

    // Auto-redirect based on project type
    if (project.project_type === 'dynamic_content' && pathname?.includes('form-pages-discovery')) {
      router.push('/dashboard/test-pages')
    } else if (project.project_type === 'enterprise' && pathname?.includes('test-pages')) {
      router.push('/dashboard/form-pages-discovery')
    }
  }

  const handleAddProject = async () => {
    if (!newProjectName.trim()) {
      setError('Project name is required')
      return
    }
    
    setAddingProject(true)
    setError(null)
    
    try {
      const response = await fetchWithAuth(
        '/api/projects/',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: newProjectName.trim(),
            description: newProjectDescription.trim() || null,
            product_id: 1,
            project_type: accountCategory === 'form_centric' ? 'enterprise'
                        : accountCategory === 'dynamic' ? 'dynamic_content'
                        : newProjectType
          })

        }
      )
      
      if (response.ok) {
        const newProject = await response.json()
        setMessage('Project created successfully!')
        setShowAddProjectModal(false)
        setNewProjectName('')
        setNewProjectDescription('')
        setNewProjectType('enterprise')
        loadProjects()
        // Auto-select the new project
        selectProject(newProject)
      } else {
        const errData = await response.json()
        setError(typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Failed to create project'))
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
      const response = await fetchWithAuth(
        `/api/projects/${projectToDelete.id}`,
        {
          method: 'DELETE'
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
        
        loadProjects()
      } else {
        const errData = await response.json()
        setError(typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Failed to delete project'))
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
      const response = await fetchWithAuth(
        `/api/projects/${activeProject.id}/networks`
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
    setTotpSecret('')
    setCredentialsChanged({ username: false, password: false, totp: false })
    setShowPassword(false)
    setShowTotpSecret(false)
    setEditingNetwork(null)
    setShowAddNetworkModal(true)
  }

  const openEditNetworkModal = (network: Network) => {
    setEditingNetwork(network)
    setAddNetworkType(network.network_type as 'qa' | 'staging' | 'production')
    setNetworkName(network.name)
    setNetworkUrl(network.url)
    setNetworkUsername(network.login_username ? '********' : '')
    setNetworkPassword(network.login_password ? '********' : '')
    setTotpSecret(network.totp_secret ? '********' : '')
    setCredentialsChanged({ username: false, password: false, totp: false })
    setShowPassword(false)
    setShowTotpSecret(false)
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
        : `/api/projects/${activeProject!.id}/networks`

      const response = await fetchWithAuth(url, {
        method: editingNetwork ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: networkName.trim(),
          url: networkUrl.trim(),
          network_type: addNetworkType,
          ...(credentialsChanged.username && { login_username: networkUsername.trim() || null }),
          ...(credentialsChanged.password && { login_password: networkPassword.trim() || null }),
          ...(credentialsChanged.totp && { totp_secret: totpSecret.trim() || null })
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
        setError(typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Failed to save network'))
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
      const response = await fetchWithAuth(
        `/api/projects/${activeProject!.id}/networks/${networkToDelete.id}`,
        {
          method: 'DELETE'
        }
      )
      
      if (response.ok) {
        setMessage('Network deleted!')
        setShowDeleteNetworkConfirm(false)
        setNetworkToDelete(null)
        openNetworksModal()
      } else {
        const errData = await response.json()
        setError(typeof errData.detail === 'string' ? errData.detail : (errData.detail?.[0]?.msg || 'Failed to delete network'))
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingNetwork(false)
    }
  }

  const handleLogout = async () => {
    try {
      await fetchWithAuth('/api/auth/logout', {
        method: 'POST'
      })
    } catch (err) {
      console.error('Logout error:', err)
    }
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
        <div style={{ fontWeight: 600, fontSize: '14px', color: t.text }}>{network.name}</div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={onEdit} style={iconButtonStyle} title="Edit">Edit</button>
          <button onClick={onDelete} style={{ ...iconButtonStyle, color: t.danger, borderColor: t.dangerBorder }} title="Delete">Delete</button>
        </div>
      </div>
      <div style={{ fontSize: '13px', color: t.textMuted, wordBreak: 'break-all', marginBottom: '6px' }}>{network.url}</div>
      {network.login_username && (
        <div style={{ fontSize: '12px', color: t.textMuted, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px' }}>User:</span> {network.login_username}
        </div>
      )}
    </div>
  )

  if (!userId) return (
    <div style={{ 
      minHeight: '100vh', 
      background: t.pageBg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ color: t.textMuted, fontSize: '14px' }}>Loading...</div>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: t.pageBg }}>
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
 .sidebar-item:hover {
  background: ${t.sidebarHover} !important;
  color: ${t.sidebarTextActive} !important;
  }
        .top-btn:hover {
          background: ${t.hoverBg} !important;
        }
        .dropdown-item:hover {
          background: ${t.hoverBg} !important;
        }
      `}</style>
      
      {/* ============================================ */}
      {/* HEADER */}
      {/* ============================================ */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0 24px',
        height: '56px',
        background: t.headerBg,
        borderBottom: `1px solid ${t.border}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Left side - Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            background: `linear-gradient(135deg, ${t.brand}, #06b6d4)`,
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(8, 145, 178, 0.3)',
          }}>
            <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Q</span>
          </div>
          <span style={{ 
            fontSize: '17px', 
            fontWeight: 700, 
            color: t.text,
            letterSpacing: '-0.4px'
          }}>
            Quattera AI
          </span>
        </div>
        
        {/* Right side - Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Project Selector */}
          <div className="project-dropdown" style={{ position: 'relative' }}>
            <button
              onClick={(e) => { e.stopPropagation(); setShowProjectDropdown(!showProjectDropdown) }}
              style={{
                background: t.brandLight,
                border: `1px solid ${t.brandBorder}`,
                borderRadius: '8px',
                padding: '6px 12px',
                color: t.text,
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ width: '8px', height: '8px', borderRadius: '3px', background: t.success }} />
              <span>{activeProject ? activeProject.name : 'Select Project'}</span>
              <span style={{ color: t.textMuted, fontSize: '10px' }}>&#9660;</span>
            </button>
            
            {showProjectDropdown && (
              <div style={dropdownMenuStyle}>
                <div style={dropdownHeaderStyle}>SWITCH PROJECT</div>
                {projects.length === 0 ? (
                  <div style={{ ...dropdownItemStyle, color: t.textMuted }}>No projects yet</div>
                ) : (
                  projects.map(project => (
                    <div
                      key={project.id}
                      onClick={() => selectProject(project)}
                      className="dropdown-item"
                      style={{
                        ...dropdownItemStyle,
                        background: activeProject?.id === project.id ? t.brandLight : 'transparent',
                        color: activeProject?.id === project.id ? t.brand : t.text,
                      }}
                    >
                      <span style={{ flex: 1, fontSize: '13px' }}>{project.name}</span>
                      <span style={{ fontSize: '12px', color: t.textMuted }}>
                        {project.network_count} sites
                      </span>
                    </div>
                  ))
                )}
                <div style={{ height: '1px', background: t.border, margin: '4px 0' }} />
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowAddProjectModal(true) }}
                  className="dropdown-item"
                  style={{ ...dropdownItemStyle, color: t.brand, fontWeight: 500 }}
                >
                  + Add Project
                </div>
                <div
                  onClick={() => { setShowProjectDropdown(false); setShowProjectsModal(true) }}
                  className="dropdown-item"
                  style={{ ...dropdownItemStyle }}
                >
                  Manage Projects
                </div>
              </div>
            )}
          </div>
          
          <div style={{ width: '1px', height: '24px', background: t.border }} />
          
          {/* AI Usage Indicator */}
          {userRole === 'admin' && !isByok && aiUsed !== null && aiBudget !== null && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                background: t.warningBg,
                borderRadius: '6px',
                border: `1px solid ${t.warningBorder}`,
                fontSize: '12px',
                color: t.warning,
              }}
              title={`AI Usage: ${Math.round(aiUsed)} / ${aiBudget} actions`}
            >
              <span style={{ fontSize: '11px' }}>AI Trial:</span>
              <span style={{ fontWeight: 600, color: aiUsed >= aiBudget ? t.danger : aiUsed >= aiBudget * 0.8 ? t.warning : t.success }}>
                {Math.round(aiUsed)} / {aiBudget}
              </span>
            </div>
          )}
          
          {/* Agent Status */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              background: agentStatus === 'online' ? t.successBg : t.mutedBg,
              borderRadius: '6px',
              border: `1px solid ${agentStatus === 'online' ? t.successBorder : t.border}`,
              fontSize: '12px',
            }}
            title={agentLastSeen ? `Last seen: ${new Date(agentLastSeen + 'Z').toLocaleString()}` : 'No agent connected'}
          >
            <div style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: agentStatus === 'online' ? t.success : t.textMuted,
              animation: agentStatus === 'online' ? 'pulse 2s infinite' : 'none'
            }} />
            <span style={{ 
              color: agentStatus === 'online' ? t.success : t.textMuted, 
              fontWeight: 500, 
            }}>
              {agentStatus === 'online' ? 'Online' : 'Offline'}
            </span>
          </div>
          
          {/* Download Agent */}
          <button
            onClick={() => window.open('/api/installer/download/linux', '_blank')}
            className="top-btn"
            style={{
              background: 'transparent',
              border: `1px solid ${t.brandBorder}`,
              borderRadius: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              color: t.brand,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            Download Agent
          </button>
          
          {/* User Menu Dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              onBlur={() => setTimeout(() => setShowUserDropdown(false), 200)}
              style={{
                background: t.brandLight,
                border: 'none',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                color: t.brand,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease'
              }}
            >
              A
            </button>

            {showUserDropdown && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                background: t.cardBg,
                borderRadius: '8px',
                border: `1px solid ${t.border}`,
                boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                minWidth: '160px',
                overflow: 'hidden',
                zIndex: 1000,
                animation: 'fadeIn 0.15s ease',
              }}>
                <div
                  onClick={() => {
                    setShowUserDropdown(false)
                    router.push('/settings')
                  }}
                  className="dropdown-item"
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: t.text,
                    fontSize: '13px',
                    fontWeight: 500,
                    transition: 'background 0.15s ease'
                  }}
                >
                  Settings
                </div>
                <div style={{ height: '1px', background: t.border }} />
                <div
                  onClick={() => {
                    setShowUserDropdown(false)
                    handleLogout()
                  }}
                  className="dropdown-item"
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: t.danger,
                    fontSize: '13px',
                    fontWeight: 500,
                    transition: 'background 0.15s ease'
                  }}
                >
                  Logout
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toasts */}
      {error && (
        <div style={errorToastStyle}>
          {error}
          <button onClick={() => setError(null)} style={toastCloseStyle}>&times;</button>
        </div>
      )}
      {message && (
        <div style={successToastStyle}>
          {message}
        </div>
      )}

      {/* ============================================ */}
      {/* MAIN LAYOUT (Sidebar + Content) */}
      {/* ============================================ */}
      <div style={{ display: 'flex', minHeight: 'calc(100vh - 56px)' }}>
        {/* ============================================ */}
        {/* SIDEBAR */}
        {/* ============================================ */}
        <div style={{
          width: '230px',
          background: t.sidebarBg,
          borderRight: 'none',
          flexShrink: 0,
          paddingTop: '12px',
          boxShadow: '2px 0 12px rgba(0,0,0,0.08)',
        }}>          
          <div style={{ padding: '0 12px' }}>
            {/* Team Members - admin only */}
            {(userRole === 'admin' || userRole === 'super_admin') && (
              <>
                <div style={{ padding: '14px 12px 8px', fontSize: '10px', fontWeight: 700, color: t.sidebarSection, letterSpacing: '0.8px', textTransform: 'uppercase' }}>
                  Team
                </div>
                <div 
                  onClick={() => router.push('/users')}
                  className="sidebar-item"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '9px 12px',
                    cursor: 'pointer',
                    fontSize: '13.5px',
                    fontWeight: pathname === '/users' ? 600 : 400,
                    borderRadius: '7px',
                    color: pathname === '/users' ? t.sidebarTextActive : t.sidebarText,
                    background: pathname === '/users' ? t.sidebarActiveBg : 'transparent',
                    borderLeft: pathname === '/users' ? `3px solid ${t.brand}` : '3px solid transparent',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span>Members</span>
                </div>
              </>
            )}
            
            {/* Project section */}
            <div style={{ padding: '18px 12px 8px', fontSize: '10px', fontWeight: 700, color: t.sidebarSection, letterSpacing: '0.8px', textTransform: 'uppercase' }}>
              Project
            </div>
            
            {[
              { id: 'project-dashboard', path: '/dashboard/project-dashboard', label: 'Dashboard' },
              ...(activeProject?.project_type === 'dynamic_content'
                ? [{ id: 'test-pages', path: '/dashboard/test-pages', label: 'Test Pages' }]
                : [
                    { id: 'form-pages-discovery', path: '/dashboard/form-pages-discovery', label: 'Form Discovery' },
                    { id: 'custom-tests', path: '/dashboard/custom-tests', label: 'Custom Tests' }
                  ]
              ),
              { id: 'test-scenarios', path: '/dashboard/test-scenarios', label: 'Test Scenarios' },
              { id: 'run-tests', path: '/dashboard/run-tests', label: 'Run Tests' },
              { id: 'test-sites', path: '/dashboard/test-sites', label: 'Test Sites' },
            ].map((item) => (
              <div 
                key={item.id}
                onClick={() => router.push(item.path)}
                className="sidebar-item"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 12px',
                  cursor: 'pointer',
                  fontSize: '13.5px',
                  fontWeight: isActiveRoute(item.id) ? 600 : 400,
                  borderRadius: '7px',
                  color: isActiveRoute(item.id) ? t.sidebarTextActive : t.sidebarText,
                  background: isActiveRoute(item.id) ? t.sidebarActiveBg : 'transparent',
                  borderLeft: isActiveRoute(item.id) ? `3px solid ${t.brand}` : '3px solid transparent',
                  transition: 'all 0.15s ease',
                  margin: '1px 0',
                }}
              >
                <span>{item.label}</span>
              </div>
            ))}
            
            {/* System section */}
            <div style={{ padding: '18px 12px 8px', fontSize: '10px', fontWeight: 700, color: t.sidebarSection, letterSpacing: '0.8px', textTransform: 'uppercase' }}>
              System
            </div>
            
            <div 
              onClick={() => router.push('/dashboard/logs')}
              className="sidebar-item"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 12px',
                cursor: 'pointer',
                fontSize: '13.5px',
                fontWeight: isActiveRoute('logs') ? 600 : 400,
                borderRadius: '7px',
                color: isActiveRoute('logs') ? t.sidebarTextActive : t.sidebarText,
                background: isActiveRoute('logs') ? t.sidebarActiveBg : 'transparent',
                borderLeft: isActiveRoute('logs') ? `3px solid ${t.brand}` : '3px solid transparent',
                transition: 'all 0.15s ease',
              }}
            >
              <span>Logs</span>
            </div>
          </div>
        </div>

        {/* ============================================ */}
        {/* CONTENT AREA */}
        {/* ============================================ */}
        <div style={{ flex: 1, padding: '24px 32px', overflowY: 'auto' }}>
          {pathname?.includes('test-sites') ? (
            <div style={contentCardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ margin: '0 0 4px', fontSize: '18px', fontWeight: 600, color: t.text, letterSpacing: '-0.3px' }}>
                    Test Sites
                  </h2>
                  <p style={{ margin: 0, color: t.textMuted, fontSize: '13px' }}>
                    Manage your test site environments for {activeProject?.name || 'this project'}
                  </p>
                </div>
              </div>
              
              {/* Environment Info Banner */}
              <div style={infoBannerStyle}>
                <div>
                  <strong style={{ color: t.brand, fontSize: '13px' }}>Environment Usage Guide</strong>
                  <p style={{ margin: '6px 0 0', color: t.textSecondary, fontSize: '13px', lineHeight: '1.6' }}>
                    <strong style={{ color: t.text }}>Form Pages Discovery & Mapping</strong> are performed exclusively in the <strong style={{ color: t.success }}>QA environment</strong> to safely explore your application. 
                    When <strong style={{ color: t.text }}>running tests</strong>, you can target any environment based on your testing needs.
                  </p>
                </div>
              </div>
              
              {loadingNetworks ? (
                <div style={{ textAlign: 'center', padding: '32px', color: t.textMuted, fontSize: '13px' }}>Loading networks...</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {/* QA Networks */}
                  <div style={networkSectionStyle}>
                    <div style={networkSectionHeaderStyle} onClick={() => toggleSection('qa')}>
                      <span style={{ fontWeight: 600, color: t.text, fontSize: '13px' }}>
                        <span style={{ color: t.success, marginRight: '6px' }}>&#9679;</span>
                        QA Environment ({networks.qa.length})
                      </span>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('qa') }} style={addBtnStyle}>+</button>
                        <span style={{ color: t.textMuted, fontSize: '10px' }}>{collapsedSections.qa ? '&#9660;' : '&#9650;'}</span>
                      </div>
                    </div>
                    {!collapsedSections.qa && (
                      <div style={{ padding: '12px 16px' }}>
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
                      <span style={{ fontWeight: 600, color: t.text, fontSize: '13px' }}>
                        <span style={{ color: t.warning, marginRight: '6px' }}>&#9679;</span>
                        Staging Environment ({networks.staging.length})
                      </span>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('staging') }} style={addBtnStyle}>+</button>
                        <span style={{ color: t.textMuted, fontSize: '10px' }}>{collapsedSections.staging ? '&#9660;' : '&#9650;'}</span>
                      </div>
                    </div>
                    {!collapsedSections.staging && (
                      <div style={{ padding: '12px 16px' }}>
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
                      <span style={{ fontWeight: 600, color: t.text, fontSize: '13px' }}>
                        <span style={{ color: t.danger, marginRight: '6px' }}>&#9679;</span>
                        Production Environment ({networks.production.length})
                      </span>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <button onClick={(e) => { e.stopPropagation(); openAddNetworkModal('production') }} style={addBtnStyle}>+</button>
                        <span style={{ color: t.textMuted, fontSize: '10px' }}>{collapsedSections.production ? '&#9660;' : '&#9650;'}</span>
                      </div>
                    </div>
                    {!collapsedSections.production && (
                      <div style={{ padding: '12px 16px' }}>
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
          ) : (
            children
          )}
        </div>
      </div>

      {/* ============================================ */}
      {/* MODALS */}
      {/* ============================================ */}

      {/* Add Project Modal */}
      {showAddProjectModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <div style={modalHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: '16px', color: t.text, fontWeight: 600 }}>
                Create New Project
              </h2>
            </div>
            
            <div style={{ padding: '20px' }}>
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
              
              <div style={{ marginBottom: '8px' }}>
                <label style={labelStyle}>Description (optional)</label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  placeholder="Enter project description"
                  style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }}
                />
              </div>

              {/* Only show project type selection if accountCategory is null (legacy users) */}
              {accountCategory === null && (
              <div style={{ marginBottom: '8px' }}>
                <label style={labelStyle}>Project Type *</label>
                <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    cursor: 'pointer',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    border: newProjectType === 'enterprise' ? `2px solid ${t.brand}` : `1px solid ${t.border}`,
                    background: newProjectType === 'enterprise' ? t.brandLight : 'transparent',
                    flex: 1
                  }}>
                    <input
                      type="radio"
                      name="projectType"
                      value="enterprise"
                      checked={newProjectType === 'enterprise'}
                      onChange={() => setNewProjectType('enterprise')}
                      style={{ width: '14px', height: '14px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600, color: t.text, fontSize: '13px' }}>Enterprise Forms</div>
                      <div style={{ fontSize: '12px', color: t.textMuted, marginTop: '2px' }}>Auto-discover forms, multi-path mapping</div>
                    </div>
                  </label>
                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    cursor: 'pointer',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    border: newProjectType === 'dynamic_content' ? `2px solid ${t.brand}` : `1px solid ${t.border}`,
                    background: newProjectType === 'dynamic_content' ? t.brandLight : 'transparent',
                    flex: 1
                  }}>
                    <input
                      type="radio"
                      name="projectType"
                      value="dynamic_content"
                      checked={newProjectType === 'dynamic_content'}
                      onChange={() => setNewProjectType('dynamic_content')}
                      style={{ width: '14px', height: '14px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600, color: t.text, fontSize: '13px' }}>Dynamic Content</div>
                      <div style={{ fontSize: '12px', color: t.textMuted, marginTop: '2px' }}>Manual test pages, natural language tests</div>
                    </div>
                  </label>
                </div>
              </div>
              )}
            </div>
            
            <div style={modalFooterStyle}>
              <button
                onClick={() => { setShowAddProjectModal(false); setNewProjectName(''); setNewProjectDescription(''); setNewProjectType('enterprise') }}
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
          <div style={{ ...modalContentStyle, maxWidth: '520px' }}>
            <div style={{ ...modalHeaderStyle, justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0, fontSize: '16px', color: t.text, fontWeight: 600 }}>Manage Projects</h2>
              <button onClick={() => setShowProjectsModal(false)} style={modalCloseStyle}>&times;</button>
            </div>
            
            <div style={{ padding: '0', maxHeight: '400px', overflow: 'auto' }}>
              {projects.length === 0 ? (
                <p style={{ color: t.textMuted, textAlign: 'center', padding: '32px', fontSize: '13px' }}>No projects yet</p>
              ) : (
                projects.map(project => (
                  <div key={project.id} style={projectListItemStyle}>
                    <div>
                      <strong style={{ color: t.text, fontSize: '14px' }}>{project.name}</strong>
                      {project.description && <p style={{ margin: '4px 0 0', fontSize: '12px', color: t.textMuted }}>{project.description}</p>}
                      <div style={{ fontSize: '12px', color: t.textMuted, marginTop: '4px' }}>
                        {project.network_count} networks &middot; {project.form_page_count} form pages
                      </div>
                    </div>
                    <button
                      onClick={() => { setProjectToDelete(project); setShowDeleteConfirm(true) }}
                      style={deleteIconBtnStyle}
                      title="Delete project"
                    >
                      Delete
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
            <div style={{ ...modalHeaderStyle, borderBottom: `2px solid ${t.dangerBorder}` }}>
              <h2 style={{ margin: 0, fontSize: '16px', color: t.danger, fontWeight: 600 }}>
                Delete Project?
              </h2>
            </div>
            <div style={{ padding: '20px' }}>
              <p style={{ color: t.textSecondary, fontSize: '14px', margin: '0 0 16px' }}>
                Are you sure you want to delete <strong style={{ color: t.text }}>{projectToDelete.name}</strong>?
              </p>
              <div style={warningBoxStyle}>
                <strong style={{ color: t.warning, fontSize: '13px' }}>This will permanently delete:</strong>
                <ul style={{ margin: '8px 0 0', paddingLeft: '18px', color: t.textSecondary, fontSize: '13px' }}>
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
              <h2 style={{ margin: 0, fontSize: '16px', color: t.text, fontWeight: 600 }}>
                {editingNetwork ? 'Edit Network' : 'Add Network'}
              </h2>
            </div>
            
            <div style={{ padding: '20px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Environment</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {(['qa', 'staging', 'production'] as const).map(type => (
                    <button
                      key={type}
                      onClick={() => !editingNetwork && setAddNetworkType(type)}
                      style={{
                        flex: 1,
                        padding: '8px',
                        border: addNetworkType === type ? `2px solid ${t.brand}` : `1px solid ${t.border}`,
                        borderRadius: '6px',
                        background: addNetworkType === type ? t.brandLight : 'transparent',
                        color: addNetworkType === type ? t.brand : t.textMuted,
                        cursor: editingNetwork ? 'not-allowed' : 'pointer',
                        fontWeight: 500,
                        fontSize: '13px',
                        textTransform: 'capitalize',
                        opacity: editingNetwork && addNetworkType !== type ? 0.4 : 1
                      }}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>
              
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Network Name *</label>
                <input
                  type="text"
                  value={networkName}
                  onChange={(e) => setNetworkName(e.target.value)}
                  placeholder="e.g., Main App, Admin Portal"
                  style={inputStyle}
                />
              </div>
              
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>URL *</label>
                <input
                  type="text"
                  value={networkUrl}
                  onChange={(e) => setNetworkUrl(e.target.value)}
                  placeholder="https://example.com"
                  style={inputStyle}
                />
              </div>
              
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Login Username (optional)</label>
                <input
                  type="text"
                  value={networkUsername}
                  onChange={(e) => {
                    setNetworkUsername(e.target.value)
                    setCredentialsChanged(prev => ({...prev, username: true}))
                  }}
                  placeholder={editingNetwork?.login_username ? "Configured (enter new to change)" : "Username for auto-login"}
                  style={inputStyle}
                />
              </div>
              
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Login Password (optional)</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={networkPassword}
                    onChange={(e) => {
                      setNetworkPassword(e.target.value)
                      setCredentialsChanged(prev => ({...prev, password: true}))
                    }}
                    placeholder={editingNetwork?.login_password ? "Configured (enter new to change)" : "Password for auto-login"}
                    style={{ ...inputStyle, paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (networkPassword !== '********') setShowPassword(!showPassword)
                    }}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: t.textMuted,
                      cursor: 'pointer',
                      fontSize: '12px',
                      display: networkPassword === '********' ? 'none' : 'block'
                    }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <div>
                <label style={labelStyle}>TOTP Secret (optional - for 2FA)</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showTotpSecret ? 'text' : 'password'}
                    value={totpSecret}
                    onChange={(e) => {
                      setTotpSecret(e.target.value)
                      setCredentialsChanged(prev => ({...prev, totp: true}))
                    }}
                    placeholder={editingNetwork?.totp_secret ? "Configured (enter new to change)" : "TOTP secret for 2FA"}
                    style={{ ...inputStyle, paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (totpSecret !== '********') setShowTotpSecret(!showTotpSecret)
                    }}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: t.textMuted,
                      cursor: 'pointer',
                      fontSize: '12px',
                      display: totpSecret === '********' ? 'none' : 'block'
                    }}
                  >
                    {showTotpSecret ? 'Hide' : 'Show'}
                  </button>
                </div>
                <p style={{ fontSize: '11px', color: t.textMuted, marginTop: '4px' }}>
                  Enter the TOTP secret key (not the QR code) for automated 2FA login
                </p>
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
            <div style={{ ...modalHeaderStyle, borderBottom: `2px solid ${t.dangerBorder}` }}>
              <h2 style={{ margin: 0, fontSize: '16px', color: t.danger, fontWeight: 600 }}>
                Delete Network?
              </h2>
            </div>
            <div style={{ padding: '20px' }}>
              <p style={{ color: t.textSecondary, fontSize: '14px', margin: 0 }}>
                Are you sure you want to delete <strong style={{ color: t.text }}>{networkToDelete.name}</strong>?
              </p>
              <p style={{ color: t.textMuted, fontSize: '13px', marginTop: '8px' }}>
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

const dropdownMenuStyle: React.CSSProperties = {
  position: 'absolute',
  top: 'calc(100% + 6px)',
  left: 0,
  background: t.cardBg,
  border: `1px solid ${t.border}`,
  borderRadius: '8px',
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
  minWidth: '260px',
  zIndex: 1000,
  overflow: 'hidden',
  animation: 'fadeIn 0.15s ease'
}

const dropdownHeaderStyle: React.CSSProperties = {
  padding: '10px 14px',
  fontSize: '11px',
  fontWeight: 600,
  color: t.textMuted,
  letterSpacing: '0.5px',
  borderBottom: `1px solid ${t.borderLight}`
}

const dropdownItemStyle: React.CSSProperties = {
  padding: '10px 14px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  color: t.text,
  fontSize: '13px',
  transition: 'all 0.1s ease'
}

const errorToastStyle: React.CSSProperties = {
  position: 'fixed',
  top: '70px',
  right: '24px',
  background: t.cardBg,
  color: t.danger,
  padding: '12px 16px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  zIndex: 1000,
  border: `1px solid ${t.dangerBorder}`,
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
  animation: 'fadeIn 0.2s ease',
  fontSize: '13px',
  fontWeight: 500
}

const successToastStyle: React.CSSProperties = {
  position: 'fixed',
  top: '70px',
  right: '24px',
  background: t.cardBg,
  color: t.success,
  padding: '12px 16px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  zIndex: 1000,
  border: `1px solid ${t.successBorder}`,
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
  animation: 'fadeIn 0.2s ease',
  fontSize: '13px',
  fontWeight: 500
}

const toastCloseStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: t.textMuted,
  width: '20px',
  height: '20px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '16px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginLeft: '4px'
}

const contentCardStyle: React.CSSProperties = {
  background: t.cardBg,
  borderRadius: '10px',
  padding: '24px',
  border: `1px solid ${t.border}`,
  boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
}

const infoBannerStyle: React.CSSProperties = {
  background: t.brandLight,
  border: `1px solid ${t.brandBorder}`,
  borderRadius: '8px',
  padding: '14px 16px',
  marginBottom: '20px',
}

const networkSectionStyle: React.CSSProperties = {
  background: t.cardBg,
  borderRadius: '8px',
  overflow: 'hidden',
  border: `1px solid ${t.border}`
}

const networkSectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  background: t.mutedBg,
  cursor: 'pointer',
  transition: 'all 0.15s ease'
}

const addBtnStyle: React.CSSProperties = {
  background: t.brand,
  color: '#fff',
  border: 'none',
  borderRadius: '4px',
  width: '24px',
  height: '24px',
  fontSize: '14px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}

const networkCardStyle: React.CSSProperties = {
  background: t.mutedBg,
  border: `1px solid ${t.border}`,
  borderRadius: '8px',
  padding: '14px',
  transition: 'all 0.15s ease'
}

const iconButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: `1px solid ${t.border}`,
  borderRadius: '4px',
  padding: '4px 8px',
  cursor: 'pointer',
  fontSize: '12px',
  color: t.textMuted,
  transition: 'all 0.15s ease'
}

const emptyTextStyle: React.CSSProperties = {
  color: t.textMuted,
  fontSize: '13px',
  textAlign: 'center',
  padding: '20px'
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
  padding: '20px',
  animation: 'fadeIn 0.15s ease'
}

const modalContentStyle: React.CSSProperties = {
  background: t.cardBg,
  borderRadius: '12px',
  width: '100%',
  maxWidth: '480px',
  border: `1px solid ${t.border}`,
  boxShadow: '0 16px 48px rgba(0,0,0,0.12)',
  overflow: 'hidden'
}

const modalHeaderStyle: React.CSSProperties = {
  padding: '16px 20px',
  borderBottom: `1px solid ${t.border}`,
  display: 'flex',
  alignItems: 'center'
}

const modalCloseStyle: React.CSSProperties = {
  background: t.mutedBg,
  border: `1px solid ${t.border}`,
  color: t.textMuted,
  width: '28px',
  height: '28px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '18px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.15s ease'
}

const modalFooterStyle: React.CSSProperties = {
  padding: '16px 20px',
  background: t.mutedBg,
  borderTop: `1px solid ${t.border}`,
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '8px'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '6px',
  fontWeight: 500,
  color: t.text,
  fontSize: '13px'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  border: `1px solid ${t.border}`,
  borderRadius: '6px',
  fontSize: '13px',
  boxSizing: 'border-box',
  background: t.cardBg,
  color: t.text,
  outline: 'none',
  transition: 'all 0.15s ease'
}

const primaryButtonStyle: React.CSSProperties = {
  background: t.brand,
  color: 'white',
  padding: '8px 16px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s ease'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: 'transparent',
  color: t.textSecondary,
  padding: '8px 16px',
  border: `1px solid ${t.border}`,
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s ease'
}

const dangerButtonStyle: React.CSSProperties = {
  background: t.danger,
  color: 'white',
  padding: '8px 16px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s ease'
}

const warningBoxStyle: React.CSSProperties = {
  background: t.warningBg,
  border: `1px solid ${t.warningBorder}`,
  padding: '14px',
  borderRadius: '8px'
}

const projectListItemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '14px 20px',
  borderBottom: `1px solid ${t.borderLight}`,
  transition: 'all 0.15s ease'
}

const deleteIconBtnStyle: React.CSSProperties = {
  background: t.dangerBg,
  border: `1px solid ${t.dangerBorder}`,
  borderRadius: '6px',
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: '12px',
  color: t.danger,
  transition: 'all 0.15s ease'
}
