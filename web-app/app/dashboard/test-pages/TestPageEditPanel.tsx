'use client'
import { useState, useRef, useEffect } from 'react'

// ============ INTERFACES ============
export interface TestPage {
  id: number
  test_name: string
  url: string
  network_id: number
  network_name?: string
  test_case_description?: string
  status: 'not_mapped' | 'mapping' | 'mapped' | 'failed'
  mapping_session_id?: number
  created_at: string
  updated_at: string
}

export interface JunctionChoice {
  junction_id?: string
  junction_name: string
  option: string
  selector?: string
}

export interface CompletedPath {
  id: number
  path_number: number
  path_junctions: JunctionChoice[]
  steps: any[]
  steps_count: number
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface ThemeColors {
  bgGradient: string
  headerBg: string
  sidebarBg: string
  cardBg: string
  cardBorder: string
  cardGlow: string
  accentPrimary: string
  accentSecondary: string
  accentGlow: string
  iconGlow: string
  buttonGlow: string
  textPrimary: string
  textSecondary: string
  textGlow: string
  statusOnline: string
  statusGlow: string
  borderGlow: string
}

export interface TestPageEditPanelProps {
  editingTestPage: TestPage
  completedPaths: CompletedPath[]
  loadingPaths: boolean
  token: string
  editTestName: string
  setEditTestName: (name: string) => void
  editUrl: string
  setEditUrl: (url: string) => void
  editTestCaseDescription: string
  setEditTestCaseDescription: (desc: string) => void
  savingTestPage: boolean
  mappingTestPageIds: Set<number>
  mappingStatus: Record<number, { status: string; sessionId?: number; error?: string }>
  expandedPathId: number | null
  setExpandedPathId: (id: number | null) => void
  editingPathStep: { pathId: number; stepIndex: number } | null
  setEditingPathStep: (step: { pathId: number; stepIndex: number } | null) => void
  editedPathStepData: any
  setEditedPathStepData: (data: any) => void
  error: string | null
  setError: (error: string | null) => void
  message: string | null
  setMessage: (message: string | null) => void
  onClose: () => void
  onSave: () => void
  onStartMapping: (testPageId: number) => void
  onCancelMapping: (testPageId: number) => void
  onDeletePath: (pathId: number) => void
  onSavePathStep: (pathId: number, stepIndex: number, stepData?: any) => void
  onExportPath: (path: CompletedPath) => void
  onRefreshPaths: () => void
  onDeleteTestPage: (testPageId: number) => void
  getTheme: () => { name: string; colors: ThemeColors }
  isLightTheme: () => boolean
}

// ============ COMPONENT ============
export default function TestPageEditPanel({
  editingTestPage,
  completedPaths,
  loadingPaths,
  token,
  editTestName,
  setEditTestName,
  editUrl,
  setEditUrl,
  editTestCaseDescription,
  setEditTestCaseDescription,
  savingTestPage,
  mappingTestPageIds,
  mappingStatus,
  expandedPathId,
  setExpandedPathId,
  editingPathStep,
  setEditingPathStep,
  editedPathStepData,
  setEditedPathStepData,
  error,
  setError,
  message,
  setMessage,
  onClose,
  onSave,
  onStartMapping,
  onCancelMapping,
  onDeletePath,
  onSavePathStep,
  onExportPath,
  onRefreshPaths,
  onDeleteTestPage,
  getTheme,
  isLightTheme
}: TestPageEditPanelProps) {
  
  const theme = getTheme()
  
  // State
  const [localPathSteps, setLocalPathSteps] = useState<Record<number, any[]>>({})
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingTestPage, setDeletingTestPage] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editablePathIds, setEditablePathIds] = useState<Set<number>>(new Set())
  const [showMappingDropdown, setShowMappingDropdown] = useState(false)
  const [showMoreDropdown, setShowMoreDropdown] = useState(false)
  const mappingDropdownRef = useRef<HTMLDivElement>(null)
  const moreDropdownRef = useRef<HTMLDivElement>(null)
  
  // Spec Compliance state
  const [showSpecCompliancePanel, setShowSpecCompliancePanel] = useState(false)
  const [specContent, setSpecContent] = useState<string>('')
  const [specFilename, setSpecFilename] = useState<string>('')
  const [specLoading, setSpecLoading] = useState(false)
  const [specEditing, setSpecEditing] = useState(false)
  const [specEditContent, setSpecEditContent] = useState<string>('')
  const [specComplianceStatus, setSpecComplianceStatus] = useState<string>('idle')
  const [specComplianceReport, setSpecComplianceReport] = useState<string>('')
  const [specComplianceError, setSpecComplianceError] = useState<string | null>(null)
  const specFileInputRef = useRef<HTMLInputElement>(null)

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (mappingDropdownRef.current && !mappingDropdownRef.current.contains(event.target as Node)) {
        setShowMappingDropdown(false)
      }
      if (moreDropdownRef.current && !moreDropdownRef.current.contains(event.target as Node)) {
        setShowMoreDropdown(false)
      }
    }
    if (showMappingDropdown || showMoreDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showMappingDropdown, showMoreDropdown])
  
  const getPathSteps = (pathId: number, originalSteps: any[]) => {
    if (editablePathIds.has(pathId) && localPathSteps[pathId]) {
      return localPathSteps[pathId]
    }
    return originalSteps
  }
  
  const handleDeleteTestPage = async () => {
    setDeletingTestPage(true)
    try {
      await onDeleteTestPage(editingTestPage.id)
      setShowDeleteConfirm(false)
      onClose()
    } catch (err) {
      setError('Failed to delete test page')
    } finally {
      setDeletingTestPage(false)
    }
  }
  
  const handleSaveEdit = async () => {
    await onSave()
    setIsEditing(false)
  }
  
  const handleCancelEdit = () => {
    setEditTestName(editingTestPage.test_name)
    setEditUrl(editingTestPage.url)
    setEditTestCaseDescription(editingTestPage.test_case_description || '')
    setIsEditing(false)
  }
  
  // Spec handlers
  const handleSpecFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSpecLoading(true)
    setSpecFilename(file.name)
    try {
      const text = await file.text()
      setSpecContent(text)
    } catch (err) {
      setError('Failed to read spec file')
    } finally {
      setSpecLoading(false)
    }
  }
  
  const handleSpecSave = () => {
    setSpecContent(specEditContent)
    setSpecEditing(false)
  }
  
  const handleSpecDelete = () => {
    setSpecContent('')
    setSpecFilename('')
  }
  
  const handleGenerateSpecCompliance = async () => {
    if (!specContent || completedPaths.length === 0) return
    setSpecComplianceStatus('generating')
    setSpecComplianceError(null)
    try {
      const response = await fetch('/api/ai/spec-compliance', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spec_content: specContent,
          paths: completedPaths,
          test_page_name: editingTestPage.test_name
        })
      })
      if (response.ok) {
        const data = await response.json()
        if (data.task_id) {
          pollSpecComplianceStatus(data.task_id)
        } else if (data.report) {
          setSpecComplianceReport(data.report)
          setSpecComplianceStatus('completed')
        }
      } else {
        setSpecComplianceError('Failed to generate compliance report')
        setSpecComplianceStatus('error')
      }
    } catch (err) {
      setSpecComplianceError('Failed to generate compliance report')
      setSpecComplianceStatus('error')
    }
  }
  
  const pollSpecComplianceStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/ai/task-status/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
          const data = await response.json()
          if (data.status === 'completed') {
            clearInterval(interval)
            setSpecComplianceReport(data.result?.report || '')
            setSpecComplianceStatus('completed')
          } else if (data.status === 'failed') {
            clearInterval(interval)
            setSpecComplianceError(data.error || 'Task failed')
            setSpecComplianceStatus('error')
          }
        }
      } catch (err) {
        clearInterval(interval)
        setSpecComplianceError('Failed to check task status')
        setSpecComplianceStatus('error')
      }
    }, 2000)
  }

  const isMapping = mappingStatus[editingTestPage.id]?.sessionId ? true : false

  // ============ STYLES MATCHING ENTERPRISE ============
  const cardBg = 'linear-gradient(135deg, rgba(242, 246, 250, 0.98) 0%, rgba(242, 246, 250, 0.95) 100%)'
  const cardBorder = 'rgba(100, 116, 139, 0.25)'
  const textPrimary = '#1e293b'
  const textSecondary = '#64748b'
  const accentPrimary = '#0369a1'

  return (
    <div>
      {/* Back Button - Enterprise Style */}
      <button
        onClick={onClose}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: cardBg,
          border: `1px solid ${cardBorder}`,
          borderRadius: '10px',
          padding: '14px 24px',
          fontSize: '16px',
          fontWeight: 500,
          color: textPrimary,
          cursor: 'pointer',
          marginBottom: '24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
        }}
      >
        ← Back to Test Pages
      </button>

      {/* Messages */}
      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '12px',
          color: '#dc2626',
          marginBottom: '20px',
          fontSize: '16px'
        }}>
          <span>⚠️</span>
          <span style={{ flex: 1 }}>{error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '20px' }}>×</button>
        </div>
      )}
      {message && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px',
          background: 'rgba(34, 197, 94, 0.1)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '12px',
          color: '#16a34a',
          marginBottom: '20px',
          fontSize: '16px'
        }}>
          <span>✓</span>
          <span style={{ flex: 1 }}>{message}</span>
          <button onClick={() => setMessage(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '20px' }}>×</button>
        </div>
      )}

      {/* Header Card - Enterprise Style */}
      <div style={{
        background: cardBg,
        border: `1px solid ${cardBorder}`,
        borderRadius: '12px',
        padding: '20px 28px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <span style={{ fontSize: '28px' }}>📋</span>
          <div>
            <span style={{ fontSize: '18px', color: textSecondary }}>Test Page: </span>
            <span style={{ fontSize: '22px', fontWeight: 600, color: accentPrimary }}>{editingTestPage.test_name}</span>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Mapping Button - Show Stop when mapping, Dropdown when not */}
          {isMapping ? (
            mappingStatus[editingTestPage.id]?.status === 'stopping' ? (
              <button disabled style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '10px',
                background: 'rgba(245, 158, 11, 0.2)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                color: '#d97706',
                padding: '12px 20px',
                borderRadius: '10px',
                fontSize: '16px',
                fontWeight: 600,
                cursor: 'not-allowed'
              }}>
                <span style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid rgba(217, 119, 6, 0.3)',
                  borderTopColor: '#d97706',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }}></span>
                Stopping...
              </button>
            ) : (
              <button
                onClick={() => onCancelMapping(editingTestPage.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(239, 68, 68, 0.3)'
                }}
              >
                ⏹️ Stop Mapping
              </button>
            )
          ) : (
            <div style={{ position: 'relative' }} ref={mappingDropdownRef}>
              <button
                onClick={() => setShowMappingDropdown(!showMappingDropdown)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: '#fff',
                  border: `1px solid ${cardBorder}`,
                  color: textPrimary,
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 500,
                  cursor: 'pointer'
                }}
              >
                Mapping ▼
              </button>
              {showMappingDropdown && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '8px',
                  background: '#fff',
                  borderRadius: '12px',
                  boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                  border: `1px solid ${cardBorder}`,
                  minWidth: '220px',
                  zIndex: 100,
                  padding: '8px'
                }}>
                  <button
                    onClick={() => { onStartMapping(editingTestPage.id); setShowMappingDropdown(false); }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      width: '100%',
                      padding: '14px 18px',
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.25)',
                      borderRadius: '8px',
                      color: '#059669',
                      fontSize: '15px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <span>{completedPaths.length > 0 ? '🔄' : '🗺️'}</span>
                    <span>{completedPaths.length > 0 ? 'Remap Test Page' : 'Map Test Page'}</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* More Dropdown */}
          <div style={{ position: 'relative' }} ref={moreDropdownRef}>
            <button
              onClick={() => setShowMoreDropdown(!showMoreDropdown)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: '#fff',
                border: `1px solid ${cardBorder}`,
                color: textPrimary,
                padding: '12px 20px',
                borderRadius: '10px',
                fontSize: '16px',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              More ▼
            </button>
            {showMoreDropdown && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                background: '#fff',
                borderRadius: '12px',
                boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                border: `1px solid ${cardBorder}`,
                minWidth: '240px',
                zIndex: 100,
                padding: '8px'
              }}>
                <button
                  onClick={() => { setShowSpecCompliancePanel(true); setShowMoreDropdown(false); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    width: '100%',
                    padding: '14px 18px',
                    background: 'rgba(139, 92, 246, 0.1)',
                    border: '1px solid rgba(139, 92, 246, 0.25)',
                    borderRadius: '8px',
                    color: '#7c3aed',
                    fontSize: '15px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textAlign: 'left',
                    marginBottom: '8px'
                  }}
                >
                  <span>📋</span>
                  <span>Check Spec Compliance</span>
                </button>
                <button
                  onClick={() => { setShowDeleteConfirm(true); setShowMoreDropdown(false); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    width: '100%',
                    padding: '14px 18px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    borderRadius: '8px',
                    color: '#dc2626',
                    fontSize: '15px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <span>🗑️</span>
                  <span>Delete Test Page</span>
                </button>
              </div>
            )}
          </div>

          {/* Back Button */}
          <button
            onClick={onClose}
            style={{
              background: '#fff',
              border: `1px solid ${cardBorder}`,
              color: textPrimary,
              padding: '12px 24px',
              borderRadius: '10px',
              fontSize: '16px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Back
          </button>
        </div>
      </div>

      {/* Main Content - Two Column Layout Like Enterprise */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Left Column - Info Cards */}
        <div>
          {/* Edit Button */}
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                color: '#2563eb',
                padding: '12px 20px',
                borderRadius: '10px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                marginBottom: '20px'
              }}
            >
              ✏️ Edit Test Page Info
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
              <button
                onClick={handleSaveEdit}
                disabled={savingTestPage}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: savingTestPage ? 'not-allowed' : 'pointer',
                  opacity: savingTestPage ? 0.7 : 1
                }}
              >
                {savingTestPage ? '💾 Saving...' : '💾 Save Changes'}
              </button>
              <button
                onClick={handleCancelEdit}
                style={{
                  background: '#fff',
                  border: `1px solid ${cardBorder}`,
                  color: textPrimary,
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 500,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          )}

          {/* TEST NAME Card - Cyan like HIERARCHY */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.22) 0%, rgba(6, 182, 212, 0.15) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            borderRadius: '12px',
            padding: '20px 24px',
            marginBottom: '16px'
          }}>
            <div style={{ 
              fontSize: '14px', 
              fontWeight: 700, 
              color: '#0891b2', 
              marginBottom: '12px', 
              textTransform: 'uppercase', 
              letterSpacing: '1.5px' 
            }}>
              TEST NAME
            </div>
            {isEditing ? (
              <input
                type="text"
                value={editTestName}
                onChange={(e) => setEditTestName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(0,0,0,0.15)',
                  fontSize: '16px',
                  color: textPrimary,
                  background: '#fff',
                  boxSizing: 'border-box'
                }}
              />
            ) : (
              <div style={{ fontSize: '18px', color: textPrimary, fontWeight: 500 }}>
                {editingTestPage.test_name}
              </div>
            )}
          </div>

          {/* URL Card - Yellow/Orange like URL in enterprise */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.22) 0%, rgba(251, 191, 36, 0.15) 100%)',
            border: '1px solid rgba(251, 191, 36, 0.4)',
            borderRadius: '12px',
            padding: '20px 24px',
            marginBottom: '16px'
          }}>
            <div style={{ 
              fontSize: '14px', 
              fontWeight: 700, 
              color: '#d97706', 
              marginBottom: '12px', 
              textTransform: 'uppercase', 
              letterSpacing: '1.5px' 
            }}>
              URL
            </div>
            {isEditing ? (
              <input
                type="text"
                value={editUrl}
                onChange={(e) => setEditUrl(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(0,0,0,0.15)',
                  fontSize: '16px',
                  color: textPrimary,
                  background: '#fff',
                  boxSizing: 'border-box'
                }}
              />
            ) : (
              <a
                href={editingTestPage.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: accentPrimary, textDecoration: 'none', fontSize: '17px' }}
              >
                {editingTestPage.url}
              </a>
            )}
          </div>

          {/* TEST CASE DESCRIPTION Card */}
          <div style={{
            background: cardBg,
            border: `1px solid ${cardBorder}`,
            borderRadius: '12px',
            padding: '20px 24px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
          }}>
            <div style={{ 
              fontSize: '14px', 
              fontWeight: 700, 
              color: textSecondary, 
              marginBottom: '12px', 
              textTransform: 'uppercase', 
              letterSpacing: '1.5px' 
            }}>
              TEST CASE DESCRIPTION
            </div>
            {isEditing ? (
              <textarea
                value={editTestCaseDescription}
                onChange={(e) => setEditTestCaseDescription(e.target.value)}
                rows={6}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(0,0,0,0.15)',
                  fontSize: '16px',
                  color: textPrimary,
                  background: '#fff',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                  lineHeight: 1.6,
                  boxSizing: 'border-box'
                }}
              />
            ) : (
              <div style={{ 
                fontSize: '17px',
                color: textPrimary, 
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6
              }}>
                {editingTestPage.test_case_description || 'No description provided.'}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Completed Paths */}
        <div style={{
          background: cardBg,
          border: `1px solid ${cardBorder}`,
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
        }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '24px' }}>📊</span>
              <span style={{ fontSize: '18px', fontWeight: 600, color: textPrimary }}>
                Mapping Result
              </span>
              {completedPaths.length > 0 && (
                <span style={{
                  background: '#10b981',
                  color: 'white',
                  padding: '4px 14px',
                  borderRadius: '14px',
                  fontSize: '15px',
                  fontWeight: 600
                }}>
                  ✓ Mapped
                </span>
              )}
            </div>
            <button
              onClick={onRefreshPaths}
              disabled={loadingPaths}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: '#fff',
                border: `1px solid ${cardBorder}`,
                color: textSecondary,
                padding: '10px 18px',
                borderRadius: '8px',
                fontSize: '15px',
                cursor: loadingPaths ? 'not-allowed' : 'pointer',
                opacity: loadingPaths ? 0.6 : 1
              }}
            >
              🔄 Refresh
            </button>
          </div>

          {/* Content */}
          {loadingPaths ? (
            <div style={{ textAlign: 'center', padding: '50px', color: textSecondary, fontSize: '16px' }}>
              Loading paths...
            </div>
          ) : completedPaths.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px' }}>
              <div style={{ fontSize: '56px', marginBottom: '16px' }}>📋</div>
              <p style={{ margin: 0, color: textSecondary, fontSize: '18px' }}>Not mapped yet.</p>
              <p style={{ margin: '10px 0 0', color: textSecondary, fontSize: '15px' }}>Click "Map Test Page" to map this test case.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {completedPaths.map(path => (
                <div key={path.id} style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: '10px',
                  overflow: 'hidden'
                }}>
                  {/* Path Header */}
                  <div
                    onClick={() => setExpandedPathId(expandedPathId === path.id ? null : path.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '16px 20px',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{
                        width: '36px',
                        height: '36px',
                        background: '#10b981',
                        color: '#fff',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '16px',
                        fontWeight: 700
                      }}>
                        {path.path_number}
                      </div>
                      <div>
                        <div style={{ fontSize: '17px', fontWeight: 600, color: textPrimary }}>
                          Path {path.path_number}
                        </div>
                        <div style={{ fontSize: '14px', color: textSecondary }}>
                          {path.steps_count} steps
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button
                        onClick={(e) => { e.stopPropagation(); onExportPath(path); }}
                        style={{
                          background: '#fff',
                          border: `1px solid ${cardBorder}`,
                          color: textSecondary,
                          padding: '8px 14px',
                          borderRadius: '6px',
                          fontSize: '14px',
                          cursor: 'pointer'
                        }}
                      >
                        📥 Export
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); onDeletePath(path.id); }}
                        style={{
                          background: '#fff',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#ef4444',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          fontSize: '14px',
                          cursor: 'pointer'
                        }}
                      >
                        🗑️
                      </button>
                      <span style={{ 
                        fontSize: '18px',
                        color: textSecondary,
                        transform: expandedPathId === path.id ? 'rotate(180deg)' : 'rotate(0deg)',
                        display: 'inline-block',
                        transition: 'transform 0.2s ease'
                      }}>▼</span>
                    </div>
                  </div>

                  {/* Expanded Steps */}
                  {expandedPathId === path.id && (
                    <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(16, 185, 129, 0.2)', background: '#fff' }}>
                      <div style={{ fontSize: '15px', fontWeight: 600, color: textSecondary, marginBottom: '14px' }}>
                        Steps:
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {getPathSteps(path.id, path.steps || []).map((step: any, idx: number) => (
                          <div key={idx} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '14px',
                            padding: '14px',
                            background: 'rgba(0,0,0,0.02)',
                            borderRadius: '8px'
                          }}>
                            <div style={{
                              width: '28px',
                              height: '28px',
                              background: step.action === 'verify' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(156, 163, 175, 0.2)',
                              color: step.action === 'verify' ? '#2563eb' : textSecondary,
                              borderRadius: '50%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '13px',
                              fontWeight: 600
                            }}>
                              {step.step_number || idx + 1}
                            </div>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: '15px', color: textPrimary }}>
                                {step.description || `${step.action} on ${step.selector?.substring(0, 30)}...`}
                              </div>
                              <div style={{ fontSize: '13px', color: textSecondary }}>{step.action}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '24px'
        }} onClick={() => setShowDeleteConfirm(false)}>
          <div style={{
            background: '#fff',
            borderRadius: '16px',
            padding: '32px',
            width: '100%',
            maxWidth: '500px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
            border: `1px solid ${cardBorder}`
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 16px', fontSize: '22px', color: '#dc2626' }}>⚠️ Delete Test Page</h3>
            <p style={{ color: textSecondary, marginBottom: '24px', fontSize: '16px', lineHeight: '1.6' }}>
              Are you sure you want to delete "<strong>{editingTestPage.test_name}</strong>"?
              <br /><br />
              This will also delete all {completedPaths.length} completed path(s) and cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                style={{
                  background: '#fff',
                  border: `1px solid ${cardBorder}`,
                  color: textPrimary,
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '16px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteTestPage}
                disabled={deletingTestPage}
                style={{
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: deletingTestPage ? 'not-allowed' : 'pointer',
                  opacity: deletingTestPage ? 0.7 : 1
                }}
              >
                {deletingTestPage ? 'Deleting...' : '🗑️ Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Spec Compliance Panel */}
      {showSpecCompliancePanel && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '24px'
        }} onClick={() => setShowSpecCompliancePanel(false)}>
          <div style={{
            background: '#fff',
            borderRadius: '16px',
            padding: '32px',
            width: '100%',
            maxWidth: '700px',
            maxHeight: '80vh',
            overflowY: 'auto',
            boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
            border: `1px solid ${cardBorder}`
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ margin: 0, fontSize: '22px', color: '#7c3aed' }}>📋 Spec Compliance Check</h3>
              <button
                onClick={() => setShowSpecCompliancePanel(false)}
                style={{ background: 'none', border: 'none', fontSize: '28px', cursor: 'pointer', color: textSecondary }}
              >
                ×
              </button>
            </div>

            <input
              ref={specFileInputRef}
              type="file"
              accept=".txt,.md,.pdf,.docx"
              onChange={handleSpecFileUpload}
              style={{ display: 'none' }}
            />

            {!specContent ? (
              <div style={{
                border: '2px dashed rgba(139, 92, 246, 0.3)',
                borderRadius: '12px',
                padding: '48px 24px',
                textAlign: 'center',
                background: 'rgba(139, 92, 246, 0.05)'
              }}>
                <div style={{ fontSize: '56px', marginBottom: '16px' }}>📄</div>
                <p style={{ color: textPrimary, marginBottom: '8px', fontSize: '18px', fontWeight: 600 }}>
                  No spec document uploaded
                </p>
                <p style={{ color: textSecondary, marginBottom: '20px', fontSize: '15px' }}>
                  Upload a document to check compliance
                </p>
                <button
                  onClick={() => specFileInputRef.current?.click()}
                  disabled={specLoading}
                  style={{
                    background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                    color: '#fff',
                    border: 'none',
                    padding: '14px 28px',
                    borderRadius: '10px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: specLoading ? 'not-allowed' : 'pointer',
                    opacity: specLoading ? 0.7 : 1
                  }}
                >
                  {specLoading ? 'Uploading...' : '📤 Upload Spec File'}
                </button>
                <p style={{ color: textSecondary, fontSize: '13px', marginTop: '12px', marginBottom: 0 }}>
                  Supports: .txt, .md, .pdf, .docx
                </p>
              </div>
            ) : (
              <div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px',
                  padding: '14px 18px',
                  background: 'rgba(139, 92, 246, 0.08)',
                  borderRadius: '10px',
                  border: '1px solid rgba(139, 92, 246, 0.2)'
                }}>
                  <span style={{ color: textPrimary, fontSize: '15px', fontWeight: 500 }}>
                    📎 {specFilename}
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => specFileInputRef.current?.click()} style={{ background: 'rgba(0,0,0,0.05)', color: textPrimary, border: 'none', padding: '8px 14px', borderRadius: '6px', fontSize: '14px', cursor: 'pointer' }}>Replace</button>
                    <button onClick={() => { setSpecEditing(true); setSpecEditContent(specContent); }} style={{ background: 'rgba(0,0,0,0.05)', color: textPrimary, border: 'none', padding: '8px 14px', borderRadius: '6px', fontSize: '14px', cursor: 'pointer' }}>Edit</button>
                    <button onClick={handleSpecDelete} style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', padding: '8px 14px', borderRadius: '6px', fontSize: '14px', cursor: 'pointer' }}>🗑️</button>
                  </div>
                </div>

                {specEditing ? (
                  <div>
                    <textarea
                      value={specEditContent}
                      onChange={(e) => setSpecEditContent(e.target.value)}
                      style={{ width: '100%', minHeight: '200px', padding: '14px', borderRadius: '10px', border: `1px solid ${cardBorder}`, fontSize: '15px', fontFamily: 'monospace', resize: 'vertical', boxSizing: 'border-box' }}
                    />
                    <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
                      <button onClick={handleSpecSave} style={{ background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)', color: '#fff', border: 'none', padding: '12px 24px', borderRadius: '10px', fontSize: '15px', fontWeight: 600, cursor: 'pointer' }}>💾 Save</button>
                      <button onClick={() => setSpecEditing(false)} style={{ background: 'rgba(0,0,0,0.05)', color: textPrimary, border: 'none', padding: '12px 24px', borderRadius: '10px', fontSize: '15px', cursor: 'pointer' }}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div style={{ background: 'rgba(0,0,0,0.02)', borderRadius: '10px', padding: '18px', maxHeight: '200px', overflowY: 'auto', border: `1px solid ${cardBorder}` }}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '14px', color: textPrimary, fontFamily: 'Monaco, Consolas, monospace' }}>{specContent}</pre>
                  </div>
                )}

                {completedPaths.length > 0 && !specEditing && (
                  <button
                    onClick={handleGenerateSpecCompliance}
                    disabled={specComplianceStatus === 'generating'}
                    style={{
                      marginTop: '20px',
                      background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                      color: '#fff',
                      border: 'none',
                      padding: '16px 28px',
                      borderRadius: '10px',
                      fontSize: '16px',
                      fontWeight: 600,
                      cursor: specComplianceStatus === 'generating' ? 'not-allowed' : 'pointer',
                      width: '100%',
                      opacity: specComplianceStatus === 'generating' ? 0.7 : 1
                    }}
                  >
                    {specComplianceStatus === 'generating' ? '⏳ Generating Report...' : '📊 Generate Compliance Report'}
                  </button>
                )}
                
                {completedPaths.length === 0 && !specEditing && (
                  <p style={{ color: textSecondary, fontSize: '15px', marginTop: '16px', textAlign: 'center' }}>
                    ℹ️ Map this test page first to check spec compliance
                  </p>
                )}

                {specComplianceReport && (
                  <div style={{ marginTop: '20px', padding: '18px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '10px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: '#059669', marginBottom: '14px' }}>📊 Compliance Report</div>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '14px', color: textPrimary, fontFamily: 'inherit', lineHeight: 1.6 }}>{specComplianceReport}</pre>
                  </div>
                )}

                {specComplianceError && (
                  <div style={{ marginTop: '16px', padding: '14px 18px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '10px', color: '#dc2626', fontSize: '15px' }}>
                    ⚠️ {specComplianceError}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
