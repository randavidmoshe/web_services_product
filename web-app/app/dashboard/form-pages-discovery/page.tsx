'use client'
import { useEffect, useState } from 'react'

interface Network {
  id: number
  name: string
  url: string
  login_username: string
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
    started_at: string | null
    completed_at: string | null
  }
  forms: DiscoveredForm[]
}

export default function FormDiscoveryPage() {
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [companyId, setCompanyId] = useState<string | null>(null)
  
  // Networks
  const [networks, setNetworks] = useState<Network[]>([])
  const [selectedNetworkId, setSelectedNetworkId] = useState<number | null>(null)
  const [loadingNetworks, setLoadingNetworks] = useState(true)
  
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
    
    // Load networks
    if (storedCompanyId) {
      loadNetworks(storedCompanyId)
    }
  }, [])

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

  const loadNetworks = async (companyId: string) => {
    try {
      const response = await fetch(
        `http://localhost:8001/api/projects?company_id=${companyId}`,
        { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } }
      )
      
      if (response.ok) {
        const projects = await response.json()
        // For now, create a mock network list or load from projects
        // TODO: Add proper networks endpoint
        setNetworks([
          { id: 1, name: 'OrangeHRM Demo', url: 'https://opensource-demo.orangehrmlive.com', login_username: 'Admin' }
        ])
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const startDiscovery = async () => {
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
        `http://localhost:8001/api/form-pages/networks/${selectedNetworkId}/locate?${params}`,
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
        `http://localhost:8001/api/form-pages/sessions/${sessionId}/status`,
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
            setError(data.session.error_message || 'Discovery failed')
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll status:', err)
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
        </div>
      )}
      {message && (
        <div style={successBoxStyle}>
          ✅ {message}
        </div>
      )}

      {/* Configuration Section */}
      <div style={cardStyle}>
        <h2>Configuration</h2>
        
        <div style={{ marginTop: '20px' }}>
          <label style={labelStyle}>Select Network:</label>
          <select
            value={selectedNetworkId || ''}
            onChange={(e) => setSelectedNetworkId(Number(e.target.value))}
            style={selectStyle}
            disabled={isDiscovering}
          >
            <option value="">-- Select a network --</option>
            {networks.map(network => (
              <option key={network.id} value={network.id}>
                {network.name} ({network.url})
              </option>
            ))}
          </select>
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
            disabled={isDiscovering || !selectedNetworkId}
            style={{
              ...primaryButtonStyle,
              opacity: (isDiscovering || !selectedNetworkId) ? 0.6 : 1,
              cursor: (isDiscovering || !selectedNetworkId) ? 'not-allowed' : 'pointer'
            }}
          >
            {isDiscovering ? '🔄 Discovering...' : '🚀 Start Discovery'}
          </button>
        </div>
      </div>

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

const errorBoxStyle: React.CSSProperties = {
  background: '#ffebee',
  color: '#c62828',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px'
}

const successBoxStyle: React.CSSProperties = {
  background: '#e8f5e9',
  color: '#2e7d32',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px'
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
