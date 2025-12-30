'use client'
import { useState } from 'react'
import Link from 'next/link'
import TwoFASetupModal from '@/components/TwoFASetupModal'

const QuatheraLogo = () => (
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
)

export default function WebAppLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [twoFACode, setTwoFACode] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // 2FA states
  const [requires2FA, setRequires2FA] = useState(false)
  const [pendingUserId, setPendingUserId] = useState<number | null>(null)
  const [pendingUserType, setPendingUserType] = useState<string>('')
  const [pendingCompanyId, setPendingCompanyId] = useState<number | null>(null)
  const [tempToken, setTempToken] = useState<string>('')
  const [show2FASetupModal, setShow2FASetupModal] = useState(false)

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
        
        // Check if 2FA verification is required
        if (data.requires_2fa) {
          setRequires2FA(true)
          setPendingUserId(data.user_id)
          setPendingUserType(data.type)
          setPendingCompanyId(data.company_id || null)
          setMessage('')
          setIsLoading(false)
          return
        }
        
        // Check if 2FA setup is required (for admins)
        if (data.requires_2fa_setup) {
          setTempToken(data.token)
          setPendingUserType(data.type)
          setPendingUserId(data.user_id)
          setPendingCompanyId(data.company_id || null)
          setShow2FASetupModal(true)
          setIsLoading(false)
          return
        }
        
        completeLogin(data)
      } else {
        setMessage('❌ Invalid credentials')
        setIsLoading(false)
      }
    } catch (error) {
      setMessage('❌ Connection error')
      setIsLoading(false)
    }
  }

  const handle2FAVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage('')
    setIsLoading(true)
    
    try {
      const response = await fetch('/api/2fa/verify-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: pendingUserId,
          user_type: pendingUserType,
          code: twoFACode
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        completeLogin(data)
      } else {
        const errorData = await response.json()
        setMessage(`❌ ${errorData.detail || 'Invalid code'}`)
        setTwoFACode('')
        setIsLoading(false)
      }
    } catch (error) {
      setMessage('❌ Connection error')
      setIsLoading(false)
    }
  }

  const completeLogin = (data: any) => {
    localStorage.setItem('token', data.token)
    localStorage.setItem('userType', data.type)
    localStorage.setItem('user_id', String(data.user_id))
    if (data.company_id) {
      localStorage.setItem('company_id', String(data.company_id))
    }
    setMessage('✅ Login successful!')
    setTimeout(() => window.location.href = '/dashboard', 1000)
  }

  const handle2FASetupSuccess = () => {
    setShow2FASetupModal(false)
    localStorage.setItem('token', tempToken)
    localStorage.setItem('userType', pendingUserType)
    if (pendingUserId) {
      localStorage.setItem('user_id', String(pendingUserId))
    }
    if (pendingCompanyId) {
      localStorage.setItem('company_id', String(pendingCompanyId))
    }
    setMessage('✅ 2FA enabled! Redirecting...')
    setTimeout(() => window.location.href = '/dashboard', 1000)
  }

  const resetLogin = () => {
    setRequires2FA(false)
    setTwoFACode('')
    setPendingUserId(null)
    setPendingUserType('')
    setPendingCompanyId(null)
    setMessage('')
  }

  return (
    <div style={{
      minHeight: '100vh',
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
    }}>
      {/* Background */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: '#0A0E17' }} />
      
      {/* Grid Pattern */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: 'linear-gradient(rgba(0, 245, 212, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 245, 212, 0.03) 1px, transparent 1px)',
        backgroundSize: '60px 60px', pointerEvents: 'none'
      }} />
      
      {/* Gradient Orbs */}
      <div style={{ position: 'absolute', top: '-20%', right: '-10%', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(0, 187, 249, 0.15) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-30%', left: '-10%', width: '800px', height: '800px', background: 'radial-gradient(circle, rgba(155, 93, 229, 0.1) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
      
      {/* Content */}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 20px' }}>
        <div style={{ marginBottom: '8px' }}><QuatheraLogo /></div>
        <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '16px', marginBottom: '40px', letterSpacing: '1px' }}>
          AI-Powered Form Testing Platform
        </p>
        
        {/* Login Card */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.95)',
          borderRadius: '20px',
          padding: '48px',
          width: '100%',
          maxWidth: '420px',
          boxShadow: '0 25px 80px rgba(0, 0, 0, 0.4)'
        }}>
          {!requires2FA ? (
            <>
              <h2 style={{ margin: '0 0 8px', fontSize: '28px', fontWeight: 700, color: '#0A0E17', textAlign: 'center' }}>Welcome Back</h2>
              <p style={{ margin: '0 0 32px', fontSize: '15px', color: '#64748b', textAlign: 'center' }}>Sign in to your account</p>
              
              <form onSubmit={handleLogin}>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#374151' }}>Email</label>
                  <input
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{
                      width: '100%', padding: '14px 18px', border: '2px solid #e5e7eb', borderRadius: '10px',
                      fontSize: '16px', boxSizing: 'border-box', outline: 'none'
                    }}
                    required
                    disabled={isLoading}
                  />
                </div>
                
                <div style={{ marginBottom: '28px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#374151' }}>Password</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={{
                      width: '100%', padding: '14px 18px', border: '2px solid #e5e7eb', borderRadius: '10px',
                      fontSize: '16px', boxSizing: 'border-box', outline: 'none'
                    }}
                    required
                    disabled={isLoading}
                  />
                </div>
                
                <button
                  type="submit"
                  style={{
                    width: '100%', padding: '16px',
                    background: isLoading ? '#94a3b8' : 'linear-gradient(135deg, #0A0E17 0%, #1e293b 100%)',
                    color: 'white', border: 'none', borderRadius: '10px', fontSize: '16px', fontWeight: 600,
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 20px rgba(10, 14, 23, 0.3)'
                  }}
                  disabled={isLoading}
                >
                  {isLoading ? 'Signing in...' : 'Sign In'}
                </button>
              </form>
            </>
          ) : (
            <>
              <h2 style={{ margin: '0 0 8px', fontSize: '28px', fontWeight: 700, color: '#0A0E17', textAlign: 'center' }}>
                🔐 Two-Factor Authentication
              </h2>
              <p style={{ margin: '0 0 32px', fontSize: '15px', color: '#64748b', textAlign: 'center' }}>
                Enter the 6-digit code from your authenticator app
              </p>
              
              <form onSubmit={handle2FAVerify}>
                <div style={{ marginBottom: '28px' }}>
                  <input
                    type="text"
                    maxLength={6}
                    placeholder="000000"
                    value={twoFACode}
                    onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, ''))}
                    style={{
                      width: '100%', padding: '20px', fontSize: '32px', textAlign: 'center',
                      letterSpacing: '12px', border: '2px solid #e5e7eb', borderRadius: '10px',
                      boxSizing: 'border-box', outline: 'none', fontFamily: 'monospace'
                    }}
                    autoFocus
                    disabled={isLoading}
                  />
                </div>
                
                <button
                  type="submit"
                  style={{
                    width: '100%', padding: '16px',
                    background: isLoading || twoFACode.length !== 6 ? '#94a3b8' : 'linear-gradient(135deg, #0A0E17 0%, #1e293b 100%)',
                    color: 'white', border: 'none', borderRadius: '10px', fontSize: '16px', fontWeight: 600,
                    cursor: isLoading || twoFACode.length !== 6 ? 'not-allowed' : 'pointer'
                  }}
                  disabled={isLoading || twoFACode.length !== 6}
                >
                  {isLoading ? 'Verifying...' : 'Verify'}
                </button>
              </form>
              
              <button
                onClick={resetLogin}
                style={{
                  width: '100%', marginTop: '16px', padding: '12px',
                  background: 'transparent', color: '#64748b',
                  border: '1px solid #e5e7eb', borderRadius: '10px',
                  fontSize: '14px', cursor: 'pointer'
                }}
              >
                ← Back to login
              </button>
            </>
          )}
          
          {message && (
            <div style={{
              marginTop: '20px', padding: '14px', textAlign: 'center', borderRadius: '10px',
              background: message.includes('✅') ? '#d1fae5' : '#fee2e2',
              color: message.includes('✅') ? '#059669' : '#dc2626',
              fontSize: '14px'
            }}>
              {message}
            </div>
          )}
          
          {!requires2FA && (
            <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px', color: '#64748b' }}>
              <Link href="/forgot-password" style={{ color: '#00BBF9', textDecoration: 'none', fontWeight: 500 }}>
                Forgot your password?
              </Link>
            </p>
          )}
        </div>
        
        {!requires2FA && (
          <p style={{ marginTop: '32px', color: 'rgba(255, 255, 255, 0.7)', fontSize: '15px' }}>
            Don't have an account?{' '}
            <Link href="/signup" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 600 }}>
              Start Free Trial
            </Link>
          </p>
        )}
      </div>

      <TwoFASetupModal
        isOpen={show2FASetupModal}
        onClose={() => setShow2FASetupModal(false)}
        onSuccess={handle2FASetupSuccess}
        token={tempToken}
        isMandatory={pendingUserType === 'admin'}
      />
    </div>
  )
}
