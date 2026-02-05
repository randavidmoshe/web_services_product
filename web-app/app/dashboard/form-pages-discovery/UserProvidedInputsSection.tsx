'use client'
import { useEffect, useState, useRef } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

interface UserProvidedInputsProps {
  formPageId: number
  apiBase: string
  isLightTheme: boolean
  themeColors: {
    textPrimary: string
    textSecondary: string
    accentPrimary: string
  }
}

interface UserInputsData {
  status: string
  inputs?: {
    field_values: { field_hint: string; value: string }[]
    file_paths: { field_hint: string; path: string }[]
  }
  raw_content?: string
}

export default function UserProvidedInputsSection({
  formPageId,
  apiBase,
  isLightTheme,
  themeColors
}: UserProvidedInputsProps) {
  const [userInputs, setUserInputs] = useState<UserInputsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [inputText, setInputText] = useState('')
  const [polling, setPolling] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch user inputs on mount and when formPageId changes
  useEffect(() => {
    fetchUserInputs()
  }, [formPageId])

  // Poll while status is 'parsing'
  useEffect(() => {
    if (userInputs?.status === 'parsing' && !polling) {
      setPolling(true)
      const interval = setInterval(async () => {
        const data = await fetchUserInputsData()
        if (data && data.status !== 'parsing') {
          clearInterval(interval)
          setPolling(false)
        }
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [userInputs?.status])

  const fetchUserInputsData = async (): Promise<UserInputsData | null> => {
    try {
      const res = await fetchWithAuth(`${apiBase}/api/form-mapper/form-pages/${formPageId}/user-inputs`)
      if (res.ok) {
        const data = await res.json()
        setUserInputs(data)
        return data
      }
    } catch (err) {
      console.error('Failed to fetch user inputs:', err)
    }
    return null
  }

  const fetchUserInputs = () => {
    fetchUserInputsData()
  }

  const uploadUserInputs = async (content: string) => {
    if (!content.trim()) return
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('content', content)

      const res = await fetchWithAuth(`${apiBase}/api/form-mapper/form-pages/${formPageId}/user-inputs`, {
        method: 'POST',
        body: formData
      })

      if (res.ok) {
        setShowModal(false)
        setInputText('')
        fetchUserInputs()
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to upload inputs')
      }
    } catch (err) {
      alert('Failed to upload inputs')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetchWithAuth(`${apiBase}/api/form-mapper/form-pages/${formPageId}/user-inputs`, {
        method: 'POST',
        body: formData
      })

      if (res.ok) {
        setShowModal(false)
        fetchUserInputs()
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to upload file')
      }
    } catch (err) {
      alert('Failed to upload file')
    } finally {
      setLoading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const clearUserInputs = async () => {
    if (!confirm('Are you sure you want to clear all field values?')) return
    try {
      await fetchWithAuth(`${apiBase}/api/form-mapper/form-pages/${formPageId}/user-inputs`, {
        method: 'DELETE'
      })
      setUserInputs(null)
      setInputText('')
    } catch (err) {
      console.error('Failed to clear inputs:', err)
    }
  }

  const openEditModal = () => {
    setInputText(userInputs?.raw_content || '')
    setShowModal(true)
  }

  const handleSave = () => {
    uploadUserInputs(inputText)
  }

  return (
    <>
      {/* Section - Separate from URL block */}
      <div style={{
        background: 'transparent',
        borderRadius: '10px',
        padding: '0'
      }}>
        {/* Header with info icon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <h4 style={{
            margin: 0,
            fontSize: '18px',
            color: themeColors.textSecondary,
            textTransform: 'uppercase',
            letterSpacing: '1px',
            fontWeight: 600
          }}>
            📋 Specific Field Values
          </h4>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowInfo(!showInfo)}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: '18px',
                padding: '2px 6px',
                borderRadius: '50%',
                color: themeColors.textSecondary
              }}
              title="Click for more info"
            >
              ⓘ
            </button>
            {showInfo && (
              <div style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: isLightTheme ? '#1e293b' : '#1e293b',
                color: '#fff',
                padding: '24px 28px',
                borderRadius: '16px',
                fontSize: '16px',
                width: '400px',
                zIndex: 2000,
                boxShadow: '0 20px 50px rgba(0,0,0,0.4)',
                lineHeight: 1.7
              }}>
                <p style={{ margin: '0 0 14px', fontWeight: 700, fontSize: '20px' }}>What is this?</p>
                <p style={{ margin: '0 0 14px', fontSize: '16px' }}>
                  Provide values for fields where you need specific inputs instead of random/generated values.
                </p>
                <p style={{ margin: '0 0 14px', fontSize: '16px' }}>
                  <strong>Examples:</strong> Database ports, AD usernames, config file paths, license keys
                </p>
                <p style={{ margin: 0, color: '#fca5a5', fontSize: '16px' }}>
                  ⚠️ Not for test scenario fields - only for technical/system values that must be exact.
                </p>
                <button
                  onClick={() => setShowInfo(false)}
                  style={{
                    position: 'absolute',
                    top: '12px',
                    right: '12px',
                    background: 'transparent',
                    border: 'none',
                    color: '#fff',
                    fontSize: '20px',
                    cursor: 'pointer',
                    opacity: 0.7
                  }}
                >
                  ×
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Content based on state */}
        {userInputs?.status === 'parsing' ? (
          <div style={{ color: themeColors.textSecondary, fontSize: '16px', padding: '12px 0' }}>
            ⏳ Parsing inputs...
          </div>
        ) : userInputs?.status === 'ready' && userInputs.inputs ? (
          <div>
            <div style={{
              fontSize: '18px',
              color: themeColors.textPrimary,
              marginBottom: '14px',
              fontWeight: 500
            }}>
              ✓ {userInputs.inputs.field_values?.length || 0} field values, {userInputs.inputs.file_paths?.length || 0} file paths
            </div>
            
            {/* Field values list */}
            <div style={{ 
              background: isLightTheme ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.2)',
              borderRadius: '8px',
              padding: '14px',
              marginBottom: '14px'
            }}>
              {userInputs.inputs.field_values?.map((fv, i) => (
                <div key={`fv-${i}`} style={{
                  fontSize: '18px',
                  color: themeColors.textSecondary,
                  marginBottom: '8px',
                  display: 'flex',
                  gap: '10px'
                }}>
                  <span>•</span>
                  <span><strong>{fv.field_hint}:</strong> <span style={{ color: themeColors.textPrimary }}>{fv.value}</span></span>
                </div>
              ))}
              {userInputs.inputs.file_paths?.map((fp, i) => (
                <div key={`fp-${i}`} style={{
                  fontSize: '15px',
                  color: themeColors.textSecondary,
                  marginBottom: '8px',
                  display: 'flex',
                  gap: '10px'
                }}>
                  <span>📁</span>
                  <span><strong>{fp.field_hint}:</strong> <code style={{ 
                    color: themeColors.textPrimary, 
                    fontSize: '14px',
                    background: isLightTheme ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)',
                    padding: '3px 8px',
                    borderRadius: '4px'
                  }}>{fp.path}</code></span>
                </div>
              ))}
            </div>

            {/* Edit and Clear buttons */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={openEditModal} style={{
                background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                border: 'none',
                color: '#fff',
                padding: '10px 18px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                ✏️ Edit
              </button>
              <button onClick={clearUserInputs} style={{
                background: 'transparent',
                border: `1px solid ${isLightTheme ? '#dc2626' : '#ef4444'}`,
                color: isLightTheme ? '#dc2626' : '#ef4444',
                padding: '10px 18px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                🗑️ Clear
              </button>
            </div>
          </div>
        ) : (
          /* No values yet - show add buttons */
          <div>
            <p style={{
              fontSize: '16px',
              color: themeColors.textPrimary,
              margin: '0 0 16px',
              lineHeight: 1.5
            }}>
              No field values configured. Add values that must be exact (not random).
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button onClick={() => setShowModal(true)} style={{
                background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                color: '#fff',
                border: 'none',
                padding: '12px 20px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                ✏️ Enter Values
              </button>
              <label style={{
                border: `1px solid ${isLightTheme ? '#8b5cf6' : '#a78bfa'}`,
                color: isLightTheme ? '#7c3aed' : '#a78bfa',
                color: isLightTheme ? '#0ea5e9' : themeColors.accentPrimary,
                padding: '12px 20px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                📁 Upload File
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.json,.csv"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Modal for entering/editing values */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '24px'
        }} onClick={() => setShowModal(false)}>
          <div style={{
            background: isLightTheme
              ? 'linear-gradient(135deg, #ffffff, #f8fafc)'
              : 'linear-gradient(135deg, rgba(75, 85, 99, 0.98), rgba(55, 65, 81, 0.98))',
            borderRadius: '24px',
            padding: '32px',
            width: '100%',
            maxWidth: '600px',
            boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
            border: isLightTheme ? '1px solid #e2e8f0' : '1px solid rgba(255,255,255,0.12)'
          }} onClick={e => e.stopPropagation()}>
            <h2 style={{
              margin: '0 0 8px',
              color: themeColors.textPrimary,
              fontSize: '22px'
            }}>
              📋 Specific Field Values
            </h2>
            <p style={{
              color: themeColors.textSecondary,
              fontSize: '14px',
              margin: '0 0 8px'
            }}>
              Enter field names and values, one per line.
            </p>
            <p style={{
              color: themeColors.textSecondary,
              fontSize: '13px',
              margin: '0 0 20px',
              opacity: 0.8
            }}>
              Format: <code style={{ 
                background: isLightTheme ? '#f1f5f9' : 'rgba(255,255,255,0.1)',
                padding: '2px 6px',
                borderRadius: '4px'
              }}>Field Name: value</code>
            </p>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={`Database Port: 5432
AD Username: DOMAIN\\admin
Config File: C:\\Users\\john\\config.xml
Certificate: C:\\certs\\client.pfx`}
              style={{
                width: '100%',
                height: '200px',
                padding: '16px',
                border: isLightTheme ? '1px solid #d1d5db' : '1px solid rgba(255,255,255,0.12)',
                borderRadius: '12px',
                fontSize: '14px',
                fontFamily: 'monospace',
                boxSizing: 'border-box',
                background: isLightTheme ? '#f9fafb' : 'rgba(255,255,255,0.05)',
                color: themeColors.textPrimary,
                outline: 'none',
                resize: 'vertical'
              }}
            />
            
            {/* Or upload file */}
            <div style={{
              marginTop: '16px',
              paddingTop: '16px',
              borderTop: `1px solid ${isLightTheme ? '#e2e8f0' : 'rgba(255,255,255,0.1)'}`,
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ color: themeColors.textSecondary, fontSize: '14px' }}>Or</span>
              <label style={{
                background: 'transparent',
                border: `1px solid ${themeColors.textSecondary}`,
                color: themeColors.textSecondary,
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                📁 Upload File (.txt, .json, .csv)
                <input
                  type="file"
                  accept=".txt,.json,.csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      const reader = new FileReader()
                      reader.onload = (event) => {
                        setInputText(event.target?.result as string || '')
                      }
                      reader.readAsText(file)
                    }
                  }}
                  style={{ display: 'none' }}
                />
              </label>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px',
              marginTop: '24px'
            }}>
              <button onClick={() => setShowModal(false)} style={{
                background: 'transparent',
                border: isLightTheme ? '1px solid #d1d5db' : '1px solid rgba(255,255,255,0.2)',
                color: themeColors.textSecondary,
                padding: '12px 24px',
                borderRadius: '10px',
                fontSize: '15px',
                cursor: 'pointer'
              }}>Cancel</button>
              <button
                onClick={handleSave}
                disabled={loading || !inputText.trim()}
                style={{
                  background: themeColors.accentPrimary,
                  color: '#fff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading || !inputText.trim() ? 0.6 : 1
                }}
              >
                {loading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
