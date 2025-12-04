'use client'
import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import config from '../../config'
import TwoFASetupModal from '@/components/TwoFASetupModal'

const QuatheraLogoSmall = () => (
  <svg width="200" height="50" viewBox="150 200 700 100" xmlns="http://www.w3.org/2000/svg">
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
        <circle cx="0" cy="0" r="40" fill="none" stroke="url(#circuitGradient)" strokeWidth="4" filter="url(#glow)"/>
        <g stroke="url(#circuitGradient)" strokeWidth="2.5" fill="none" strokeLinecap="round" filter="url(#glow)">
          <path d="M -28 -16 Q -34 0 -30 16 Q -24 34 0 38 Q 24 34 30 16 Q 34 0 28 -16 Q 20 -34 0 -36 Q -20 -34 -28 -16"/>
          <path d="M 20 24 L 40 44 L 52 40"/>
          <circle cx="52" cy="40" r="3" fill="url(#circuitGradient)"/>
        </g>
        <circle cx="0" cy="0" r="6" fill="#0A0E17" stroke="url(#circuitGradient)" strokeWidth="1.5"/>
      </g>
      
      <g transform="translate(-180, 0)">
        <text x="0" y="14" 
              fontFamily="'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif" 
              fontSize="64" 
              fontWeight="300" 
              fill="#FFFFFF" 
              letterSpacing="4">
          <tspan fill="url(#circuitGradient)" fontWeight="600">Q</tspan>uathera
        </text>
      </g>
    </g>
  </svg>
)

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
  const [show2FASetup, setShow2FASetup] = useState(false)
  const [tempToken, setTempToken] = useState('')

  useEffect(() => {
    const planParam = searchParams.get('plan')
    const productParam = searchParams.get('product')
    if (planParam) setFormData(prev => ({ ...prev, plan: planParam }))
    if (productParam) setFormData(prev => ({ ...prev, product_type: productParam }))
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
      
      if (!response.ok) throw new Error(data.detail || 'Signup failed')
      
      setTempToken(data.token)
      
      if (data.requires_2fa_setup) {
        setShow2FASetup(true)
      } else {
        completeSignup(data.token)
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const completeSignup = (token: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('userType', 'admin')
    setSuccess(true)
    setTimeout(() => { window.location.href = `${config.appUrl}/dashboard` }, 2000)
  }

  const handle2FASuccess = () => {
    setShow2FASetup(false)
    completeSignup(tempToken)
  }

  if (success) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0A0E17' }}>
        <div style={{ background: 'rgba(255,255,255,0.95)', padding: '60px', borderRadius: '20px', textAlign: 'center' }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>✅</div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '12px', color: '#0A0E17' }}>Account Created!</h1>
          <p style={{ color: '#64748b' }}>Redirecting to dashboard...</p>
        </div>
      </div>
    )
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '14px 18px', border: '2px solid #e5e7eb',
    borderRadius: '10px', fontSize: '15px', boxSizing: 'border-box', outline: 'none'
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#374151'
  }

  return (
    <div style={{
      minHeight: '100vh', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif", padding: '40px 20px'
    }}>
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: '#0A0E17' }} />
      <div style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: 'linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px)',
        backgroundSize: '60px 60px', pointerEvents: 'none'
      }} />
      <div style={{ position: 'fixed', top: '-20%', right: '-10%', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(0,187,249,0.15) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', bottom: '-30%', left: '-10%', width: '800px', height: '800px', background: 'radial-gradient(circle, rgba(155,93,229,0.1) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />

      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: '480px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Link href="/" style={{ textDecoration: 'none' }}><QuatheraLogoSmall /></Link>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.95)', borderRadius: '20px', padding: '40px', boxShadow: '0 25px 80px rgba(0,0,0,0.4)' }}>
          <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px', textAlign: 'center', color: '#0A0E17' }}>Create Your Account</h1>
          <p style={{ color: '#64748b', textAlign: 'center', marginBottom: '32px', fontSize: '15px' }}>Start your free 14-day trial</p>

          {error && (
            <div style={{ background: '#fee2e2', color: '#dc2626', padding: '14px 18px', borderRadius: '10px', marginBottom: '24px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Select Plan</label>
              <select value={formData.plan} onChange={(e) => setFormData({ ...formData, plan: e.target.value })} style={{ ...inputStyle, cursor: 'pointer', background: '#fff' }}>
                <option value="trial">Free Trial (14 days)</option>
                <option value="trial_byok">Free Trial with Your API Key</option>
                <option value="starter">Starter ($300/month)</option>
                <option value="professional">Professional ($500/month)</option>
              </select>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Company Name *</label>
              <input type="text" required value={formData.company_name} onChange={(e) => setFormData({ ...formData, company_name: e.target.value })} style={inputStyle} placeholder="Acme Corporation" />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Your Full Name *</label>
              <input type="text" required value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} style={inputStyle} placeholder="John Smith" />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Email Address *</label>
              <input type="email" required value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} style={inputStyle} placeholder="john@company.com" />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Password *</label>
              <input type="password" required value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} style={inputStyle} placeholder="At least 6 characters" />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Confirm Password *</label>
              <input type="password" required value={formData.confirm_password} onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })} style={inputStyle} placeholder="Confirm your password" />
            </div>

            {formData.plan === 'trial_byok' && (
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>Claude API Key *</label>
                <input type="password" required value={formData.claude_api_key} onChange={(e) => setFormData({ ...formData, claude_api_key: e.target.value })} style={inputStyle} placeholder="sk-ant-api03-..." />
                <p style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>
                  Get your API key from <a href="https://console.anthropic.com" target="_blank" style={{ color: '#00BBF9' }}>console.anthropic.com</a>
                </p>
              </div>
            )}

            <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '10px', padding: '14px 16px', marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <span style={{ fontSize: '20px' }}>🔐</span>
              <div>
                <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#166534' }}>Two-Factor Authentication Required</p>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#15803d' }}>You'll set up 2FA after creating your account to secure your admin access.</p>
              </div>
            </div>

            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '16px', borderRadius: '10px',
              background: loading ? '#94a3b8' : 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17', fontWeight: 700, fontSize: '16px', border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer', boxShadow: '0 4px 20px rgba(0,245,212,0.3)'
            }}>
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <p style={{ fontSize: '12px', color: '#94a3b8', textAlign: 'center', marginTop: '20px' }}>
            By signing up, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>

        <p style={{ textAlign: 'center', marginTop: '24px', color: 'rgba(255,255,255,0.7)', fontSize: '15px' }}>
          Already have an account? <Link href="/login" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 600 }}>Sign In</Link>
        </p>
      </div>

      <TwoFASetupModal isOpen={show2FASetup} onClose={() => {}} onSuccess={handle2FASuccess} token={tempToken} isMandatory={true} />
    </div>
  )
}
