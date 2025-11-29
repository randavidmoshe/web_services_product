'use client'
import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import config from '../../config'

export default function Signup() {
  const searchParams = useSearchParams()
  
  const [formData, setFormData] = useState({
    company_name: '',
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    product_type: 'form_testing',
    plan: 'trial',
    claude_api_key: ''
  })
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    const planParam = searchParams.get('plan')
    const productParam = searchParams.get('product')
    if (planParam) {
      setFormData(prev => ({ ...prev, plan: planParam }))
    }
    if (productParam) {
      setFormData(prev => ({ ...prev, product_type: productParam }))
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match')
      return
    }
    
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    
    if (formData.plan === 'trial_byok' && !formData.claude_api_key) {
      setError('API key is required for BYOK plan')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await fetch(`${config.apiUrl}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: formData.company_name,
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          product_type: formData.product_type,
          plan: formData.plan,
          claude_api_key: formData.plan === 'trial_byok' ? formData.claude_api_key : null
        })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed')
      }
      
      setSuccess(true)
      // Redirect to login after 2 seconds
      setTimeout(() => {
        window.location.href = '/login'
      }, 2000)
      
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const planLabels: Record<string, string> = {
    trial: 'Free Trial (14 days)',
    trial_byok: 'Free Trial with Your API Key',
    starter: 'Starter ($300/month)',
    professional: 'Professional ($500/month)'
  }

  if (success) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f8fafc'
      }}>
        <div style={{
          background: '#fff',
          padding: '60px',
          borderRadius: '16px',
          textAlign: 'center',
          boxShadow: '0 4px 24px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>✅</div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '12px' }}>Account Created!</h1>
          <p style={{ color: '#64748b' }}>Redirecting to login...</p>
        </div>
      </div>
    )
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
          <span style={{ color: '#64748b' }}>Already have an account?</span>
          <Link href="/login" style={{
            color: '#2563eb',
            fontWeight: 600
          }}>
            Login
          </Link>
        </div>
      </nav>

      {/* Signup Form */}
      <div style={{
        maxWidth: '480px',
        margin: '60px auto',
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
          Create Your Account
        </h1>
        <p style={{
          color: '#64748b',
          textAlign: 'center',
          marginBottom: '32px'
        }}>
          Start your free trial today
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
          {/* Plan Selection */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Select Plan
            </label>
            <select
              value={formData.plan}
              onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
            >
              <option value="trial">Free Trial (14 days)</option>
              <option value="trial_byok">Free Trial with Your API Key</option>
              <option value="starter">Starter ($300/month)</option>
              <option value="professional">Professional ($500/month)</option>
            </select>
          </div>

          {/* Company Name */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Company Name *
            </label>
            <input
              type="text"
              required
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="Acme Corporation"
            />
          </div>

          {/* Full Name */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Your Full Name *
            </label>
            <input
              type="text"
              required
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="John Smith"
            />
          </div>

          {/* Email */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Email Address *
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
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

          {/* Password */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Password *
            </label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="At least 6 characters"
            />
          </div>

          {/* Confirm Password */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Confirm Password *
            </label>
            <input
              type="password"
              required
              value={formData.confirm_password}
              onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px'
              }}
              placeholder="Confirm your password"
            />
          </div>

          {/* Claude API Key (for BYOK) */}
          {formData.plan === 'trial_byok' && (
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                Claude API Key *
              </label>
              <input
                type="password"
                required
                value={formData.claude_api_key}
                onChange={(e) => setFormData({ ...formData, claude_api_key: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  fontSize: '14px'
                }}
                placeholder="sk-ant-api03-..."
              />
              <p style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
                Get your API key from{' '}
                <a href="https://console.anthropic.com" target="_blank" style={{ color: '#2563eb' }}>
                  console.anthropic.com
                </a>
              </p>
            </div>
          )}

          {/* Submit Button */}
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
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p style={{
          fontSize: '12px',
          color: '#64748b',
          textAlign: 'center',
          marginTop: '20px'
        }}>
          By signing up, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  )
}
