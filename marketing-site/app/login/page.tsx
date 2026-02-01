'use client'
import { useState } from 'react'
import Link from 'next/link'
import config from '../../config'

// Quathera Logo Component (unchanged)
const QuatheraLogo = () => (
  <svg width="280" height="70" viewBox="150 180 700 140" xmlns="http://www.w3.org/2000/svg">
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
        <circle cx="0" cy="0" r="40" fill="none" stroke="url(#circuitGradient)" strokeWidth="4" filter="url(#glow)" />
        <g stroke="url(#circuitGradient)" strokeWidth="2.5" fill="none" strokeLinecap="round" filter="url(#glow)">
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

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const [resendLoading, setResendLoading] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${config.apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        // Check for email not verified error
        if (response.status === 403 && data.detail === 'Email not verified') {
          setError('EMAIL_NOT_VERIFIED')
          setLoading(false)
          return
        }
        throw new Error(data.detail || 'Login failed')
      }

      setSuccess(true)

      // Store auth data (unchanged)
      localStorage.setItem('token', data.token)
      localStorage.setItem('userType', data.type)
      localStorage.setItem('user_id', data.user_id)
      if (data.company_id) {
        localStorage.setItem('company_id', data.company_id)
      }

      // Redirect to dashboard (unchanged)
      setTimeout(() => {
        window.location.href = `${config.appUrl}/dashboard`
      }, 1000)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleResendVerification = async () => {
    if (resendCooldown > 0 || resendLoading) return

    setResendLoading(true)
    setResendSuccess(false)

    try {
      await fetch(`${config.apiUrl}/api/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      setResendSuccess(true)
      setResendCooldown(60)

      // Countdown timer
      const interval = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(interval)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } catch (err) {
      // Still show success to prevent enumeration
      setResendSuccess(true)
    } finally {
      setResendLoading(false)
    }
  }

  if (success) {
    return (
      <div style={successShell}>
        <div style={successCard}>
          <div style={{ fontSize: 54, marginBottom: 12 }}>✅</div>
          <h1 style={{ fontSize: 22, fontWeight: 900, marginBottom: 10, color: '#fff' }}>Signed in</h1>
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
        <div style={{ textAlign: 'center', marginBottom: 22 }}>
          <Link href="/" style={{ textDecoration: 'none' }}>
            <QuatheraLogo />
          </Link>
        </div>

        <div className="gateway" style={gatewayWrap}>
          {/* Left: secure context */}
          <section style={sidePanel}>
            <div style={pill}>
              <span style={pillDot} />
              Secure gateway
            </div>

            <h1 style={{ fontSize: 34, fontWeight: 950, margin: '14px 0 10px', lineHeight: 1.1 }}>
              Sign in
            </h1>

            <p style={{ margin: 0, color: 'rgba(255,255,255,0.68)', lineHeight: 1.7, fontSize: 14 }}>
              Secure access with email, password, and two-factor authentication.
            </p>

            <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
              {[
                { n: '1', t: 'Authenticate', d: 'Sign in with your account credentials.' },
                { n: '2', t: 'Secure access', d: 'Two-factor authentication protects admin access.' },
                { n: '3', t: 'Enter the app', d: 'Continue to your dashboard and projects.' },
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
              <Link href="/signup" style={smallLink}>
                Need an account? Create one
              </Link>
            </div>
          </section>

          {/* Right: login form */}
          <section style={formCard}>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 950, color: 'rgba(255,255,255,0.9)' }}>Account access</div>
              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13, marginTop: 6, lineHeight: 1.6 }}>
                Sign in to continue to the Quattera app.
              </div>
            </div>

            {error === 'EMAIL_NOT_VERIFIED' ? (
              <div style={verificationBox}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ fontSize: 24 }}>📧</span>
                </div>
                <div style={{ fontWeight: 900, marginBottom: 8, color: '#fff' }}>
                  Email not verified
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', marginBottom: 16, lineHeight: 1.5 }}>
                  Please check your inbox and click the verification link. Check spam folder if you don't see it.
                </div>
                {resendSuccess ? (
                  <div style={{ color: '#00F5D4', fontSize: 13, fontWeight: 600 }}>
                    ✓ Verification email sent!
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendLoading || resendCooldown > 0}
                    style={resendBtn(resendLoading || resendCooldown > 0)}
                  >
                    {resendLoading ? 'Sending...' : resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend verification email'}
                  </button>
                )}
              </div>
            ) : error ? (
              <div style={errorBox}>{error}</div>
            ) : null}

            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={inputStyle}
                  placeholder="you@company.com"
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={inputStyle}
                  placeholder="Your password"
                />
              </div>

              <div style={twoFABox}>
                <span style={{ fontSize: 18 }}>🔐</span>
                <div>
                  <div style={{ margin: 0, fontSize: 13, fontWeight: 900, color: 'rgba(255,255,255,0.90)' }}>
                    Two-factor authentication required
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'rgba(255,255,255,0.62)', lineHeight: 1.5 }}>
                    If enabled for your account, you’ll be prompted during sign-in.
                  </div>
                </div>
              </div>

              <button type="submit" disabled={loading} style={submitBtn(loading)}>
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: 'rgba(255,255,255,0.68)' }}>
              <Link href="/forgot-password" style={{ color: '#00BBF9', textDecoration: 'none', fontWeight: 800 }}>
                Forgot your password?
              </Link>
            </p>

            <p style={{ textAlign: 'center', marginTop: 18, fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
              By signing in, you agree to our Terms of Service and Privacy Policy.
            </p>
          </section>
        </div>

        <p style={{ textAlign: 'center', marginTop: 18, color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>
          Don&apos;t have an account?{' '}
          <Link href="/signup" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 900 }}>
            Create one
          </Link>
        </p>
      </div>

      <style jsx>{`
        ::placeholder {
          color: rgba(255, 255, 255, 0.35);
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

/* styles (match signup) */
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

const verificationBox: React.CSSProperties = {
  background: 'rgba(0, 187, 249, 0.12)',
  border: '1px solid rgba(0, 187, 249, 0.35)',
  color: 'rgba(255,255,255,0.88)',
  padding: '20px 18px',
  borderRadius: 12,
  marginBottom: 14,
  textAlign: 'center',
}

const resendBtn = (disabled: boolean): React.CSSProperties => ({
  padding: '10px 20px',
  borderRadius: 8,
  background: disabled ? 'rgba(148,163,184,0.4)' : 'rgba(0, 245, 212, 0.2)',
  color: disabled ? 'rgba(255,255,255,0.5)' : '#00F5D4',
  fontWeight: 700,
  fontSize: 13,
  border: '1px solid',
  borderColor: disabled ? 'rgba(148,163,184,0.3)' : 'rgba(0, 245, 212, 0.4)',
  cursor: disabled ? 'not-allowed' : 'pointer',
})