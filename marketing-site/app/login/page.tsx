'use client'
import { useState } from 'react'
import Link from 'next/link'
import config from '../../config'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      const response = await fetch(`${config.apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed')
      }
      
      // Redirect to dashboard with auth data in URL
      // The web app will read these params and store them
      const params = new URLSearchParams({
        token: data.token,
        user_id: data.user_id.toString(),
        company_id: data.company_id.toString(),
        type: data.type
      })
      window.open(`${config.appUrl}/dashboard?${params.toString()}`, '_blank'); window.location.href = '/'
      
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
      {/* Navigation */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 60px',
        background: '#fff',
        borderBottom: '1px solid #eee'
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '28px' }}>🔷</span>
          <span style={{ fontSize: '24px', fontWeight: 700, color: '#1a1a2e' }}>QUATHERA</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <span style={{ color: '#64748b' }}>Don't have an account?</span>
          <Link href="/signup" style={{
            background: '#2563eb',
            color: '#fff',
            padding: '10px 24px',
            borderRadius: '8px',
            fontWeight: 600
          }}>
            Sign Up
          </Link>
        </div>
      </nav>

      {/* Login Form */}
      <div style={{
        maxWidth: '400px',
        margin: '100px auto',
        padding: '40px',
        background: '#fff',
        borderRadius: '16px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: 700,
          marginBottom: '8px',
          textAlign: 'center'
        }}>
          Welcome Back
        </h1>
        <p style={{
          color: '#64748b',
          textAlign: 'center',
          marginBottom: '32px'
        }}>
          Login to your account
        </p>

        {error && (
          <div style={{
            background: '#fee2e2',
            color: '#dc2626',
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="john@company.com"
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="Your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: '8px',
              background: loading ? '#94a3b8' : '#2563eb',
              color: '#fff',
              fontWeight: 600,
              fontSize: '16px',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p style={{
          textAlign: 'center',
          marginTop: '20px',
          color: '#64748b'
        }}>
          <Link href="/forgot-password" style={{ color: '#2563eb' }}>
            Forgot your password?
          </Link>
        </p>
      </div>
    </div>
  )
}
