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
        <stop offset="0%" style={{ stopColor: '#00F5D4' }} />
        <stop offset="50%" style={{ stopColor: '#00BBF9' }} />
        <stop offset="100%" style={{ stopColor: '#9B5DE5' }} />
      </linearGradient>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <g transform="translate(500, 250)">
      <g transform="translate(-280, 0)">
        <circle
          cx="0"
          cy="0"
          r="40"
          fill="none"
          stroke="url(#circuitGradient)"
          strokeWidth="4"
          filter="url(#glow)"
        />
        <g
          stroke="url(#circuitGradient)"
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
          filter="url(#glow)"
        >
          <path d="M -28 -16 Q -34 0 -30 16 Q -24 34 0 38 Q 24 34 30 16 Q 34 0 28 -16 Q 20 -34 0 -36 Q -20 -34 -28 -16" />
          <path d="M 20 24 L 40 44 L 52 40" />
          <circle cx="52" cy="40" r="3" fill="url(#circuitGradient)" />
        </g>
        <circle cx="0" cy="0" r="6" fill="#0A0E17" stroke="url(#circuitGradient)" strokeWidth="1.5" />
      </g>

      <g transform="translate(-180, 0)">
        <text
          x="0"
          y="14"
          fontFamily="'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
          fontSize="64"
          fontWeight="300"
          fill="#FFFFFF"
          letterSpacing="4"
        >
          <tspan fill="url(#circuitGradient)" fontWeight="600">
            Q
          </tspan>
          uattera
        </text>
      </g>
    </g>
  </svg>
)

type AccessModel = 'early_access' | 'byok'

export default function Signup() {
  const searchParams = useSearchParams()

  const [accessModel, setAccessModel] = useState<AccessModel>('early_access')

  const [formData, setFormData] = useState({
    company_name: '',
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    product_type: 'form_testing',
    plan: 'trial', // keep backend contract: trial | trial_byok
    claude_api_key: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [verificationRequired, setVerificationRequired] = useState(false)
  const [show2FASetup, setShow2FASetup] = useState(false)
  const [tempToken, setTempToken] = useState('')

  useEffect(() => {
    const planParam = searchParams.get('plan')
    const productParam = searchParams.get('product')

    if (productParam) setFormData((prev) => ({ ...prev, product_type: productParam }))

    // Backwards compatible: if old links still pass ?plan=trial_byok, we reflect it.
    if (planParam === 'trial_byok') {
      setAccessModel('byok')
      setFormData((prev) => ({ ...prev, plan: 'trial_byok' }))
    } else if (planParam === 'trial') {
      setAccessModel('early_access')
      setFormData((prev) => ({ ...prev, plan: 'trial' }))
    }
  }, [searchParams])

  // Keep plan in sync with accessModel (this preserves your backend logic)
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      plan: accessModel === 'byok' ? 'trial_byok' : 'trial',
    }))
  }, [accessModel])

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
      setError('API key is required for BYOK')
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
          claude_api_key: formData.plan === 'trial_byok' ? formData.claude_api_key : null,
        }),
      })

      const data = await response.json()

      if (!response.ok) throw new Error(data.detail || 'Signup failed')

      // Email verification required
      if (data.status === 'verification_required') {
        setVerificationRequired(true)
        return
      }

      // Legacy flow (shouldn't happen anymore)
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
    setTimeout(() => {
      window.location.href = `${config.appUrl}/dashboard`
    }, 1500)
  }

  const handle2FASuccess = () => {
    setShow2FASetup(false)
    completeSignup(tempToken)
  }

  if (verificationRequired) {
    return (
      <div style={successShell}>
        <div style={successCard}>
          <div style={{ fontSize: 54, marginBottom: 12 }}>📧</div>
          <h1 style={{ fontSize: 22, fontWeight: 900, marginBottom: 10, color: '#fff' }}>Check your email</h1>
          <p style={{ color: 'rgba(255,255,255,0.65)', margin: 0, lineHeight: 1.6 }}>
            We sent a verification link to <strong>{formData.email}</strong>
          </p>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '16px 0 0', fontSize: 14 }}>
            Click the link to verify your account, then sign in.
          </p>
          <Link href="/login" style={{
            display: 'inline-block',
            marginTop: 24,
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
            color: '#0A0E17',
            fontWeight: 700,
            borderRadius: 10,
            textDecoration: 'none'
          }}>
            Go to Login
          </Link>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div style={successShell}>
        <div style={successCard}>
          <div style={{ fontSize: 54, marginBottom: 12 }}>✅</div>
          <h1 style={{ fontSize: 22, fontWeight: 900, marginBottom: 10, color: '#fff' }}>Account created</h1>
          <p style={{ color: 'rgba(255,255,255,0.65)', margin: 0 }}>Redirecting to the app…</p>
        </div>
      </div>
    )
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '14px 14px',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 12,
    fontSize: 14,
    boxSizing: 'border-box',
    outline: 'none',
    background: 'rgba(255,255,255,0.06)',
    color: '#fff',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: 8,
    fontSize: 13,
    fontWeight: 800,
    color: 'rgba(255,255,255,0.80)',
  }

  return (
    <div style={shell}>
      {/* background layers */}
      <div style={bgBase} />
      <div style={bgGrid} />
      <div style={bgGlowRight} />
      <div style={bgGlowLeft} />

      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 980 }}>
        {/* top logo */}
        <div style={{ textAlign: 'center', marginBottom: 22 }}>
          <Link href="/" style={{ textDecoration: 'none' }}>
            <QuatheraLogoSmall />
          </Link>
        </div>

        <div style={gatewayWrap}>
          {/* Left: secure context */}
          <section style={sidePanel}>
            <div style={pill}>
              <span style={pillDot} />
              Secure gateway
            </div>

            <h1 style={{ fontSize: 34, fontWeight: 950, margin: '14px 0 10px', lineHeight: 1.1 }}>
              Create your account
            </h1>

            <p style={{ margin: 0, color: 'rgba(255,255,255,0.68)', lineHeight: 1.7, fontSize: 14 }}>
              You’ll verify your email and set up 2FA before choosing your project type and AI access.
            </p>

            <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
              {[
                { n: '1', t: 'Sign up', d: 'Create your account with email and password.' },
                { n: '2', t: 'Verify email', d: 'Confirm your email from your inbox.' },
                { n: '3', t: 'Set up 2FA', d: 'Secure your admin access.' },
                { n: '4', t: 'Choose in-app', d: 'Pick project type + Early Access or BYOK.' },
              ].map((s) => (
                <div key={s.n} style={stepCard}>
                  <div style={stepRow}>
                    <div style={stepNum}>{s.n}</div>
                    <div>
                      <div style={{ fontWeight: 900 }}>{s.t}</div>
                      <div style={{ color: 'rgba(255,255,255,0.62)', fontSize: 12, lineHeight: 1.5 }}>{s.d}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 14, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Link href="/pricing" style={smallLink}>
                Back to Pricing
              </Link>
              <Link href="/login" style={smallLink}>
                Already have an account? Log in
              </Link>
            </div>
          </section>

          {/* Right: form card */}
          <section style={formCard}>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 950, color: 'rgba(255,255,255,0.9)' }}>Account creation</div>
              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13, marginTop: 6, lineHeight: 1.6 }}>
                No pricing shown here. Access is configured inside the app.
              </div>
            </div>

            {error && <div style={errorBox}>{error}</div>}

            <form onSubmit={handleSubmit}>
              {/* AI access model (replaces plan/pricing UI) */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>AI Access Model</label>
                <select
                  value={accessModel}
                  onChange={(e) => setAccessModel(e.target.value as AccessModel)}
                  style={{ ...inputStyle, cursor: 'pointer' }}
                >
                  <option value="early_access">Early Access (manual approval)</option>
                  <option value="byok">BYOK (instant)</option>
                </select>
                <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5 }}>
                  Early Access is reviewed manually due to limited funded AI capacity. BYOK uses your own AI key.
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Company Name *</label>
                <input
                  type="text"
                  required
                  value={formData.company_name}
                  onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                  style={inputStyle}
                  placeholder="Acme Corporation"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Your Full Name *</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  style={inputStyle}
                  placeholder="John Smith"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Email Address *</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={inputStyle}
                  placeholder="john@company.com"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Password *</label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  style={inputStyle}
                  placeholder="At least 6 characters"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Confirm Password *</label>
                <input
                  type="password"
                  required
                  value={formData.confirm_password}
                  onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                  style={inputStyle}
                  placeholder="Confirm your password"
                />
              </div>

              {formData.plan === 'trial_byok' && (
                <div style={{ marginBottom: 16 }}>
                  <label style={labelStyle}>Anthropic API Key *</label>
                  <input
                    type="password"
                    required
                    value={formData.claude_api_key}
                    onChange={(e) => setFormData({ ...formData, claude_api_key: e.target.value })}
                    style={inputStyle}
                    placeholder="sk-ant-api03-..."
                  />
                  <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 8, lineHeight: 1.5 }}>
                    Get your key from{' '}
                    <a
                      href="https://console.anthropic.com"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#00BBF9', textDecoration: 'none', fontWeight: 800 }}
                    >
                      console.anthropic.com
                    </a>
                    .
                  </p>
                </div>
              )}

              {/* 2FA requirement */}
              <div style={twoFABox}>
                <span style={{ fontSize: 18 }}>🔐</span>
                <div>
                  <div style={{ margin: 0, fontSize: 13, fontWeight: 900, color: 'rgba(255,255,255,0.90)' }}>
                    Two-factor authentication required
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'rgba(255,255,255,0.62)', lineHeight: 1.5 }}>
                    You’ll set up 2FA after account creation to secure admin access.
                  </div>
                </div>
              </div>

              <button type="submit" disabled={loading} style={submitBtn(loading)}>
                {loading ? 'Creating account…' : 'Create account'}
              </button>
            </form>

            {/* minimal legal */}
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', textAlign: 'center', marginTop: 14 }}>
              By signing up, you agree to our Terms of Service and Privacy Policy.
            </p>
          </section>
        </div>

        {/* bottom link */}
        <p style={{ textAlign: 'center', marginTop: 18, color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>
          Already have an account?{' '}
          <Link href="/login" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 900 }}>
            Sign In
          </Link>
        </p>
      </div>

      <TwoFASetupModal
        isOpen={show2FASetup}
        onClose={() => {}}
        onSuccess={handle2FASuccess}
        token={tempToken}
        isMandatory={true}
      />

      <style jsx>{`
        ::placeholder {
          color: rgba(255, 255, 255, 0.35);
        }
        select option {
          color: #0a0e17;
        }
        @media (max-width: 980px) {
          .gateway {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}

/* styles */
const shell: React.CSSProperties = {
  minHeight: '100vh',
  position: 'relative',
  display: 'grid',
  placeItems: 'center',
  fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
  padding: '36px 18px',
}

const bgBase: React.CSSProperties = { position: 'fixed', inset: 0, background: '#0A0E17' }

const bgGrid: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  backgroundImage:
    'linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px)',
  backgroundSize: '60px 60px',
  pointerEvents: 'none',
}

const bgGlowRight: React.CSSProperties = {
  position: 'fixed',
  top: '-20%',
  right: '-10%',
  width: 640,
  height: 640,
  background: 'radial-gradient(circle, rgba(0,187,249,0.15) 0%, transparent 70%)',
  borderRadius: '50%',
  pointerEvents: 'none',
}

const bgGlowLeft: React.CSSProperties = {
  position: 'fixed',
  bottom: '-30%',
  left: '-10%',
  width: 820,
  height: 820,
  background: 'radial-gradient(circle, rgba(155,93,229,0.12) 0%, transparent 70%)',
  borderRadius: '50%',
  pointerEvents: 'none',
}

const gatewayWrap: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1.05fr 0.95fr',
  gap: 18,
  alignItems: 'stretch',
}

const sidePanel: React.CSSProperties = {
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(255,255,255,0.02)',
  borderRadius: 18,
  padding: 22,
}

const formCard: React.CSSProperties = {
  borderRadius: 18,
  padding: 22,
  border: '1px solid rgba(0,245,212,0.22)',
  background: 'linear-gradient(135deg, rgba(0,245,212,0.06), rgba(0,0,0,0.20))',
  boxShadow: '0 0 0 1px rgba(0,245,212,0.05) inset, 0 25px 80px rgba(0,0,0,0.35)',
}

const pill: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 10,
  padding: '8px 12px',
  borderRadius: 999,
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.12)',
  fontSize: 12,
  fontWeight: 900,
  color: 'rgba(255,255,255,0.82)',
}

const pillDot: React.CSSProperties = {
  width: 8,
  height: 8,
  borderRadius: 999,
  background: '#34d399',
  display: 'inline-block',
}

const stepCard: React.CSSProperties = {
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(0,0,0,0.18)',
  borderRadius: 14,
  padding: 12,
}

const stepRow: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 12 }

const stepNum: React.CSSProperties = {
  width: 30,
  height: 30,
  borderRadius: 999,
  background: 'rgba(255,255,255,0.07)',
  border: '1px solid rgba(255,255,255,0.12)',
  display: 'grid',
  placeItems: 'center',
  fontWeight: 950,
}

const smallLink: React.CSSProperties = {
  color: 'rgba(255,255,255,0.72)',
  textDecoration: 'none',
  fontSize: 13,
  border: '1px solid rgba(255,255,255,0.12)',
  background: 'rgba(255,255,255,0.04)',
  padding: '10px 12px',
  borderRadius: 12,
}

const errorBox: React.CSSProperties = {
  background: 'rgba(220,38,38,0.12)',
  border: '1px solid rgba(220,38,38,0.35)',
  color: 'rgba(255,255,255,0.88)',
  padding: '12px 14px',
  borderRadius: 12,
  marginBottom: 14,
  fontSize: 13,
  lineHeight: 1.5,
}

const twoFABox: React.CSSProperties = {
  border: '1px solid rgba(52,211,153,0.25)',
  background: 'rgba(52,211,153,0.08)',
  borderRadius: 12,
  padding: '12px 12px',
  marginBottom: 14,
  display: 'flex',
  alignItems: 'flex-start',
  gap: 12,
}

const submitBtn = (loading: boolean): React.CSSProperties => ({
  width: '100%',
  padding: '14px',
  borderRadius: 12,
  background: loading ? 'rgba(148,163,184,0.6)' : 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
  color: '#0A0E17',
  fontWeight: 950,
  fontSize: 15,
  border: 'none',
  cursor: loading ? 'not-allowed' : 'pointer',
  boxShadow: loading ? 'none' : '0 10px 30px rgba(0,245,212,0.16)',
})

const successShell: React.CSSProperties = {
  minHeight: '100vh',
  display: 'grid',
  placeItems: 'center',
  background: '#0A0E17',
}

const successCard: React.CSSProperties = {
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(255,255,255,0.03)',
  padding: 44,
  borderRadius: 18,
  textAlign: 'center',
}