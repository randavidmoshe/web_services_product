'use client'
import { useState, useEffect } from 'react'

interface TwoFASetupModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  token: string
  isMandatory?: boolean
}

export default function TwoFASetupModal({ 
  isOpen, 
  onClose, 
  onSuccess, 
  token,
  isMandatory = false 
}: TwoFASetupModalProps) {
  const [qrCode, setQrCode] = useState('')
  const [secret, setSecret] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [setupLoading, setSetupLoading] = useState(false)

  useEffect(() => {
    if (isOpen && !qrCode) {
      initSetup()
    }
  }, [isOpen])

  const initSetup = async () => {
    setSetupLoading(true)
    setError('')
    
    try {
      const response = await fetch('/api/2fa/setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to initialize 2FA setup')
      }
      
      const data = await response.json()
      setQrCode(data.qr_code)
      setSecret(data.manual_entry_key)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSetupLoading(false)
    }
  }

  const verifyCode = async () => {
    if (verificationCode.length !== 6) {
      setError('Please enter a 6-digit code')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('/api/2fa/verify-setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: verificationCode })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Invalid code')
      }
      
      onSuccess()
    } catch (err: any) {
      setError(err.message)
      setVerificationCode('')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '32px',
        maxWidth: '440px',
        width: '100%',
        boxShadow: '0 25px 80px rgba(0, 0, 0, 0.3)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>🔐</div>
          <h2 style={{ margin: '0 0 8px', fontSize: '24px', fontWeight: 700, color: '#0A0E17' }}>
            Set Up Two-Factor Authentication
          </h2>
          <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
            {isMandatory 
              ? 'Two-factor authentication is required for your account'
              : 'Add an extra layer of security to your account'
            }
          </p>
        </div>

        {error && (
          <div style={{
            background: '#fee2e2',
            color: '#dc2626',
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}

        {setupLoading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p style={{ color: '#64748b' }}>Loading...</p>
          </div>
        ) : qrCode && (
          <>
            <div style={{ 
              background: '#f8fafc', 
              borderRadius: '12px', 
              padding: '20px',
              marginBottom: '20px'
            }}>
              <p style={{ margin: '0 0 16px', fontSize: '14px', color: '#374151', fontWeight: 500 }}>
                1. Scan this QR code with your authenticator app
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
                <img src={qrCode} alt="2FA QR Code" style={{ width: '200px', height: '200px', borderRadius: '8px' }} />
              </div>
              <p style={{ margin: '0 0 8px', fontSize: '12px', color: '#64748b', textAlign: 'center' }}>
                Or enter this code manually:
              </p>
              <div style={{
                background: '#e2e8f0',
                padding: '10px',
                borderRadius: '6px',
                fontFamily: 'monospace',
                fontSize: '14px',
                textAlign: 'center',
                wordBreak: 'break-all',
                color: '#0A0E17'
              }}>
                {secret}
              </div>
            </div>

            <p style={{ margin: '0 0 12px', fontSize: '14px', color: '#374151', fontWeight: 500 }}>
              2. Enter the 6-digit code from your app
            </p>
            <input
              type="text"
              maxLength={6}
              placeholder="000000"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '24px',
                textAlign: 'center',
                letterSpacing: '8px',
                border: '2px solid #e5e7eb',
                borderRadius: '10px',
                outline: 'none',
                boxSizing: 'border-box',
                fontFamily: 'monospace'
              }}
              autoFocus
            />

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              {!isMandatory && (
                <button
                  onClick={onClose}
                  style={{
                    flex: 1,
                    padding: '14px',
                    background: '#f1f5f9',
                    color: '#64748b',
                    border: 'none',
                    borderRadius: '10px',
                    fontSize: '15px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Skip for Now
                </button>
              )}
              <button
                onClick={verifyCode}
                disabled={loading || verificationCode.length !== 6}
                style={{
                  flex: 1,
                  padding: '14px',
                  background: loading || verificationCode.length !== 6 
                    ? '#94a3b8' 
                    : 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
                  color: '#0A0E17',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: loading || verificationCode.length !== 6 ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Verifying...' : 'Enable 2FA'}
              </button>
            </div>
          </>
        )}

        <p style={{ margin: '20px 0 0', fontSize: '12px', color: '#94a3b8', textAlign: 'center' }}>
          Recommended apps: Google Authenticator, Authy, or Microsoft Authenticator
        </p>
      </div>
    </div>
  )
}
