'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

function ResetPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const urlToken = searchParams.get('token')
    if (urlToken) setToken(urlToken)
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!token) { setError('Invalid reset link'); return }
    if (!password.trim()) { setError('Please enter a new password'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (password !== confirmPassword) { setError('Passwords do not match'); return }

    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password })
      })

      const data = await res.json()
      if (res.ok) {
        setSuccess(true)
      } else {
        setError(data.detail || 'Failed to reset password')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1e293b', margin: '0 0 12px' }}>
              Invalid Reset Link
            </h1>
            <p style={{ color: '#64748b', marginBottom: '24px' }}>
              This password reset link is invalid or has expired.
            </p>
            <button onClick={() => router.push('/forgot-password')} style={primaryButtonStyle}>
              Request New Link
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>🔑</div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#1e293b', margin: '0 0 8px' }}>
            {success ? 'Password Updated!' : 'Create New Password'}
          </h1>
          <p style={{ color: '#64748b', margin: 0, fontSize: '15px' }}>
            {success ? 'You can now login with your new password' : 'Enter your new password below'}
          </p>
        </div>

        {!success ? (
          <form onSubmit={handleSubmit}>
            {error && <div style={errorStyle}>❌ {error}</div>}

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>New Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                style={inputStyle}
                autoFocus
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                style={inputStyle}
              />
            </div>

            <button type="submit" disabled={loading} style={{ ...primaryButtonStyle, opacity: loading ? 0.6 : 1 }}>
              {loading ? 'Updating...' : 'Reset Password'}
            </button>
          </form>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <div style={successBoxStyle}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>✅</div>
              <p style={{ margin: 0, color: '#16a34a', fontWeight: 500 }}>
                Your password has been successfully updated!
              </p>
            </div>
            <button onClick={() => router.push('/login')} style={primaryButtonStyle}>
              Go to Login
            </button>
          </div>
        )}

        {!success && (
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button onClick={() => router.push('/login')} style={linkButtonStyle}>
              ← Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div style={containerStyle}><div style={cardStyle}>Loading...</div></div>}>
      <ResetPasswordContent />
    </Suspense>
  )
}

const containerStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '40px 20px'
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.98)',
  borderRadius: '24px',
  padding: '48px',
  width: '100%',
  maxWidth: '420px',
  boxShadow: '0 25px 80px rgba(0, 0, 0, 0.4)'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '14px',
  fontWeight: 600,
  color: '#374151',
  marginBottom: '8px'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 18px',
  border: '2px solid #e2e8f0',
  borderRadius: '10px',
  fontSize: '16px',
  boxSizing: 'border-box',
  outline: 'none'
}

const primaryButtonStyle: React.CSSProperties = {
  width: '100%',
  padding: '16px',
  background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
  color: 'white',
  border: 'none',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer'
}

const linkButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#6366f1',
  fontSize: '14px',
  fontWeight: 500,
  cursor: 'pointer'
}

const errorStyle: React.CSSProperties = {
  background: '#fef2f2',
  color: '#dc2626',
  padding: '12px 16px',
  borderRadius: '10px',
  marginBottom: '20px',
  fontSize: '14px'
}

const successBoxStyle: React.CSSProperties = {
  background: '#f0fdf4',
  border: '1px solid #bbf7d0',
  borderRadius: '12px',
  padding: '24px',
  marginBottom: '20px'
}