'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Please enter your email')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() })
      })

      if (res.ok) {
        setSent(true)
      } else {
        setError('Something went wrong. Please try again.')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>🔐</div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#1e293b', margin: '0 0 8px' }}>
            Forgot Password?
          </h1>
          <p style={{ color: '#64748b', margin: 0, fontSize: '15px' }}>
            {sent ? "Check your email for reset instructions" : "No worries, we'll send you reset instructions"}
          </p>
        </div>

        {!sent ? (
          <form onSubmit={handleSubmit}>
            {error && <div style={errorStyle}>❌ {error}</div>}

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                style={inputStyle}
                autoFocus
              />
            </div>

            <button type="submit" disabled={loading} style={{ ...primaryButtonStyle, opacity: loading ? 0.6 : 1 }}>
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <div style={successBoxStyle}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>✉️</div>
              <p style={{ margin: 0, color: '#16a34a', fontWeight: 500 }}>
                If an account exists for <strong>{email}</strong>, you'll receive a password reset email shortly.
              </p>
            </div>
            <button onClick={() => { setSent(false); setEmail('') }} style={secondaryButtonStyle}>
              Try another email
            </button>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <button onClick={() => router.push('/login')} style={linkButtonStyle}>
            ← Back to Login
          </button>
        </div>
      </div>
    </div>
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

const secondaryButtonStyle: React.CSSProperties = {
  padding: '12px 24px',
  background: 'transparent',
  color: '#6366f1',
  border: '2px solid #e2e8f0',
  borderRadius: '10px',
  fontSize: '14px',
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