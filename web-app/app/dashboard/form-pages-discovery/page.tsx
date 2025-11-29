'use client'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

interface Project {
  id: number
  name: string
}

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
}

interface NetworksByType {
  qa: Network[]
  staging: Network[]
  production: Network[]
}

interface DiscoveredForm {
  id: number
  form_name: string
  url: string
  navigation_steps: any[]
  is_root: boolean
  created_at: string
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
  forms: DiscoveredForm[]
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
  'UNKNOWN': '❓ Unknown error occurred'
}

const getErrorMessage = (errorCode: string | null, errorMessage: string | null): string => {
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }
  return errorMessage || 'Discovery failed'
}

export default function FormDiscoveryPage() {
  const searchParams = useSearchParams()
  
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [companyId, setCompanyId] = useState<string | null>(null)
  
  // Projects
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(true)
  
  // Networks
  const [networks, setNetworks] = useState<Network[]>([])
  const [selectedNetworkId, setSelectedNetworkId] = useState<number | null>(null)
  const [loadingNetworks, setLoadingNetworks] = useState(false)
  
  // Discovery settings
  const [maxDepth, setMaxDepth] = useState(20)
  const [maxFormPages, setMaxFormPages] = useState(50)
  const [headless, setHeadless] = useState(false)
  const [slowMode, setSlowMode] = useState(true)
  
  // Discovery status
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    const storedCompanyId = localStorage.getItem('company_id')
    
    if (!storedToken) {
      window.location.href = '/login'
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
    setCompanyId(storedCompanyId)
    
    // Load projects
    if (storedCompanyId) {
      loadProjects(storedCompanyId, storedToken)
    }
  }, [])

  // Handle URL query params for pre-selection
  useEffect(() => {
    const projectIdParam = searchParams.get('project_id')
    const networkIdParam = searchParams.get('network_id')
    
    if (projectIdParam) {
      const projectId = parseInt(projectIdParam)
      setSelectedProjectId(projectId)
      
      // Load networks for this project
      if (token) {
        loadNetworks(projectId, token, networkIdParam ? parseInt(networkIdParam) : null)
      }
    }
  }, [searchParams, token])

  // Poll for status when discovering
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (isDiscovering && sessionId) {
      interval = setInterval(() => {
        pollStatus(sessionId)
      }, 3000)
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isDiscovering, sessionId])

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
      }
    } catch (err) {
      console.error('Failed to load projects:', err)
    } finally {
      setLoadingProjects(false)
    }
  }

  const loadNetworks = async (projectId: number, authToken: string, preSelectNetworkId: number | null = null) => {
    setLoadingNetworks(true)
    setNetworks([])
    setSelectedNetworkId(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data: NetworksByType = await response.json()
        // Flatten networks from all types into a single array
        const allNetworks = [
          ...data.qa.map(n => ({ ...n, network_type: 'qa' })),
          ...data.staging.map(n => ({ ...n, network_type: 'staging' })),
          ...data.production.map(n => ({ ...n, network_type: 'production' }))
        ]
        setNetworks(allNetworks)
        
        // Pre-select network if provided
        if (preSelectNetworkId && allNetworks.some(n => n.id === preSelectNetworkId)) {
          setSelectedNetworkId(preSelectNetworkId)
        }
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const handleProjectChange = (projectId: number | null) => {
    setSelectedProjectId(projectId)
    setSelectedNetworkId(null)
    setNetworks([])
    
    if (projectId && token) {
      loadNetworks(projectId, token)
    }
  }

  const startDiscovery = async () => {
    if (!selectedProjectId) {
      setError('Please select a project')
      return
    }
    if (!selectedNetworkId || !userId) {
      setError('Please select a network')
      return
    }
    
    setError(null)
    setMessage(null)
    setIsDiscovering(true)
    
    try {
      const params = new URLSearchParams({
        user_id: userId,
        max_depth: maxDepth.toString(),
        headless: headless.toString(),
        slow_mode: slowMode.toString()
      })
      
      if (maxFormPages) {
        params.append('max_form_pages', maxFormPages.toString())
      }
      
      const response = await fetch(
        `/api/form-pages/networks/${selectedNetworkId}/locate?${params}`,
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
        setSessionId(data.crawl_session_id)
        setMessage(`Discovery started! Task ID: ${data.task_id}`)
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to start discovery')
        setIsDiscovering(false)
      }
    } catch (err) {
      setError('Connection error. Is your agent running?')
      setIsDiscovering(false)
    }
  }

  const pollStatus = async (sessionId: number) => {
    try {
      const response = await fetch(
        `/api/form-pages/sessions/${sessionId}/status`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      
      if (response.ok) {
        const data: SessionStatus = await response.json()
        setStatus(data)
        
        // Stop polling if completed or failed
        if (data.session.status === 'completed' || data.session.status === 'failed') {
          setIsDiscovering(false)
          if (data.session.status === 'completed') {
            setMessage(`Discovery completed! Found ${data.session.forms_found} forms.`)
          } else {
            setError(getErrorMessage(data.session.error_code, data.session.error_message))
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll status:', err)
    }
  }

  const getNetworkTypeLabel = (type: string) => {
    switch (type) {
      case 'qa': return 'QA'
      case 'staging': return 'Staging'
      case 'production': return 'Production'
      default: return type
    }
  }

  if (!token) return <p>Loading...</p>

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>🔍 Form Discovery</h1>
        <button 
          onClick={() => window.location.href = '/dashboard'}
          style={secondaryButtonStyle}
        >
          ← Back to Dashboard
        </button>
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

      {/* No Projects Warning */}
      {!loadingProjects && projects.length === 0 && (
        <div style={warningBoxStyle}>
          <h3 style={{ marginTop: 0 }}>No Projects Found</h3>
          <p>You need to create a project and add networks before you can start form discovery.</p>
          <button 
            onClick={() => window.location.href = '/dashboard/projects'}
            style={primaryButtonStyle}
          >
            Go to Projects
          </button>
        </div>
      )}

      {/* Configuration Section */}
      {projects.length > 0 && (
        <div style={cardStyle}>
          <h2>Configuration</h2>
          
          {/* Project Selection */}
          <div style={{ marginTop: '20px' }}>
            <label style={labelStyle}>Select Project: *</label>
            <select
              value={selectedProjectId || ''}
              onChange={(e) => handleProjectChange(e.target.value ? Number(e.target.value) : null)}
              style={selectStyle}
              disabled={isDiscovering || loadingProjects}
            >
              <option value="">-- Select a project --</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          {/* Network Selection */}
          <div style={{ marginTop: '20px' }}>
            <label style={labelStyle}>Select Network: *</label>
            <select
              value={selectedNetworkId || ''}
              onChange={(e) => setSelectedNetworkId(e.target.value ? Number(e.target.value) : null)}
              style={selectStyle}
              disabled={isDiscovering || !selectedProjectId || loadingNetworks}
            >
              <option value="">
                {!selectedProjectId 
                  ? '-- Select a project first --' 
                  : loadingNetworks 
                    ? 'Loading networks...' 
                    : networks.length === 0 
                      ? '-- No networks in this project --'
                      : '-- Select a network --'
                }
              </option>
              {networks.map(network => (
                <option key={network.id} value={network.id}>
                  [{getNetworkTypeLabel(network.network_type)}] {network.name} ({network.url})
                </option>
              ))}
            </select>
            {selectedProjectId && networks.length === 0 && !loadingNetworks && (
              <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#666' }}>
                No networks found. <a href={`/dashboard/projects/${selectedProjectId}`} style={{ color: '#0070f3' }}>Add networks to this project</a>
              </p>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
            <div>
              <label style={labelStyle}>Max Depth:</label>
              <input
                type="number"
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                style={inputStyle}
                disabled={isDiscovering}
                min={1}
                max={50}
              />
            </div>
            <div>
              <label style={labelStyle}>Max Form Pages:</label>
              <input
                type="number"
                value={maxFormPages}
                onChange={(e) => setMaxFormPages(Number(e.target.value))}
                style={inputStyle}
                disabled={isDiscovering}
                min={1}
                max={200}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '30px', marginTop: '20px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={headless}
                onChange={(e) => setHeadless(e.target.checked)}
                disabled={isDiscovering}
              />
              Headless Mode
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={slowMode}
                onChange={(e) => setSlowMode(e.target.checked)}
                disabled={isDiscovering}
              />
              Slow Mode (for observation)
            </label>
          </div>

          <div style={{ marginTop: '30px' }}>
            <button
              onClick={startDiscovery}
              disabled={isDiscovering || !selectedProjectId || !selectedNetworkId}
              style={{
                ...primaryButtonStyle,
                opacity: (isDiscovering || !selectedProjectId || !selectedNetworkId) ? 0.6 : 1,
                cursor: (isDiscovering || !selectedProjectId || !selectedNetworkId) ? 'not-allowed' : 'pointer'
              }}
            >
              {isDiscovering ? '🔄 Discovering...' : '🚀 Start Discovery'}
            </button>
          </div>
        </div>
      )}

      {/* Status Section */}
      {status && (
        <div style={{ ...cardStyle, marginTop: '30px' }}>
          <h2>Discovery Status</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginTop: '20px' }}>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Status</div>
              <div style={{ 
                ...statValueStyle, 
                color: status.session.status === 'completed' ? 'green' : 
                       status.session.status === 'failed' ? 'red' : 
                       status.session.status === 'running' ? 'orange' : '#666'
              }}>
                {status.session.status.toUpperCase()}
              </div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Pages Crawled</div>
              <div style={statValueStyle}>{status.session.pages_crawled}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Forms Found</div>
              <div style={statValueStyle}>{status.session.forms_found}</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statLabelStyle}>Started</div>
              <div style={{ ...statValueStyle, fontSize: '14px' }}>
                {status.session.started_at ? new Date(status.session.started_at).toLocaleTimeString() : '-'}
              </div>
            </div>
          </div>

          {/* Progress bar */}
          {status.session.status === 'running' && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ background: '#e0e0e0', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                <div style={{
                  background: '#0070f3',
                  height: '100%',
                  width: `${Math.min((status.session.forms_found / maxFormPages) * 100, 100)}%`,
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Results Table */}
      {status && status.forms.length > 0 && (
        <div style={{ ...cardStyle, marginTop: '30px' }}>
          <h2>Discovered Forms ({status.forms.length})</h2>
          
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
              {status.forms.map(form => (
                <tr key={form.id}>
                  <td style={tdStyle}>
                    <strong>{form.form_name}</strong>
                  </td>
                  <td style={tdStyle}>
                    <a href={form.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>
                      {form.url.length > 50 ? form.url.substring(0, 50) + '...' : form.url}
                    </a>
                  </td>
                  <td style={tdStyle}>{form.navigation_steps?.length || 0}</td>
                  <td style={tdStyle}>
                    <span style={{
                      background: form.is_root ? '#e3f2fd' : '#fff3e0',
                      color: form.is_root ? '#1565c0' : '#e65100',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '12px'
                    }}>
                      {form.is_root ? 'Root' : 'Child'}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    {form.created_at ? new Date(form.created_at).toLocaleString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Styles
const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: '8px',
  padding: '24px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
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
  fontSize: '14px'
}

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  fontSize: '14px',
  background: '#fff'
}

const primaryButtonStyle: React.CSSProperties = {
  background: '#0070f3',
  color: 'white',
  padding: '12px 24px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '16px',
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
  padding: '24px',
  borderRadius: '8px',
  marginBottom: '20px',
  textAlign: 'center'
}

const statBoxStyle: React.CSSProperties = {
  background: '#f9f9f9',
  padding: '16px',
  borderRadius: '6px',
  textAlign: 'center'
}

const statLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#666',
  marginBottom: '4px'
}

const statValueStyle: React.CSSProperties = {
  fontSize: '24px',
  fontWeight: 600,
  color: '#333'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  marginTop: '20px'
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
