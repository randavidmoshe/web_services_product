'use client'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    
    if (!storedToken) {
      window.location.href = '/login'
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
  }, [])

  if (!token) return <p>Loading...</p>

  return (
    <div style={{ padding: '40px' }}>
      <h1>Dashboard</h1>
      
      <div style={{ marginTop: '30px' }}>
        <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h2>🔍 Form Discovery</h2>
          <p>Discover all form pages in your web application automatically using AI</p>
          <button 
            onClick={() => window.location.href = '/dashboard/form-pages-discovery'}
            style={buttonStyle}
          >
            Start Form Discovery
          </button>
        </div>

        <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h2>🎯 Projects</h2>
          <p>Create and manage your testing projects</p>
          <button style={buttonStyle}>Create Project</button>
        </div>

        <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h2>🤖 Download Agent</h2>
          <p>Download the desktop agent to start testing</p>
          <button 
            onClick={() => window.open('http://localhost:8001/api/installer/download/linux', '_blank')}
            style={buttonStyle}
          >
            Download Agent (Linux)
          </button>
        </div>

        <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h2>📊 Results</h2>
          <p>View your form discovery results</p>
          <button style={buttonStyle}>View Results</button>
        </div>
      </div>

      <div style={{ marginTop: '30px' }}>
        <button 
          onClick={() => {
            localStorage.clear()
            window.location.href = '/login'
          }}
          style={{ ...buttonStyle, background: '#dc3545' }}
        >
          Logout
        </button>
      </div>
    </div>
  )
}

const buttonStyle = {
  background: '#0070f3',
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  marginTop: '10px'
}
