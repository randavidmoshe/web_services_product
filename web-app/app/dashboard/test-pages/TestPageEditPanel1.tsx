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
  // Data
  editingTestPage: TestPage
  completedPaths: CompletedPath[]
  loadingPaths: boolean
  token: string
  
  // Edit state
  editTestName: string
  setEditTestName: (name: string) => void
  editUrl: string
  setEditUrl: (url: string) => void
  editTestCaseDescription: string
  setEditTestCaseDescription: (desc: string) => void
  savingTestPage: boolean
  
  // Mapping state
  mappingTestPageIds: Set<number>
  mappingStatus: Record<number, { status: string; sessionId?: number; error?: string }>
  
  // Path editing state
  expandedPathId: number | null
  setExpandedPathId: (id: number | null) => void
  editingPathStep: { pathId: number; stepIndex: number } | null
  setEditingPathStep: (step: { pathId: number; stepIndex: number } | null) => void
  editedPathStepData: any
  setEditedPathStepData: (data: any) => void
  
  // Messages
  error: string | null
  setError: (error: string | null) => void
  message: string | null
  setMessage: (message: string | null) => void
  
  // Functions
  onClose: () => void
  onSave: () => void
  onStartMapping: (testPageId: number) => void
  onCancelMapping: (testPageId: number) => void
  onDeletePath: (pathId: number) => void
  onSavePathStep: (pathId: number, stepIndex: number, stepData?: any) => void
  onExportPath: (path: CompletedPath) => void
  onRefreshPaths: () => void
  onDeleteTestPage: (testPageId: number) => void
  
  // Theme
  getTheme: () => { name: string; colors: ThemeColors }
  isLightTheme: () => boolean
}

// ============ STYLES ============
const errorBoxStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '16px 20px',
  background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1))',
  border: '1px solid rgba(239, 68, 68, 0.3)',
  borderRadius: '12px',
  color: '#ef4444',
  marginBottom: '20px',
  animation: 'fadeIn 0.3s ease'
}

const successBoxStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '16px 20px',
  background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(22, 163, 74, 0.1))',
  border: '1px solid rgba(34, 197, 94, 0.3)',
  borderRadius: '12px',
  color: '#86efac',
  marginBottom: '20px',
  animation: 'fadeIn 0.3s ease'
}

const modalOverlayStyle: React.CSSProperties = {
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
}

const smallModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(75, 85, 99, 0.98), rgba(55, 65, 81, 0.98))',
  borderRadius: '24px',
  padding: '40px',
  width: '100%',
  maxWidth: '500px',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
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
  
  // Action types available in agent_selenium
  const ACTION_TYPES = [
    'click', 'fill', 'type', 'select', 'hover', 'scroll', 'slider', 'drag_and_drop',
    'press_key', 'clear', 'wait_for_visible', 'double_click', 'wait_for_hidden',
    'switch_to_window', 'switch_to_parent_window', 'refresh', 'check', 'uncheck',
    'wait', 'wait_dom_ready', 'wait_for_ready', 'switch_to_frame', 'switch_to_default', 'switch_to_shadow_root',
    'accept_alert', 'dismiss_alert', 'fill_alert', 'navigate', 'create_file',
    'upload_file', 'verify', 'verify_login_page'
  ]
  
  // Local state for expanded steps (key: pathId-stepIndex)
  const [expandedPathSteps, setExpandedPathSteps] = useState<Set<string>>(new Set())
  // Local state to track edited step data before save
  const [localEditedStepData, setLocalEditedStepData] = useState<Record<string, any>>({})
  // Local state for edited path steps (full array per path)
  const [localPathSteps, setLocalPathSteps] = useState<Record<number, any[]>>({})
  
  // Delete confirmation state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingTestPage, setDeletingTestPage] = useState(false)
  
  // Path editing mode state
  const [editablePathIds, setEditablePathIds] = useState<Set<number>>(new Set())
  const [showEditPathWarning, setShowEditPathWarning] = useState<number | null>(null)
  const [modifiedPathIds, setModifiedPathIds] = useState<Set<number>>(new Set())

  // Dropdown state
  const [showMappingDropdown, setShowMappingDropdown] = useState(false)
  const [showMoreDropdown, setShowMoreDropdown] = useState(false)
  const mappingDropdownRef = useRef<HTMLDivElement>(null)
  const moreDropdownRef = useRef<HTMLDivElement>(null)

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

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showMappingDropdown, showMoreDropdown])
  
  // Check if a path is in edit mode
  const isPathEditable = (pathId: number) => editablePathIds.has(pathId)
  
  // Mark a path as modified
  const markPathAsModified = (pathId: number) => {
    setModifiedPathIds(prev => new Set([...prev, pathId]))
  }
  
  // Enable editing for a path
  const enablePathEditing = (pathId: number) => {
    setEditablePathIds(prev => new Set([...prev, pathId]))
    setShowEditPathWarning(null)
  }
  
  // Get steps for a path (local edits if editing enabled, otherwise original)
  const getPathSteps = (pathId: number, originalSteps: any[]) => {
    if (editablePathIds.has(pathId) && localPathSteps[pathId]) {
      return localPathSteps[pathId]
    }
    return originalSteps
  }
  
  // Toggle step expanded/collapsed
  const toggleStepExpanded = (pathId: number, stepIndex: number, step: any) => {
    const key = `${pathId}-${stepIndex}`
    setExpandedPathSteps(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
        setLocalEditedStepData(prev => {
          const newData = { ...prev }
          delete newData[key]
          return newData
        })
      } else {
        next.add(key)
        const currentSteps = localPathSteps[pathId]
        const currentStep = currentSteps ? currentSteps[stepIndex] : step
        setLocalEditedStepData(prev => ({
          ...prev,
          [key]: {
            action: currentStep?.action || '',
            selector: currentStep?.selector || '',
            value: currentStep?.value || currentStep?.input_value || '',
            description: currentStep?.description || ''
          }
        }))
      }
      return next
    })
  }
  
  // Update local edit data for a step field
  const updateLocalStepField = (pathId: number, stepIndex: number, field: string, value: string) => {
    const key = `${pathId}-${stepIndex}`
    
    setLocalEditedStepData(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value
      }
    }))
    
    setLocalPathSteps(prev => {
      let steps: any[]
      if (!prev[pathId]) {
        const path = completedPaths.find(p => p.id === pathId)
        steps = path?.steps ? path.steps.map(s => ({ ...s })) : []
      } else {
        steps = prev[pathId].map(s => ({ ...s }))
      }
      
      if (steps[stepIndex]) {
        steps[stepIndex] = { ...steps[stepIndex], [field]: value }
      }
      return { ...prev, [pathId]: steps }
    })
    
    markPathAsModified(pathId)
  }
  
  // Save single step changes
  const handleSaveStep = async (pathId: number, stepIndex: number) => {
    const key = `${pathId}-${stepIndex}`
    const editData = localEditedStepData[key]
    if (editData) {
      await onSavePathStep(pathId, stepIndex, editData)
      setExpandedPathSteps(prev => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
      setLocalEditedStepData(prev => {
        const newData = { ...prev }
        delete newData[key]
        return newData
      })
    }
  }
  
  // Handle delete test page
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

  // Check if currently mapping
  const isMapping = mappingTestPageIds.has(editingTestPage.id) || editingTestPage.status === 'mapping'
  const currentMappingStatus = mappingStatus[editingTestPage.id]

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-start',
      padding: '40px',
      zIndex: 100,
      overflowY: 'auto'
    }}>
      <div style={{
        background: isLightTheme() ? '#fff' : getTheme().colors.cardBg,
        borderRadius: '20px',
        width: '100%',
        maxWidth: '1400px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
        border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)'}`
      }}>
        {/* Header */}
        <div style={{
          padding: '24px 28px',
          borderBottom: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
          background: isLightTheme() ? 'linear-gradient(135deg, #f0f9ff, #e0f2fe)' : 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05))',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '32px' }}>🧪</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '22px', color: getTheme().colors.textPrimary, fontWeight: 700 }}>
                {editingTestPage.test_name}
              </h2>
              <p style={{ margin: '4px 0 0', fontSize: '14px', color: getTheme().colors.textSecondary }}>
                Test Page Configuration
              </p>
            </div>
            {/* Status Badge */}
            <span style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: 600,
              background: editingTestPage.status === 'mapped' 
                ? (isLightTheme() ? '#dcfce7' : 'rgba(34, 197, 94, 0.2)')
                : editingTestPage.status === 'mapping'
                ? (isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.2)')
                : editingTestPage.status === 'failed'
                ? (isLightTheme() ? '#fee2e2' : 'rgba(239, 68, 68, 0.2)')
                : (isLightTheme() ? '#f3f4f6' : 'rgba(156, 163, 175, 0.2)'),
              color: editingTestPage.status === 'mapped'
                ? (isLightTheme() ? '#166534' : '#4ade80')
                : editingTestPage.status === 'mapping'
                ? (isLightTheme() ? '#92400e' : '#fbbf24')
                : editingTestPage.status === 'failed'
                ? (isLightTheme() ? '#991b1b' : '#f87171')
                : getTheme().colors.textSecondary
            }}>
              {editingTestPage.status === 'mapped' ? `✓ ${completedPaths.length} Path${completedPaths.length !== 1 ? 's' : ''}` :
               editingTestPage.status === 'mapping' ? '⏳ Mapping...' :
               editingTestPage.status === 'failed' ? '✗ Failed' : 'Not Mapped'}
            </span>
          </div>
          
          <div style={{ display: 'flex', gap: '12px' }}>
            {/* Mapping Dropdown */}
            {!isMapping && (
              <div style={{ position: 'relative' }} ref={mappingDropdownRef}>
                <button
                  onClick={() => setShowMappingDropdown(!showMappingDropdown)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                    border: 'none',
                    color: '#fff',
                    padding: '14px 20px',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                  }}
                >
                  🗺️ Mapping ▼
                </button>
                {showMappingDropdown && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '8px',
                    background: isLightTheme() ? '#fff' : '#1f2937',
                    borderRadius: '16px',
                    boxShadow: '0 20px 50px rgba(0,0,0,0.25)',
                    border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)'}`,
                    minWidth: '240px',
                    zIndex: 100,
                    overflow: 'hidden',
                    padding: '8px'
                  }}>
                    <button
                      onClick={() => { onStartMapping(editingTestPage.id); setShowMappingDropdown(false); }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        width: '100%',
                        padding: '12px 16px',
                        background: isLightTheme() ? '#d1fae5' : 'rgba(16, 185, 129, 0.25)',
                        border: `1px solid ${isLightTheme() ? '#6ee7b7' : 'rgba(16, 185, 129, 0.4)'}`,
                        borderRadius: '10px',
                        color: isLightTheme() ? '#065f46' : '#6ee7b7',
                        fontSize: '14px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textAlign: 'left',
                        marginBottom: '8px'
                      }}
                    >
                      <span style={{ fontSize: '18px' }}>{completedPaths.length > 0 ? '🔄' : '🗺️'}</span>
                      <span>{completedPaths.length > 0 ? 'Remap Test Page' : 'Map Test Page'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Cancel Mapping button */}
            {isMapping && (
              <button
                onClick={() => onCancelMapping(editingTestPage.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  border: 'none',
                  color: '#fff',
                  padding: '14px 20px',
                  borderRadius: '12px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                ⏹️ Cancel Mapping
              </button>
            )}

            {/* More Dropdown */}
            <div style={{ position: 'relative' }} ref={moreDropdownRef}>
              <button
                onClick={() => setShowMoreDropdown(!showMoreDropdown)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.08)',
                  border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.12)'}`,
                  color: getTheme().colors.textPrimary,
                  padding: '14px 20px',
                  borderRadius: '12px',
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
                  background: isLightTheme() ? '#fff' : '#1f2937',
                  borderRadius: '16px',
                  boxShadow: '0 20px 50px rgba(0,0,0,0.25)',
                  border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)'}`,
                  minWidth: '200px',
                  zIndex: 100,
                  padding: '8px'
                }}>
                  {/* Delete */}
                  <button
                    onClick={() => { setShowDeleteConfirm(true); setShowMoreDropdown(false); }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      width: '100%',
                      padding: '12px 16px',
                      background: isLightTheme() ? '#fee2e2' : 'rgba(239, 68, 68, 0.25)',
                      border: `1px solid ${isLightTheme() ? '#fca5a5' : 'rgba(239, 68, 68, 0.4)'}`,
                      borderRadius: '10px',
                      color: isLightTheme() ? '#991b1b' : '#fca5a5',
                      fontSize: '14px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <span style={{ fontSize: '18px' }}>🗑️</span>
                    <span>Delete Test Page</span>
                  </button>
                </div>
              )}
            </div>

            <button
              onClick={onClose}
              style={{
                background: isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.08)',
                border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.12)'}`,
                color: getTheme().colors.textSecondary,
                padding: '14px 24px',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Back
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ padding: '0 28px' }}>
          {error && (
            <div style={{ ...errorBoxStyle, marginTop: '20px' }}>
              <span style={{ fontSize: '20px' }}>⚠️</span>
              <span style={{ flex: 1 }}>{error}</span>
              <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
            </div>
          )}
          {message && (
            <div style={{ ...successBoxStyle, marginTop: '20px' }}>
              <span style={{ fontSize: '20px' }}>✓</span>
              <span style={{ flex: 1 }}>{message}</span>
              <button onClick={() => setMessage(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '18px' }}>×</button>
            </div>
          )}
        </div>

        {/* Two Column Layout */}
        <div style={{ display: 'flex' }}>
          {/* Left Column - Test Page Info */}
          <div style={{
            flex: 1,
            minWidth: '400px',
            maxWidth: '500px',
            padding: '28px',
            borderRight: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.08)'}`,
            background: isLightTheme() ? '#f0fdf4' : 'rgba(16, 185, 129, 0.05)'
          }}>
            {/* URL Info */}
            <div style={{
              background: isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.1)',
              borderRadius: '10px',
              padding: '20px',
              border: `1px solid ${isLightTheme() ? '#fcd34d' : 'rgba(245, 158, 11, 0.2)'}`,
              marginBottom: '20px'
            }}>
              <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: isLightTheme() ? '#92400e' : '#fbbf24', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>URL</h4>
              <a
                href={editingTestPage.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: isLightTheme() ? '#1e40af' : '#93c5fd',
                  fontSize: '15px',
                  wordBreak: 'break-all',
                  textDecoration: 'none'
                }}
              >
                {editingTestPage.url} ↗
              </a>
            </div>

            {/* Network Info */}
            {editingTestPage.network_name && (
              <div style={{
                background: isLightTheme() ? '#dbeafe' : 'rgba(59, 130, 246, 0.1)',
                borderRadius: '10px',
                padding: '20px',
                border: `1px solid ${isLightTheme() ? '#93c5fd' : 'rgba(59, 130, 246, 0.2)'}`,
                marginBottom: '20px'
              }}>
                <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: isLightTheme() ? '#1e40af' : '#93c5fd', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>Network</h4>
                <span style={{ fontSize: '16px', color: getTheme().colors.textPrimary }}>{editingTestPage.network_name}</span>
              </div>
            )}

            {/* Test Case Description */}
            <div style={{
              background: isLightTheme() ? '#ede9fe' : 'rgba(139, 92, 246, 0.1)',
              borderRadius: '10px',
              padding: '20px',
              border: `1px solid ${isLightTheme() ? '#c4b5fd' : 'rgba(139, 92, 246, 0.2)'}`,
              marginBottom: '20px'
            }}>
              <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: isLightTheme() ? '#5b21b6' : '#c4b5fd', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>Test Case Description</h4>
              <p style={{ 
                fontSize: '15px', 
                color: getTheme().colors.textPrimary, 
                margin: 0,
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6'
              }}>
                {editingTestPage.test_case_description || 'No test case description provided.'}
              </p>
            </div>

            {/* Mapping Status - when mapping */}
            {isMapping && currentMappingStatus && (
              <div style={{
                background: isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.1)',
                borderRadius: '10px',
                padding: '20px',
                border: `1px solid ${isLightTheme() ? '#fcd34d' : 'rgba(245, 158, 11, 0.2)'}`,
                marginBottom: '20px'
              }}>
                <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: isLightTheme() ? '#92400e' : '#fbbf24', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>Mapping Status</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '24px' }}>⏳</span>
                  <span style={{ fontSize: '16px', color: getTheme().colors.textPrimary }}>
                    {currentMappingStatus.status || 'In Progress...'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Completed Paths */}
          <div style={{ flex: 2, padding: '28px' }}>
            {/* Paths Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                background: isLightTheme() ? '#d1fae5' : 'rgba(16, 185, 129, 0.15)',
                padding: '10px 16px',
                borderRadius: '10px'
              }}>
                <span style={{ fontSize: '20px' }}>📊</span>
                <span style={{ fontSize: '16px', fontWeight: 600, color: isLightTheme() ? '#065f46' : '#6ee7b7' }}>
                  Completed Mapping Paths
                </span>
                <span style={{
                  background: isLightTheme() ? '#10b981' : 'rgba(16, 185, 129, 0.3)',
                  color: '#fff',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  fontSize: '14px',
                  fontWeight: 600
                }}>
                  {completedPaths.length}
                </span>
              </div>
              <button
                onClick={onRefreshPaths}
                disabled={loadingPaths}
                style={{
                  background: 'transparent',
                  border: `1px solid ${getTheme().colors.accentPrimary}`,
                  color: getTheme().colors.accentPrimary,
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  cursor: loadingPaths ? 'not-allowed' : 'pointer',
                  opacity: loadingPaths ? 0.6 : 1
                }}
              >
                {loadingPaths ? '⏳ Loading...' : '🔄 Refresh'}
              </button>
            </div>

            {/* Paths List */}
            {completedPaths.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '40px',
                color: getTheme().colors.textSecondary,
                background: isLightTheme() ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.02)',
                borderRadius: '12px',
                border: `2px dashed ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.08)'}`
              }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>📋</div>
                <p style={{ fontSize: '16px', margin: 0 }}>No completed paths yet.</p>
                <p style={{ fontSize: '14px', margin: '8px 0 0', opacity: 0.7 }}>Click "Map Test Page" to discover paths through this page.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {completedPaths.map((path) => (
                  <div key={path.id} style={{
                    background: isLightTheme() ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '12px',
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
                        cursor: 'pointer',
                        background: isLightTheme() ? 'rgba(16, 185, 129, 0.05)' : 'rgba(16, 185, 129, 0.08)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{
                          width: '36px',
                          height: '36px',
                          background: isLightTheme() ? '#10b981' : 'rgba(16, 185, 129, 0.3)',
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
                          <div style={{ fontSize: '18px', fontWeight: 600, color: getTheme().colors.textPrimary }}>
                            Path {path.path_number}
                          </div>
                          <div style={{ fontSize: '15px', color: getTheme().colors.textSecondary }}>
                            {path.steps_count} steps • {path.path_junctions?.length || 0} junctions
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); onExportPath(path); }}
                          style={{
                            background: 'transparent',
                            border: `1px solid ${getTheme().colors.textSecondary}`,
                            color: getTheme().colors.textSecondary,
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
                            background: 'transparent',
                            border: '1px solid #ef4444',
                            color: '#ef4444',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            fontSize: '13px',
                            cursor: 'pointer'
                          }}
                        >
                          🗑️
                        </button>
                        <span style={{ 
                          fontSize: '18px',
                          color: getTheme().colors.textSecondary,
                          transform: expandedPathId === path.id ? 'rotate(180deg)' : 'rotate(0deg)',
                          display: 'inline-block',
                          transition: 'transform 0.2s ease'
                        }}>▼</span>
                      </div>
                    </div>

                    {/* Path Steps (Expanded) */}
                    {expandedPathId === path.id && (
                      <div style={{ padding: '20px', borderTop: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'}` }}>
                        {/* Junction Choices */}
                        {path.path_junctions && path.path_junctions.length > 0 && (
                          <div style={{ marginBottom: '20px' }}>
                            <div style={{ fontSize: '16px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '10px' }}>
                              Junction Choices:
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                              {path.path_junctions.map((jc, i) => (
                                <span key={i} style={{
                                  background: isLightTheme() ? '#dbeafe' : 'rgba(59, 130, 246, 0.2)',
                                  color: isLightTheme() ? '#1e40af' : '#93c5fd',
                                  padding: '8px 14px',
                                  borderRadius: '8px',
                                  fontSize: '15px',
                                  fontWeight: 500
                                }}>
                                  {jc.junction_name}: {jc.option}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Steps */}
                        <div style={{ fontSize: '16px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '12px' }}>
                          Steps:
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {getPathSteps(path.id, path.steps || []).map((step: any, stepIndex: number) => {
                            const key = `${path.id}-${stepIndex}`
                            const isExpanded = expandedPathSteps.has(key)
                            const editData = localEditedStepData[key]
                            const editable = isPathEditable(path.id)
                            
                            return (
                              <div key={stepIndex} style={{
                                background: isLightTheme() ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.02)',
                                border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)'}`,
                                borderRadius: '10px',
                                overflow: 'hidden'
                              }}>
                                {/* Step Header */}
                                <div 
                                  onClick={() => toggleStepExpanded(path.id, stepIndex, step)}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px',
                                    padding: '12px 16px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  <div style={{
                                    width: '28px',
                                    height: '28px',
                                    background: step.action === 'verify' 
                                      ? (isLightTheme() ? '#dbeafe' : 'rgba(59, 130, 246, 0.3)')
                                      : (isLightTheme() ? '#e5e7eb' : 'rgba(156, 163, 175, 0.2)'),
                                    color: step.action === 'verify'
                                      ? (isLightTheme() ? '#1e40af' : '#93c5fd')
                                      : getTheme().colors.textSecondary,
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '13px',
                                    fontWeight: 600
                                  }}>
                                    {step.step_number || stepIndex + 1}
                                  </div>
                                  <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: '14px', fontWeight: 500, color: getTheme().colors.textPrimary }}>
                                      {step.description || `${step.action} on ${step.selector?.substring(0, 40)}...`}
                                    </div>
                                    <div style={{ fontSize: '13px', color: getTheme().colors.textSecondary }}>
                                      {step.action}
                                    </div>
                                  </div>
                                  <span style={{ 
                                    fontSize: '14px',
                                    color: getTheme().colors.textSecondary,
                                    transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                    transition: 'transform 0.2s ease'
                                  }}>▼</span>
                                </div>

                                {/* Step Details (Expanded) */}
                                {isExpanded && (
                                  <div style={{ padding: '16px', borderTop: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'}`, background: isLightTheme() ? '#f9fafb' : 'rgba(0,0,0,0.1)' }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                                      <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Action</label>
                                        {editable ? (
                                          <select
                                            value={editData?.action || step.action || ''}
                                            onChange={(e) => updateLocalStepField(path.id, stepIndex, 'action', e.target.value)}
                                            style={{
                                              width: '100%',
                                              padding: '8px 10px',
                                              borderRadius: '6px',
                                              border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                                              background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                              color: getTheme().colors.textPrimary,
                                              fontSize: '14px'
                                            }}
                                          >
                                            {ACTION_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
                                          </select>
                                        ) : (
                                          <div style={{ padding: '8px 10px', background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '14px', color: getTheme().colors.textPrimary }}>
                                            {step.action}
                                          </div>
                                        )}
                                      </div>
                                      <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Value</label>
                                        {editable ? (
                                          <input
                                            type="text"
                                            value={editData?.value || step.value || step.input_value || ''}
                                            onChange={(e) => updateLocalStepField(path.id, stepIndex, 'value', e.target.value)}
                                            style={{
                                              width: '100%',
                                              padding: '8px 10px',
                                              borderRadius: '6px',
                                              border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                                              background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                              color: getTheme().colors.textPrimary,
                                              fontSize: '14px',
                                              boxSizing: 'border-box'
                                            }}
                                          />
                                        ) : (
                                          <div style={{ padding: '8px 10px', background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '14px', color: getTheme().colors.textPrimary }}>
                                            {step.value || step.input_value || '-'}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Selector</label>
                                      {editable ? (
                                        <input
                                          type="text"
                                          value={editData?.selector || step.selector || ''}
                                          onChange={(e) => updateLocalStepField(path.id, stepIndex, 'selector', e.target.value)}
                                          style={{
                                            width: '100%',
                                            padding: '8px 10px',
                                            borderRadius: '6px',
                                            border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                                            background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                            color: getTheme().colors.textPrimary,
                                            fontSize: '14px',
                                            fontFamily: 'monospace',
                                            boxSizing: 'border-box'
                                          }}
                                        />
                                      ) : (
                                        <div style={{ padding: '8px 10px', background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '14px', color: getTheme().colors.textPrimary, fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                          {step.selector || '-'}
                                        </div>
                                      )}
                                    </div>
                                    {editable && (
                                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                                        <button
                                          onClick={() => handleSaveStep(path.id, stepIndex)}
                                          style={{
                                            background: 'linear-gradient(135deg, #10b981, #059669)',
                                            color: '#fff',
                                            border: 'none',
                                            padding: '8px 16px',
                                            borderRadius: '6px',
                                            fontSize: '13px',
                                            fontWeight: 600,
                                            cursor: 'pointer'
                                          }}
                                        >
                                          💾 Save Step
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>

                        {/* Edit Path button */}
                        {!isPathEditable(path.id) && (
                          <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                            <button
                              onClick={() => {
                                if (showEditPathWarning === path.id) {
                                  enablePathEditing(path.id)
                                } else {
                                  setShowEditPathWarning(path.id)
                                }
                              }}
                              style={{
                                background: showEditPathWarning === path.id 
                                  ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                                  : 'transparent',
                                border: `1px solid ${showEditPathWarning === path.id ? '#f59e0b' : getTheme().colors.textSecondary}`,
                                color: showEditPathWarning === path.id ? '#fff' : getTheme().colors.textSecondary,
                                padding: '8px 16px',
                                borderRadius: '8px',
                                fontSize: '14px',
                                cursor: 'pointer'
                              }}
                            >
                              {showEditPathWarning === path.id ? '⚠️ Click again to enable editing' : '✏️ Edit Steps'}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div style={modalOverlayStyle} onClick={() => setShowDeleteConfirm(false)}>
          <div style={smallModalContentStyle} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 20px', fontSize: '22px', color: '#f87171' }}>⚠️ Delete Test Page</h3>
            <p style={{ color: '#e5e7eb', marginBottom: '24px', fontSize: '16px', lineHeight: '1.6' }}>
              Are you sure you want to delete "<strong>{editingTestPage.test_name}</strong>"?
              <br /><br />
              This will also delete all {completedPaths.length} completed path(s) and cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                style={{
                  background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
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
                  fontSize: '15px',
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
    </div>
  )
}
