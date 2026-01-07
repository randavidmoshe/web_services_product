'use client'
import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

interface InviteInfo {
  valid: boolean
  email?: string
  name?: string
  company_name?: string
  expired?: boolean
  already_accepted?: boolean
}

export default function AcceptInvitePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  
  const [loading, setLoading] = useState(true)
  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!token) {
      setError('Invalid invitation link. No token provided.')
      setLoading(false)
      return
    }
    
    // Fetch invitation info
    fetch(`/api/users/invite/${token}`)
      .then(res => res.json())
      .then(data => {
        setInviteInfo(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load invitation. Please try again.')
        setLoading(false)
      })
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    // Validate passwords
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    
    setSubmitting(true)
    
    try {
      const response = await fetch('/api/users/invite/accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          password
        })
      })
      
      const data = await response.json()
      
      if (response.ok) {
        setSuccess(true)
        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push('/login')
        }, 3000)
      } else {
        setError(data.detail || 'Failed to create account')
      }
    } catch {
      setError('Connection error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
            <p style={{ color: '#a0aec0', fontSize: '16px' }}>Loading invitation...</p>
          </div>
        </div>
      </div>
    )
  }

  // Success state
  if (success) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ 
              width: '80px', 
              height: '80px', 
              background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.2))',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              fontSize: '40px'
            }}>
              ✅
            </div>
            <h1 style={{ margin: '0 0 16px', fontSize: '28px', fontWeight: 700, color: '#fff' }}>
              Account Created!
            </h1>
            <p style={{ margin: '0 0 24px', color: '#a0aec0', fontSize: '16px', lineHeight: 1.6 }}>
              Your account has been set up successfully.<br />
              Redirecting you to login...
            </p>
            <button
              onClick={() => router.push('/login')}
              style={primaryButtonStyle}
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Invalid or expired invitation
  if (!inviteInfo?.valid) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ 
              width: '80px', 
              height: '80px', 
              background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.2))',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              fontSize: '40px'
            }}>
              {inviteInfo?.expired ? '⏰' : inviteInfo?.already_accepted ? '✓' : '❌'}
            </div>
            <h1 style={{ margin: '0 0 16px', fontSize: '28px', fontWeight: 700, color: '#fff' }}>
              {inviteInfo?.expired 
                ? 'Invitation Expired' 
                : inviteInfo?.already_accepted 
                  ? 'Already Accepted'
                  : 'Invalid Invitation'}
            </h1>
            <p style={{ margin: '0 0 24px', color: '#a0aec0', fontSize: '16px', lineHeight: 1.6 }}>
              {inviteInfo?.expired 
                ? 'This invitation link has expired. Please ask your admin to send a new invitation.'
                : inviteInfo?.already_accepted
                  ? 'This invitation has already been accepted. You can log in with your credentials.'
                  : error || 'This invitation link is invalid or has been revoked.'}
            </p>
            <button
              onClick={() => router.push('/login')}
              style={primaryButtonStyle}
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Valid invitation - show password form
  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ 
            width: '70px', 
            height: '70px', 
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 10px 40px rgba(99, 102, 241, 0.3)'
          }}>
            <span style={{ fontSize: '32px', fontWeight: 700, color: '#fff' }}>Q</span>
          </div>
          <h1 style={{ margin: '0 0 8px', fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            Welcome to Quattera!
          </h1>
          <p style={{ margin: '0', color: '#a0aec0', fontSize: '16px' }}>
            Set up your account to get started
          </p>
        </div>

        {/* User Info */}
        <div style={{
          background: 'rgba(99, 102, 241, 0.1)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '28px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              color: '#fff',
              fontWeight: 600
            }}>
              {inviteInfo.name?.charAt(0).toUpperCase()}
            </div>
            <div>
              <p style={{ margin: '0 0 4px', color: '#fff', fontWeight: 600, fontSize: '16px' }}>
                {inviteInfo.name}
              </p>
              <p style={{ margin: '0', color: '#a0aec0', fontSize: '14px' }}>
                {inviteInfo.email}
              </p>
            </div>
          </div>
          {inviteInfo.company_name && (
            <div style={{ 
              marginTop: '16px', 
              paddingTop: '16px', 
              borderTop: '1px solid rgba(99, 102, 241, 0.2)',
              color: '#a0aec0',
              fontSize: '14px'
            }}>
              Joining <strong style={{ color: '#fff' }}>{inviteInfo.company_name}</strong>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            padding: '14px 18px',
            borderRadius: '10px',
            marginBottom: '20px',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}

        {/* Password Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={labelStyle}>Create Password *</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
                placeholder="At least 8 characters"
                minLength={8}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '14px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: '#a0aec0',
                  cursor: 'pointer',
                  fontSize: '18px'
                }}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
          
          <div style={{ marginBottom: '28px' }}>
            <label style={labelStyle}>Confirm Password *</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              style={inputStyle}
              placeholder="Confirm your password"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={submitting}
            style={{
              ...primaryButtonStyle,
              width: '100%',
              opacity: submitting ? 0.7 : 1
            }}
          >
            {submitting ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        {/* Footer */}
        <p style={{ 
          margin: '24px 0 0', 
          textAlign: 'center', 
          color: '#64748b', 
          fontSize: '13px' 
        }}>
          By creating an account, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}

// Styles
const containerStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '24px',
  fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  backdropFilter: 'blur(20px)',
  borderRadius: '24px',
  padding: '40px',
  width: '100%',
  maxWidth: '440px',
  border: '1px solid rgba(255,255,255,0.1)',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#e2e8f0'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 18px',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '12px',
  fontSize: '16px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.1)',
  color: '#fff',
  outline: 'none'
}

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  padding: '16px 32px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.4)'
}
