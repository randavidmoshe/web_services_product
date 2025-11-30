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
      const response = await fetch('/api/auth/login', {
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
          <svg width="280" height="70" viewBox="150 180 700 140" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="circuitGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
                <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
                <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
              </linearGradient>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            <g transform="translate(500, 250)">
              {/* Q Icon */}
              <g transform="translate(-280, 0)">
                <polygon points="0,-75 65,-37.5 65,37.5 0,75 -65,37.5 -65,-37.5" 
                         fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2"/>
                <circle cx="0" cy="0" r="52" fill="none" stroke="url(#circuitGradient)" strokeWidth="5" filter="url(#glow)"/>
                <g stroke="url(#circuitGradient)" strokeWidth="3" fill="none" strokeLinecap="round" filter="url(#glow)">
                  <path d="M -35 -20 Q -42 0 -38 20 Q -30 42 0 48 Q 30 42 38 20 Q 42 0 35 -20 Q 25 -42 0 -45 Q -25 -42 -35 -20"/>
                  <path d="M -20 -10 Q -25 5 -18 18 Q -5 28 12 22 Q 25 12 22 -5 Q 18 -22 0 -25 Q -15 -22 -20 -10" opacity="0.6"/>
                  <path d="M 25 30 L 50 55 L 65 50"/>
                  <circle cx="65" cy="50" r="4" fill="url(#circuitGradient)"/>
                </g>
                <g fill="url(#circuitGradient)" filter="url(#glow)">
                  <circle cx="-38" cy="-18" r="4"/>
                  <circle cx="-40" cy="18" r="4"/>
                  <circle cx="0" cy="48" r="4"/>
                  <circle cx="38" cy="18" r="4"/>
                  <circle cx="38" cy="-18" r="4"/>
                  <circle cx="0" cy="-45" r="4"/>
                  <circle cx="-30" cy="-35" r="3"/>
                  <circle cx="30" cy="-35" r="3"/>
                </g>
                <circle cx="0" cy="0" r="8" fill="#0A0E17" stroke="url(#circuitGradient)" strokeWidth="2"/>
                <circle cx="0" cy="0" r="3" fill="url(#circuitGradient)" opacity="0.8"/>
              </g>
              
              {/* Quathera Text */}
              <g transform="translate(-180, 0)">
                <text x="0" y="18" 
                      fontFamily="'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif" 
                      fontSize="82" 
                      fontWeight="300" 
                      fill="#FFFFFF" 
                      letterSpacing="6">
                  <tspan fill="url(#circuitGradient)" fontWeight="600">Q</tspan>uathera
                </text>
              </g>
            </g>
          </svg>
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
  background: 'linear-gradient(135deg, rgba(10, 14, 23, 0.9) 0%, rgba(15, 21, 32, 0.8) 100%)'
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
  background: 'linear-gradient(135deg, #0A0E17 0%, #1a2535 100%)',
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
