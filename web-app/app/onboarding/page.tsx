'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function OnboardingPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Onboarding state
  const [step, setStep] = useState(1)
  const [accountCategory, setAccountCategory] = useState<string | null>(null)
  const [accessModel, setAccessModel] = useState<string | null>(null)
  const [accessStatus, setAccessStatus] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id')

    fetch('/api/auth/me', { credentials: 'include' })
      .then(res => {
        if (!res.ok) {
          window.location.href = '/login'
          return null
        }
        return res.json()
      })
      .then(data => {
        if (!data) return
        setUserId(String(data.user_id))
        checkOnboardingStatus()
      })
      .catch(() => {
        window.location.href = '/login'
      })
  }, [])

  const checkOnboardingStatus = async () => {
    try {
      const response = await fetchWithAuth(`/api/onboarding/status`)

      if (response.ok) {
        const data = await response.json()

        // If already completed, redirect to dashboard
        if (data.onboarding_completed) {
          window.location.href = '/dashboard/form-pages-discovery'
          return
        }

        // Set current state
        setAccountCategory(data.account_category)
        setAccessModel(data.access_model)
        setAccessStatus(data.access_status)

        // Determine current step based on state
        if (!data.account_category) {
          // Need to select category
          setStep(1)
        } else if (!data.access_model) {
          // Need to select access model
          setStep(2)
        } else if (data.access_model === 'byok' && data.access_status !== 'active') {
          // BYOK selected but no API key yet
          setStep(3)
        } else if (data.access_model === 'early_access' && data.access_status === 'pending') {
          // Early Access pending approval
          setStep(4)
        } else if (data.access_status === 'active') {
          // Everything ready, complete onboarding
          completeOnboarding()
          return
        }

        setLoading(false)
      } else {
        setError('Failed to load onboarding status')
        setLoading(false)
      }
    } catch (err) {
      setError('Connection error')
      setLoading(false)
    }
  }

  const saveCategory = async (category: string) => {
    setSaving(true)
    setError(null)

    try {
      const response = await fetchWithAuth(`/api/onboarding/category`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_category: category })
      })

      if (response.ok) {
        setAccountCategory(category)

        // Check if access model is already set (marketing BYOK instant)
        if (accessModel === 'byok') {
          // BYOK pre-selected, go to API key step
          setStep(3)
        } else if (accessModel === 'early_access' && accessStatus === 'pending') {
          // Early access pre-selected and pending
          setStep(4)
        } else if (accessModel && accessStatus === 'active') {
          // Already active, complete
          completeOnboarding()
        } else {
          // No access model set, go to selection
          setStep(2)
        }
      } else {
        setError('Failed to save category')
      }
    } catch (err) {
      setError('Connection error')
    }
    setSaving(false)
  }

  const saveAccessModel = async (model: string) => {
    setSaving(true)
    setError(null)

    try {
      const response = await fetchWithAuth(`/api/onboarding/access-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_model: model })
      })

      if (response.ok) {
        const data = await response.json()
        setAccessModel(model)
        setAccessStatus(data.access_status)

        if (model === 'byok') {
          // Go to API key input
          setStep(3)
        } else {
          // Early access - go to pending screen
          setStep(4)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to save access model')
      }
    } catch (err) {
      setError('Connection error')
    }
    setSaving(false)
  }

  const saveApiKey = async () => {
    if (!apiKey.trim()) {
      setError('Please enter your API key')
      return
    }
    if (!apiKey.trim().startsWith('sk-ant-')) {
      setError('Invalid key format. Anthropic keys start with sk-ant-')
      return
    }

    setSaving(true)
    setError(null)

    try {
      const response = await fetchWithAuth(`/api/settings/api-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey.trim() })
      })

      if (response.ok) {
        // API key saved, onboarding complete
        window.location.href = '/dashboard/form-pages-discovery'
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to save API key')
      }
    } catch (err) {
      setError('Connection error')
    }
    setSaving(false)
  }

  const completeOnboarding = async () => {
    try {
      const response = await fetchWithAuth(`/api/onboarding/complete`, {
        method: 'POST'
      })

      if (response.ok) {
        window.location.href = '/dashboard/form-pages-discovery'
      } else {
        setLoading(false)
      }
    } catch (err) {
      setLoading(false)
    }
  }

  // Calculate progress step for display (1-3)
  const getProgressStep = () => {
    if (step === 1) return 1
    if (step === 2) return 2
    return 3 // Steps 3 and 4 both show as final step
  }

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
            <p style={{ color: '#64748b', fontSize: '18px' }}>Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#1e293b', margin: '0 0 12px' }}>
            Welcome to Quattera
          </h1>
          <p style={{ fontSize: '16px', color: '#64748b', margin: 0 }}>
            Let's set up your account
          </p>
        </div>

        {/* Progress indicator */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginBottom: '40px' }}>
          {[1, 2, 3].map(s => (
            <div
              key={s}
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '16px',
                background: getProgressStep() >= s ? 'linear-gradient(135deg, #0ea5e9, #6366f1)' : '#e2e8f0',
                color: getProgressStep() >= s ? 'white' : '#94a3b8'
              }}
            >
              {s}
            </div>
          ))}
        </div>

        {/* Error message */}
        {error && (
          <div style={{ background: '#fee2e2', color: '#dc2626', padding: '14px', borderRadius: '10px', marginBottom: '24px', textAlign: 'center' }}>
            {error}
          </div>
        )}

        {/* Step 1: Account Category */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', textAlign: 'center' }}>
              What kind of application are you testing?
            </h2>
            <p style={{ color: '#64748b', marginBottom: '32px', textAlign: 'center' }}>
              This helps us configure the right testing workflow for you
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <button
                onClick={() => saveCategory('form_centric')}
                disabled={saving}
                style={optionButtonStyle}
              >
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>📋</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: '#1e293b', marginBottom: '12px' }}>
                  Form-Heavy / Enterprise Applications
                </div>
                <ul style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.8, textAlign: 'left', margin: 0, paddingLeft: '20px' }}>
                  <li>Enterprise systems with forms, workflows, and admin panels</li>
                  <li>Multi-step forms, nested fields, validations</li>
                  <li>Automatic form discovery and mapping</li>
                  <li>Spec and Figma comparison</li>
                  <li>Dynamic scenario testing within form projects</li>
                  <li style={{ listStyle: 'none', marginTop: '12px', fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>Best for internal tools, CRMs, admin portals, and workflow systems</li>
                </ul>
              </button>

              <button
                onClick={() => saveCategory('dynamic')}
                disabled={saving}
                style={optionButtonStyle}
              >
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>⚡</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: '#1e293b', marginBottom: '12px' }}>
                  Dynamic Web Applications
                </div>
                <ul style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.8, textAlign: 'left', margin: 0, paddingLeft: '20px' }}>
                  <li>Highly dynamic UIs (Streaming web apps / News sites)</li>
                  <li>User-flow driven testing</li>
                  <li>Visual step-based scenarios</li>
                  <li>Scenario-driven testing (no automatic form discovery)</li>
                  <li style={{ listStyle: 'none', marginTop: '12px', fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>Best for consumer apps, media platforms, and highly interactive UIs</li>
                </ul>
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Access Model Selection */}
        {step === 2 && (
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', textAlign: 'center' }}>
              How would you like to power AI features?
            </h2>
            <p style={{ color: '#64748b', marginBottom: '32px', textAlign: 'center' }}>
              Choose your AI access method
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* BYOK Option */}
              <button
                onClick={() => saveAccessModel('byok')}
                disabled={saving}
                style={optionButtonStyle}
              >
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔑</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>
                  Bring Your Own Key (BYOK)
                </div>
                <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '8px' }}>
                  Use your own Anthropic API key — full control, unlimited usage
                </div>
                <div style={{
                  display: 'inline-block',
                  background: '#dcfce7',
                  color: '#16a34a',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: 600
                }}>
                  Instant Access
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
                  You can switch to a managed plan later
                </div>
              </button>

              {/* Divider */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', margin: '8px 0' }}>
                <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
                <span style={{ color: '#94a3b8', fontSize: '14px' }}>or</span>
                <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
              </div>

              {/* Early Access Option */}
              <button
                onClick={() => saveAccessModel('early_access')}
                disabled={saving}
                style={optionButtonStyle}
              >
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>🚀</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>
                  Request Early Access
                </div>
                <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '8px' }}>
                  Limited free trial — curated access with a daily AI budget
                </div>
                <div style={{
                  display: 'inline-block',
                  background: '#fef3c7',
                  color: '#d97706',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: 600
                }}>
                  Subject to availability
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
                  You can bring your own key at any time
                </div>
              </button>
            </div>

            {/* Back button */}
            <button
              onClick={() => setStep(1)}
              style={{ ...secondaryButtonStyle, marginTop: '24px', width: '100%' }}
            >
              ← Back
            </button>
          </div>
        )}

        {/* Step 3: API Key Input (BYOK) */}
        {step === 3 && (
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', textAlign: 'center' }}>
              Enter Your API Key
            </h2>
            <p style={{ color: '#64748b', marginBottom: '32px', textAlign: 'center' }}>
              Your key is encrypted and stored securely
            </p>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>
                Anthropic API Key
              </label>
              <input
                type="password"
                placeholder="sk-ant-api03-..."
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  setError(null)
                }}
                style={inputStyle}
              />
            </div>

            {/* Help text */}
            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
              <p style={{ color: '#0369a1', margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>
                How to get your API key:
              </p>
              <ol style={{ color: '#0369a1', margin: 0, paddingLeft: '20px', fontSize: '14px', lineHeight: 1.8 }}>
                <li>Go to <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>console.anthropic.com</a></li>
                <li>Navigate to API Keys</li>
                <li>Create a new key or copy an existing one</li>
              </ol>
            </div>

            <button
              onClick={saveApiKey}
              disabled={saving || !apiKey.trim()}
              style={{
                ...primaryButtonStyle,
                opacity: saving || !apiKey.trim() ? 0.5 : 1
              }}
            >
              {saving ? 'Saving...' : 'Complete Setup'}
            </button>

            {/* Back button */}
            <button
              onClick={() => accessModel ? setStep(1) : setStep(2)}
              style={{ ...secondaryButtonStyle, marginTop: '12px', width: '100%' }}
            >
              ← Back
            </button>
          </div>
        )}

        {/* Step 4: Pending Approval (Early Access) */}
        {step === 4 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '64px', marginBottom: '24px' }}>⏳</div>
            <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#1e293b', marginBottom: '12px' }}>
              Early Access Pending
            </h2>
            <p style={{ color: '#64748b', marginBottom: '32px', lineHeight: 1.6 }}>
              Your Early Access request has been submitted.<br />
              We'll notify you by email once approved.
            </p>

            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
              <p style={{ color: '#0369a1', margin: 0, fontSize: '14px' }}>
                💡 Want immediate access? You can switch to BYOK anytime by providing your own API key.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={() => window.location.reload()}
                style={secondaryButtonStyle}
              >
                Check Status
              </button>
              <button
                onClick={() => {
                  setAccessModel('byok')
                  setStep(3)
                }}
                style={primaryButtonStyle}
              >
                ⚡ Switch to BYOK
              </button>
            </div>
            <button
              onClick={async () => {
                await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
                localStorage.clear()
                window.location.href = '/login'
              }}
              style={{
                marginTop: '24px',
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '14px',
                cursor: 'pointer',
                textDecoration: 'underline'
              }}
            >
              Logout
            </button>
          </div>
        )}
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
  maxWidth: '540px',
  boxShadow: '0 25px 80px rgba(0, 0, 0, 0.4)'
}

const optionButtonStyle: React.CSSProperties = {
  background: '#f8fafc',
  border: '2px solid #e2e8f0',
  borderRadius: '16px',
  padding: '24px',
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  width: '100%'
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
  padding: '14px',
  background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
  color: 'white',
  border: 'none',
  borderRadius: '10px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer'
}

const secondaryButtonStyle: React.CSSProperties = {
  padding: '14px 32px',
  background: 'transparent',
  color: '#64748b',
  border: '2px solid #e2e8f0',
  borderRadius: '10px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer'
}
