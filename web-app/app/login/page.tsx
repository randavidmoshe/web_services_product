'use client'
import { useState } from 'react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage('')
    setIsLoading(true)
    
    try {
      const response = await fetch('http://localhost:8001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('token', data.token)
        localStorage.setItem('userType', data.type)
        localStorage.setItem('user_id', data.user_id)
        if (data.company_id) {
          localStorage.setItem('company_id', data.company_id)
        }
        setMessage('✅ Login successful!')
        setTimeout(() => window.location.href = '/dashboard', 1000)
      } else {
        setMessage('❌ Invalid credentials')
        setIsLoading(false)
      }
    } catch (error) {
      setMessage('❌ Connection error')
      setIsLoading(false)
    }
  }

  return (
    <div style={containerStyle}>
      {/* Background Image */}
      <div style={backgroundStyle} />
      
      {/* Overlay */}
      <div style={overlayStyle} />
      
      {/* Content */}
      <div style={contentStyle}>
        {/* Logo */}
        <div style={logoContainerStyle}>
          <span style={logoTextStyle}>QUATHERA</span>
          <span style={logoDotStyle}>.COM</span>
        </div>
        
        {/* Tagline */}
        <p style={taglineStyle}>AI-Powered Form Discovery Platform</p>
        
        {/* Login Card */}
        <div style={cardStyle}>
          <h2 style={cardTitleStyle}>Welcome Back</h2>
          <p style={cardSubtitleStyle}>Sign in to your account</p>
          
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Email</label>
              <input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
                required
                disabled={isLoading}
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
                required
                disabled={isLoading}
              />
            </div>
            
            <button
              type="submit"
              style={{
                ...buttonStyle,
                opacity: isLoading ? 0.7 : 1,
                cursor: isLoading ? 'not-allowed' : 'pointer'
              }}
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          
          {message && (
            <div style={{
              marginTop: '20px',
              padding: '12px',
              textAlign: 'center',
              borderRadius: '6px',
              background: message.includes('✅') ? '#e8f5e9' : '#ffebee',
              color: message.includes('✅') ? '#2e7d32' : '#c62828'
            }}>
              {message}
            </div>
          )}
        </div>
        
        {/* Test Accounts */}
        <div style={testAccountsStyle}>
          <p style={{ margin: '0 0 8px', fontWeight: 600 }}>Test Accounts:</p>
          <p style={{ margin: '4px 0' }}>admin@acme.com / admin123</p>
          <p style={{ margin: '4px 0' }}>user@acme.com / user123</p>
        </div>
      </div>
    </div>
  )
}

// Styles
const containerStyle: React.CSSProperties = {
  minHeight: '100vh',
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}

const backgroundStyle: React.CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundImage: 'url(https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80)',
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  backgroundRepeat: 'no-repeat'
}

const overlayStyle: React.CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'linear-gradient(135deg, rgba(26, 26, 46, 0.85) 0%, rgba(22, 33, 62, 0.75) 100%)'
}

const contentStyle: React.CSSProperties = {
  position: 'relative',
  zIndex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '40px 20px'
}

const logoContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: '8px'
}

const logoTextStyle: React.CSSProperties = {
  fontSize: '36px',
  fontWeight: 700,
  color: '#fff',
  letterSpacing: '6px'
}

const logoDotStyle: React.CSSProperties = {
  fontSize: '36px',
  fontWeight: 700,
  color: '#4da8da',
  letterSpacing: '6px'
}

const taglineStyle: React.CSSProperties = {
  color: 'rgba(255, 255, 255, 0.7)',
  fontSize: '16px',
  marginBottom: '40px',
  letterSpacing: '1px'
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.95)',
  borderRadius: '16px',
  padding: '40px',
  width: '100%',
  maxWidth: '400px',
  boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
}

const cardTitleStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '24px',
  fontWeight: 700,
  color: '#1a1a2e',
  textAlign: 'center'
}

const cardSubtitleStyle: React.CSSProperties = {
  margin: '0 0 30px',
  fontSize: '14px',
  color: '#666',
  textAlign: 'center'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontSize: '14px',
  fontWeight: 500,
  color: '#333'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  border: '2px solid #e0e0e0',
  borderRadius: '8px',
  fontSize: '16px',
  transition: 'border-color 0.2s',
  boxSizing: 'border-box',
  outline: 'none'
}

const buttonStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px',
  background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'transform 0.2s, box-shadow 0.2s'
}

const testAccountsStyle: React.CSSProperties = {
  marginTop: '30px',
  padding: '16px 24px',
  background: 'rgba(255, 255, 255, 0.1)',
  borderRadius: '8px',
  color: 'rgba(255, 255, 255, 0.8)',
  fontSize: '13px',
  textAlign: 'center'
}
