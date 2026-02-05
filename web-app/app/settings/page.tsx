'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/services/authInterceptor'

type SettingsTab = 'profile' | 'api-key' | 'notifications' | 'security' | 'billing'

export default function SettingsPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Active tab
  const [activeTab, setActiveTab] = useState<SettingsTab>('api-key')

  // API Key state
  const [hasKey, setHasKey] = useState(false)
  const [maskedKey, setMaskedKey] = useState('')
  const [newKey, setNewKey] = useState('')
  const [showKeyInput, setShowKeyInput] = useState(false)

  // Menu items
  const menuItems: { id: SettingsTab; label: string; icon: string; available: boolean }[] = [
    { id: 'profile', label: 'Profile', icon: '👤', available: false },
    { id: 'api-key', label: 'API Key', icon: '🔑', available: true },
    { id: 'security', label: 'Security', icon: '🛡️', available: false },
    { id: 'notifications', label: 'Notifications', icon: '🔔', available: false },
    { id: 'billing', label: 'Billing', icon: '💳', available: false },
  ]

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
        fetchApiKeyStatus()
      })
      .catch(() => {
        window.location.href = '/login'
      })
  }, [])

  const fetchApiKeyStatus = async () => {
    try {
      const res = await fetchWithAuth(`/api/settings/api-key`)

      if (!res.ok) {
        throw new Error('Failed to fetch API key status')
      }

      const data = await res.json()
      setHasKey(data.has_key)
      setMaskedKey(data.masked_key || '')
    } catch (err) {
      console.error('Failed to fetch API key:', err)
    } finally {
      setLoading(false)
    }
  }

  const saveApiKey = async () => {
    if (!newKey.trim()) {
      setMessage({ type: 'error', text: 'API key is required' })
      return
    }
    if (!newKey.startsWith('sk-ant-')) {
      setMessage({ type: 'error', text: 'Invalid key format. Anthropic keys start with sk-ant-' })
      return
    }

    setSaving(true)
    setMessage(null)

    try {
      const res = await fetchWithAuth(`/api/settings/api-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: newKey.trim() })
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to save API key')
      }

      setMessage({ type: 'success', text: 'API key saved successfully' })
      setShowKeyInput(false)
      setNewKey('')
      fetchApiKeyStatus()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  const deleteApiKey = async () => {
    if (!confirm('Are you sure you want to remove your API key? AI features will be disabled.')) {
      return
    }

    setSaving(true)

    try {
      const res = await fetchWithAuth(`/api/settings/api-key`, {
        method: 'DELETE'
      })

      if (!res.ok) {
        throw new Error('Failed to delete API key')
      }

      setMessage({ type: 'success', text: 'API key removed' })
      setHasKey(false)
      setMaskedKey('')
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
            <p style={{ color: '#64748b', fontSize: '18px' }}>Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <button
          onClick={() => router.push('/dashboard/form-pages-discovery')}
          style={backButtonStyle}
        >
          ← Back to Dashboard
        </button>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1e293b', margin: 0 }}>Settings</h1>
        <div style={{ width: '140px' }} /> {/* Spacer for centering */}
      </div>

      {/* Main Content */}
      <div style={mainContentStyle}>
        {/* Sidebar */}
        <div style={sidebarStyle}>
          <nav>
            {menuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => item.available && setActiveTab(item.id)}
                style={{
                  ...menuItemStyle,
                  background: activeTab === item.id ? 'linear-gradient(135deg, #0ea5e9, #6366f1)' : 'transparent',
                  color: activeTab === item.id ? 'white' : item.available ? '#374151' : '#9ca3af',
                  cursor: item.available ? 'pointer' : 'not-allowed',
                  opacity: item.available ? 1 : 0.6
                }}
              >
                <span style={{ fontSize: '20px' }}>{item.icon}</span>
                <span>{item.label}</span>
                {!item.available && (
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: '10px',
                    background: '#e5e7eb',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    color: '#6b7280'
                  }}>
                    Soon
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content Area */}
        <div style={contentAreaStyle}>
          {/* Message */}
          {message && (
            <div style={{
              background: message.type === 'error' ? '#fef2f2' : '#f0fdf4',
              color: message.type === 'error' ? '#dc2626' : '#16a34a',
              padding: '16px 20px',
              borderRadius: '12px',
              marginBottom: '24px',
              border: `1px solid ${message.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span>{message.type === 'error' ? '❌' : '✅'}</span>
              {message.text}
            </div>
          )}

          {/* API Key Tab */}
          {activeTab === 'api-key' && (
            <div>
              <div style={sectionHeaderStyle}>
                <h2 style={{ fontSize: '20px', fontWeight: 600, color: '#1e293b', margin: 0 }}>
                  Anthropic API Key
                </h2>
                <p style={{ color: '#64748b', fontSize: '14px', margin: '8px 0 0' }}>
                  Your API key powers all AI features in Quattera. It's stored securely and encrypted.
                </p>
              </div>

              <div style={cardStyle}>
                {hasKey && !showKeyInput ? (
                  <div>
                    <div style={{ marginBottom: '20px' }}>
                      <label style={labelStyle}>Current API Key</label>
                      <div style={keyDisplayStyle}>
                        <code style={{ fontFamily: 'monospace', fontSize: '15px', color: '#1e293b' }}>
                          {maskedKey}
                        </code>
                        <span style={statusBadgeStyle}>Active</span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button
                        onClick={() => setShowKeyInput(true)}
                        style={secondaryButtonStyle}
                      >
                        Update Key
                      </button>
                      <button
                        onClick={deleteApiKey}
                        disabled={saving}
                        style={dangerButtonStyle}
                      >
                        Remove Key
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ marginBottom: '20px' }}>
                      <label style={labelStyle}>
                        {hasKey ? 'New API Key' : 'API Key'}
                      </label>
                      <input
                        type="password"
                        value={newKey}
                        onChange={(e) => setNewKey(e.target.value)}
                        placeholder="sk-ant-api03-..."
                        style={inputStyle}
                      />
                    </div>

                    <div style={infoBoxStyle}>
                      <div style={{ fontSize: '16px', marginBottom: '8px' }}>💡</div>
                      <div>
                        <p style={{ margin: '0 0 8px', fontWeight: 500, color: '#0369a1' }}>
                          How to get your API key:
                        </p>
                        <ol style={{ margin: 0, paddingLeft: '20px', color: '#0369a1', lineHeight: 1.8 }}>
                          <li>Go to <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>console.anthropic.com</a></li>
                          <li>Navigate to API Keys section</li>
                          <li>Create a new key or copy an existing one</li>
                        </ol>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                      {hasKey && (
                        <button
                          onClick={() => {
                            setShowKeyInput(false)
                            setNewKey('')
                            setMessage(null)
                          }}
                          style={secondaryButtonStyle}
                        >
                          Cancel
                        </button>
                      )}
                      <button
                        onClick={saveApiKey}
                        disabled={!newKey.trim() || saving}
                        style={{
                          ...primaryButtonStyle,
                          opacity: !newKey.trim() || saving ? 0.5 : 1,
                          cursor: !newKey.trim() || saving ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {saving ? 'Saving...' : 'Save API Key'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Additional Info */}
              <div style={{ marginTop: '32px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#1e293b', marginBottom: '12px' }}>
                  About BYOK (Bring Your Own Key)
                </h3>
                <div style={featureListStyle}>
                  <div style={featureItemStyle}>
                    <span style={{ color: '#10b981' }}>✓</span>
                    <span>Unlimited AI usage with no monthly caps</span>
                  </div>
                  <div style={featureItemStyle}>
                    <span style={{ color: '#10b981' }}>✓</span>
                    <span>Direct billing through your Anthropic account</span>
                  </div>
                  <div style={featureItemStyle}>
                    <span style={{ color: '#10b981' }}>✓</span>
                    <span>Full control over your API usage and costs</span>
                  </div>
                  <div style={featureItemStyle}>
                    <span style={{ color: '#10b981' }}>✓</span>
                    <span>Your key is encrypted and never shared</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Coming Soon Tabs */}
          {activeTab !== 'api-key' && (
            <div style={comingSoonStyle}>
              <div style={{ fontSize: '64px', marginBottom: '20px' }}>🚧</div>
              <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#1e293b', margin: '0 0 12px' }}>
                Coming Soon
              </h2>
              <p style={{ color: '#64748b', margin: 0 }}>
                This feature is under development and will be available soon.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Styles
const containerStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%)'
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '20px 40px',
  background: 'rgba(255,255,255,0.9)',
  backdropFilter: 'blur(10px)',
  borderBottom: '1px solid #e2e8f0'
}

const backButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#6366f1',
  fontSize: '15px',
  fontWeight: 500,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px 0'
}

const mainContentStyle: React.CSSProperties = {
  display: 'flex',
  maxWidth: '1200px',
  margin: '0 auto',
  padding: '40px'
}

const sidebarStyle: React.CSSProperties = {
  width: '260px',
  flexShrink: 0,
  paddingRight: '40px'
}

const menuItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  width: '100%',
  padding: '14px 18px',
  border: 'none',
  borderRadius: '12px',
  fontSize: '15px',
  fontWeight: 500,
  marginBottom: '8px',
  transition: 'all 0.2s ease',
  textAlign: 'left'
}

const contentAreaStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0
}

const sectionHeaderStyle: React.CSSProperties = {
  marginBottom: '24px'
}

const cardStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '16px',
  padding: '28px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  border: '1px solid #e2e8f0'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '14px',
  fontWeight: 600,
  color: '#374151',
  marginBottom: '10px'
}

const keyDisplayStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  background: '#f8fafc',
  padding: '16px 20px',
  borderRadius: '10px',
  border: '1px solid #e2e8f0'
}

const statusBadgeStyle: React.CSSProperties = {
  background: '#dcfce7',
  color: '#16a34a',
  padding: '6px 14px',
  borderRadius: '20px',
  fontSize: '13px',
  fontWeight: 600
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 18px',
  border: '2px solid #e2e8f0',
  borderRadius: '10px',
  fontSize: '15px',
  boxSizing: 'border-box',
  outline: 'none',
  transition: 'border-color 0.2s ease'
}

const infoBoxStyle: React.CSSProperties = {
  display: 'flex',
  gap: '14px',
  background: '#f0f9ff',
  border: '1px solid #bae6fd',
  borderRadius: '12px',
  padding: '18px'
}

const primaryButtonStyle: React.CSSProperties = {
  padding: '14px 28px',
  background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
  color: 'white',
  border: 'none',
  borderRadius: '10px',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const secondaryButtonStyle: React.CSSProperties = {
  padding: '14px 28px',
  background: 'white',
  color: '#374151',
  border: '2px solid #e2e8f0',
  borderRadius: '10px',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const dangerButtonStyle: React.CSSProperties = {
  padding: '14px 28px',
  background: 'white',
  color: '#dc2626',
  border: '2px solid #fecaca',
  borderRadius: '10px',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const featureListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px'
}

const featureItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  fontSize: '14px',
  color: '#475569'
}

const comingSoonStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'white',
  borderRadius: '16px',
  padding: '80px 40px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  border: '1px solid #e2e8f0',
  textAlign: 'center'
}