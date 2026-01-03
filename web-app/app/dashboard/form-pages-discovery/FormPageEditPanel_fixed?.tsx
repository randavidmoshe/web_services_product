'use client'
import { useState, useRef } from 'react'
import UserProvidedInputsSection from './UserProvidedInputsSection'

// ============ INTERFACES ============
export interface NavigationStep {
  action: string
  selector?: string
  value?: string
  name?: string
  description?: string
}

export interface FormPage {
  id: number
  form_name: string
  url: string
  network_id: number
  navigation_steps: NavigationStep[]
  is_root: boolean
  parent_form_id: number | null
  parent_form_name?: string
  children?: FormPage[]
  created_at: string
  mapping_status?: 'not_mapped' | 'mapping' | 'mapped' | 'failed'
  mapping_session_id?: number
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

export interface FormPageEditPanelProps {
  // Data
  editingFormPage: FormPage
  formPages: FormPage[]
  completedPaths: CompletedPath[]
  loadingPaths: boolean
  token: string
  
  // Edit state
  editFormName: string
  setEditFormName: (name: string) => void
  editNavigationSteps: NavigationStep[]
  setEditNavigationSteps: React.Dispatch<React.SetStateAction<NavigationStep[]>>
  savingFormPage: boolean
  expandedSteps: Set<number>
  setExpandedSteps: React.Dispatch<React.SetStateAction<Set<number>>>
  
  // Mapping state
  mappingFormIds: Set<number>
  mappingStatus: Record<number, { status: string; sessionId?: number; error?: string }>
  
  // Path editing state
  expandedPathId: number | null
  setExpandedPathId: (id: number | null) => void
  editingPathStep: { pathId: number; stepIndex: number } | null
  setEditingPathStep: (step: { pathId: number; stepIndex: number } | null) => void
  editedPathStepData: any
  setEditedPathStepData: (data: any) => void
  
  // Delete step state
  showDeleteStepConfirm: boolean
  setShowDeleteStepConfirm: (show: boolean) => void
  stepToDeleteIndex: number | null
  setStepToDeleteIndex: (index: number | null) => void
  
  // Messages
  error: string | null
  setError: (error: string | null) => void
  message: string | null
  setMessage: (message: string | null) => void
  
  // Functions
  onClose: () => void
  onSave: () => void
  onStartMapping: (formPageId: number) => void
  onCancelMapping: (formPageId: number) => void
  onOpenEditPanel: (formPage: FormPage) => void
  onDeletePath: (pathId: number) => void
  onSavePathStep: (pathId: number, stepIndex: number, stepData?: any) => void
  onExportPath: (path: CompletedPath) => void
  onRefreshPaths: () => void
  onDeleteFormPage: (formPageId: number) => void
  
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
  color: '#fca5a5',
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

const closeButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: 'inherit',
  fontSize: '20px',
  cursor: 'pointer',
  marginLeft: 'auto',
  padding: '0 8px',
  opacity: 0.7
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
export default function FormPageEditPanel({
  editingFormPage,
  formPages,
  completedPaths,
  loadingPaths,
  token,
  editFormName,
  setEditFormName,
  editNavigationSteps,
  setEditNavigationSteps,
  savingFormPage,
  expandedSteps,
  setExpandedSteps,
  mappingFormIds,
  mappingStatus,
  expandedPathId,
  setExpandedPathId,
  editingPathStep,
  setEditingPathStep,
  editedPathStepData,
  setEditedPathStepData,
  showDeleteStepConfirm,
  setShowDeleteStepConfirm,
  stepToDeleteIndex,
  setStepToDeleteIndex,
  error,
  setError,
  message,
  setMessage,
  onClose,
  onSave,
  onStartMapping,
  onCancelMapping,
  onOpenEditPanel,
  onDeletePath,
  onSavePathStep,
  onExportPath,
  onRefreshPaths,
  onDeleteFormPage,
  getTheme,
  isLightTheme
}: FormPageEditPanelProps) {
  
  // Action types available in agent_selenium
  const ACTION_TYPES = [
    'click', 'fill', 'select', 'hover', 'scroll', 'slider', 'drag_and_drop',
    'press_key', 'clear', 'wait_for_visible', 'double_click', 'wait_for_hidden',
    'switch_to_window', 'switch_to_parent_window', 'refresh', 'check', 'uncheck',
    'wait', 'switch_to_frame', 'switch_to_default', 'switch_to_shadow_root',
    'accept_alert', 'dismiss_alert', 'fill_alert', 'navigate', 'create_file',
    'upload_file', 'verify'
  ]
  
  // Local state for expanded steps (key: pathId-stepIndex)
  const [expandedPathSteps, setExpandedPathSteps] = useState<Set<string>>(new Set())
  // Local state to track edited step data before save
  const [localEditedStepData, setLocalEditedStepData] = useState<Record<string, any>>({})
  // Local state for edited path steps (full array per path)
  const [localPathSteps, setLocalPathSteps] = useState<Record<number, any[]>>({})
  // Drag state
  const [draggedStep, setDraggedStep] = useState<{ pathId: number; index: number } | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  
  // POM Export state
  const [showPomModal, setShowPomModal] = useState(false)
  const [pomLanguage, setPomLanguage] = useState('python')
  const [pomFramework, setPomFramework] = useState('selenium')
  const [pomStyle, setPomStyle] = useState('basic')
  const [pomTaskId, setPomTaskId] = useState<string | null>(null)
  const [pomStatus, setPomStatus] = useState<string>('idle')
  const [pomCode, setPomCode] = useState<string>('')
  const [pomError, setPomError] = useState<string | null>(null)
  
  // Rediscover confirmation modal state
  const [showRediscoverModal, setShowRediscoverModal] = useState(false)
  const [deletingFormPage, setDeletingFormPage] = useState(false)
  
  // Path editing mode state
  const [editablePathIds, setEditablePathIds] = useState<Set<number>>(new Set())
  const [showEditPathWarning, setShowEditPathWarning] = useState<number | null>(null)
  const [modifiedPathIds, setModifiedPathIds] = useState<Set<number>>(new Set())
  
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
  
  // Initialize local path steps when path editing is enabled
  const initializeLocalPathSteps = (pathId: number, steps: any[]) => {
    // Only initialize if editing is enabled for this path
    if (editablePathIds.has(pathId) && !localPathSteps[pathId]) {
      setLocalPathSteps(prev => ({
        ...prev,
        [pathId]: [...steps]
      }))
    }
  }
  
  // Get steps for a path (local edits if editing enabled, otherwise original)
  const getPathSteps = (pathId: number, originalSteps: any[]) => {
    // Only use local steps if path is editable and has local edits
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
        // Clear local edit data when collapsing
        setLocalEditedStepData(prev => {
          const newData = { ...prev }
          delete newData[key]
          return newData
        })
      } else {
        next.add(key)
        // Initialize local edit data with current step values
        // Use localPathSteps if available (for unsaved changes), otherwise original step
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
  
  // Check if step is a verify step
  const isVerifyStep = (step: any): boolean => {
    const action = (step.action || '').toLowerCase()
    return action === 'verify' || action === 'assert' || action === 'check'
  }
  
  // Update local edit data for a step field
  const updateLocalStepField = (pathId: number, stepIndex: number, field: string, value: string) => {
    const key = `${pathId}-${stepIndex}`
    
    // Update localEditedStepData
    setLocalEditedStepData(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value
      }
    }))
    
    // Also update in localPathSteps - make sure we have a proper copy
    setLocalPathSteps(prev => {
      let steps: any[]
      if (!prev[pathId]) {
        // Find the path in completedPaths to get original steps
        const path = completedPaths.find(p => p.id === pathId)
        // Deep clone the steps array
        steps = path?.steps ? path.steps.map(s => ({ ...s })) : []
      } else {
        // Deep clone existing local steps
        steps = prev[pathId].map(s => ({ ...s }))
      }
      
      if (steps[stepIndex]) {
        steps[stepIndex] = { ...steps[stepIndex], [field]: value }
      }
      return { ...prev, [pathId]: steps }
    })
    
    // Mark path as modified
    markPathAsModified(pathId)
  }
  
  // Save single step changes
  const handleSaveStep = async (pathId: number, stepIndex: number) => {
    const key = `${pathId}-${stepIndex}`
    const editData = localEditedStepData[key]
    if (editData) {
      await onSavePathStep(pathId, stepIndex, editData)
      onRefreshPaths()
      // Clear local state for this path after save
      setLocalPathSteps(prev => {
        const newState = { ...prev }
        delete newState[pathId]
        return newState
      })
      // Clear modified flag
      setModifiedPathIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(pathId)
        return newSet
      })
      toggleStepExpanded(pathId, stepIndex, {})
    }
  }
  
  // Add new step after index - shows prompt for step type
  const handleAddStepAfter = (pathId: number, afterIndex: number, steps: any[], isVerifyStep: boolean = false) => {
    const newStep = isVerifyStep 
      ? {
          action: 'verify',
          selector: '',
          value: '',
          description: 'New verify step'
        }
      : {
          action: 'click',
          selector: '',
          value: '',
          description: 'New action step'
        }
    
    setLocalPathSteps(prev => {
      const currentSteps = prev[pathId] || [...steps]
      const newSteps = [...currentSteps]
      newSteps.splice(afterIndex + 1, 0, newStep)
      return { ...prev, [pathId]: newSteps }
    })
    
    // Mark path as modified
    markPathAsModified(pathId)
    
    // Auto-expand the new step for editing
    const newStepIndex = afterIndex + 1
    const key = `${pathId}-${newStepIndex}`
    setExpandedPathSteps(prev => new Set(prev).add(key))
    setLocalEditedStepData(prev => ({
      ...prev,
      [key]: { ...newStep }
    }))
  }
  
  // Show add step options
  const [addStepMenu, setAddStepMenu] = useState<{ pathId: number; afterIndex: number; steps: any[] } | null>(null)
  
  // Duplicate step
  const handleDuplicateStep = (pathId: number, stepIndex: number, steps: any[]) => {
    setLocalPathSteps(prev => {
      const currentSteps = prev[pathId] || [...steps]
      const stepToDuplicate = { ...currentSteps[stepIndex] }
      stepToDuplicate.description = (stepToDuplicate.description || '') + ' (copy)'
      const newSteps = [...currentSteps]
      newSteps.splice(stepIndex + 1, 0, stepToDuplicate)
      return { ...prev, [pathId]: newSteps }
    })
    // Mark path as modified
    markPathAsModified(pathId)
  }
  
  // Delete step
  const handleDeletePathStep = (pathId: number, stepIndex: number, steps: any[]) => {
    if (!confirm(`Delete step ${stepIndex + 1}?`)) return
    
    setLocalPathSteps(prev => {
      const currentSteps = prev[pathId] || [...steps]
      const newSteps = currentSteps.filter((_, i) => i !== stepIndex)
      return { ...prev, [pathId]: newSteps }
    })
    
    // Mark path as modified
    markPathAsModified(pathId)
    
    // Clear expanded state for this and subsequent steps
    setExpandedPathSteps(prev => {
      const next = new Set(prev)
      next.delete(`${pathId}-${stepIndex}`)
      return next
    })
  }
  
  // Handle drag start
  const handleDragStart = (pathId: number, index: number) => {
    setDraggedStep({ pathId, index })
  }
  
  // Handle drag over
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    setDragOverIndex(index)
  }
  
  // Handle drop
  const handleDrop = (pathId: number, dropIndex: number, steps: any[]) => {
    if (!draggedStep || draggedStep.pathId !== pathId) return
    
    const fromIndex = draggedStep.index
    if (fromIndex === dropIndex) {
      setDraggedStep(null)
      setDragOverIndex(null)
      return
    }
    
    setLocalPathSteps(prev => {
      const currentSteps = prev[pathId] || [...steps]
      const newSteps = [...currentSteps]
      const [movedStep] = newSteps.splice(fromIndex, 1)
      newSteps.splice(dropIndex, 0, movedStep)
      return { ...prev, [pathId]: newSteps }
    })
    
    // Mark path as modified
    markPathAsModified(pathId)
    
    setDraggedStep(null)
    setDragOverIndex(null)
  }
  
  // Save all path steps to DB
  const handleSaveAllPathSteps = async (pathId: number) => {
    // Get base steps from localPathSteps or from completedPaths
    let steps = localPathSteps[pathId]
    if (!steps) {
      const path = completedPaths.find(p => p.id === pathId)
      steps = path?.steps ? path.steps.map(s => ({ ...s })) : []
    } else {
      steps = steps.map(s => ({ ...s }))
    }
    
    if (steps.length === 0) return
    
    // IMPORTANT: Merge in any currently edited step data from localEditedStepData
    // This ensures we capture edits that may not have synced to localPathSteps yet
    Object.keys(localEditedStepData).forEach(key => {
      const [keyPathId, keyStepIndex] = key.split('-').map(Number)
      if (keyPathId === pathId && steps[keyStepIndex]) {
        const editData = localEditedStepData[key]
        steps[keyStepIndex] = { ...steps[keyStepIndex], ...editData }
      }
    })
    
    try {
      const response = await fetch(
        `/api/form-mapper/paths/${pathId}/steps`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ steps })
        }
      )
      
      if (response.ok) {
        setMessage('All steps saved successfully!')
        // Update localPathSteps with the saved steps so UI shows correct data immediately
        setLocalPathSteps(prev => ({
          ...prev,
          [pathId]: steps
        }))
        setExpandedPathSteps(new Set())
        setLocalEditedStepData({})
        // Clear modified flag
        setModifiedPathIds(prev => {
          const newSet = new Set(prev)
          newSet.delete(pathId)
          return newSet
        })
        // Refresh paths to get server data
        onRefreshPaths()
      } else {
        setError('Failed to save steps')
      }
    } catch (err) {
      console.error('Failed to save steps:', err)
      setError('Failed to save steps')
    }
  }
  
  // Check if path has unsaved changes (only if user actually made changes)
  const hasUnsavedChanges = (pathId: number) => {
    return modifiedPathIds.has(pathId)
  }
  
  // POM Generation functions
  const handleExportPom = () => {
    setShowPomModal(true)
    setPomStatus('idle')
    setPomCode('')
    setPomError(null)
    setPomTaskId(null)
  }

  const startPomGeneration = async () => {
    setPomStatus('starting')
    setPomError(null)
    
    try {
      const response = await fetch('/api/form-mapper/pom/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_page_route_id: editingFormPage.id,
          language: pomLanguage,
          framework: pomFramework,
          style: pomLanguage === 'java' ? pomStyle : 'basic'
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to start POM generation')
      }
      
      const data = await response.json()
      setPomTaskId(data.task_id)
      setPomStatus('processing')
      pollPomStatus(data.task_id)
    } catch (err: any) {
      setPomError(err.message)
      setPomStatus('failed')
    }
  }

  const pollPomStatus = async (taskId: string) => {
    const maxAttempts = 60
    let attempts = 0
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/form-mapper/pom/tasks/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (!response.ok) {
          throw new Error('Failed to get task status')
        }
        
        const data = await response.json()
        
        if (data.status === 'completed') {
          setPomCode(data.code || '')
          setPomStatus('completed')
          return
        } else if (data.status === 'failed') {
          setPomError(data.error || 'Generation failed')
          setPomStatus('failed')
          return
        }
        
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000)
        } else {
          setPomError('Timeout waiting for generation')
          setPomStatus('failed')
        }
      } catch (err: any) {
        setPomError(err.message)
        setPomStatus('failed')
      }
    }
    
    poll()
  }

  const copyPomToClipboard = () => {
    navigator.clipboard.writeText(pomCode)
    setMessage('POM code copied to clipboard!')
  }

  const downloadPomFile = () => {
    const extensionMap: Record<string, string> = {
      'python': 'py',
      'javascript': 'js',
      'typescript': 'ts',
      'java': 'java',
      'csharp': 'cs'
    }
    const extension = extensionMap[pomLanguage] || 'txt'
    const filename = `${editingFormPage.form_name.replace(/\s+/g, '')}Page.${extension}`
    const blob = new Blob([pomCode], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
  
  // Rediscover form page handler
  const handleRediscoverFormPage = () => {
    setShowRediscoverModal(true)
  }
  
  const confirmRediscoverFormPage = async () => {
    setDeletingFormPage(true)
    await onDeleteFormPage(editingFormPage.id)
    setDeletingFormPage(false)
    setShowRediscoverModal(false)
  }
  
  // Local functions
  const getCurrentFormPageIndex = () => {
    return formPages.findIndex(fp => fp.id === editingFormPage.id)
  }

  const navigateToPreviousFormPage = () => {
    const currentIndex = getCurrentFormPageIndex()
    if (currentIndex > 0) {
      onOpenEditPanel(formPages[currentIndex - 1])
    }
  }

  const navigateToNextFormPage = () => {
    const currentIndex = getCurrentFormPageIndex()
    if (currentIndex < formPages.length - 1) {
      onOpenEditPanel(formPages[currentIndex + 1])
    }
  }

  const updateNavigationStep = (index: number, field: keyof NavigationStep, value: string) => {
    setEditNavigationSteps(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const confirmDeleteStep = (index: number) => {
    setStepToDeleteIndex(index)
    setShowDeleteStepConfirm(true)
  }

  const deleteStep = () => {
    if (stepToDeleteIndex === null) return
    setEditNavigationSteps(prev => prev.filter((_, i) => i !== stepToDeleteIndex))
    setShowDeleteStepConfirm(false)
    setStepToDeleteIndex(null)
  }

  const addStepAtEnd = () => {
    setEditNavigationSteps(prev => [...prev, { action: 'click', selector: '', description: '' }])
  }

  const addStepAfter = (index: number) => {
    setEditNavigationSteps(prev => {
      const newSteps = [...prev]
      newSteps.splice(index + 1, 0, { action: 'click', selector: '', description: '' })
      return newSteps
    })
  }

  const toggleNavStepExpanded = (index: number) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const formatStepDescription = (step: any): string => {
    if (step.description) return step.description
    if (step.name) return step.name
    
    const action = step.action || 'unknown'
    const selector = step.selector || step.locator || ''
    const value = step.value || step.input_value || ''
    
    if (action === 'click') return `Click • ${selector.substring(0, 50)}${selector.length > 50 ? '...' : ''}`
    if (action === 'fill' || action === 'type') return `Fill "${value}" • ${selector.substring(0, 30)}...`
    if (action === 'select') return `Select "${value}" • ${selector.substring(0, 30)}...`
    
    return `${action} • ${selector.substring(0, 40)}...`
  }

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto' }}>
      {/* CSS Animations */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .step-card:hover {
          border-color: ${getTheme().colors.accentPrimary}66 !important;
        }
        .expand-btn:hover {
          background: ${getTheme().colors.accentPrimary}25 !important;
        }
      `}</style>

      {error && (
        <div style={errorBoxStyle}>
          <span>❌</span> {error}
          <button onClick={() => setError(null)} style={closeButtonStyle}>×</button>
        </div>
      )}
      {message && (
        <div style={successBoxStyle}>
          <span>✅</span> {message}
          <button onClick={() => setMessage(null)} style={closeButtonStyle}>×</button>
        </div>
      )}

      {/* Back Button and Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
        <button
          onClick={onClose}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            background: getTheme().colors.cardBg,
            border: `2px solid ${getTheme().colors.cardBorder}`,
            color: getTheme().colors.textSecondary,
            padding: '14px 24px',
            borderRadius: '14px',
            fontSize: '16px',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: getTheme().colors.cardGlow
          }}
        >
          <span style={{ fontSize: '20px' }}>←</span>
          Back to Form Pages
        </button>

        {/* Previous / Next Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={navigateToPreviousFormPage}
            disabled={getCurrentFormPageIndex() <= 0}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: getCurrentFormPageIndex() <= 0 
                ? (isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)')
                : (isLightTheme() ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.2)'),
              border: `1px solid ${getCurrentFormPageIndex() <= 0 
                ? (isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)')
                : (isLightTheme() ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.4)')}`,
              color: getCurrentFormPageIndex() <= 0 
                ? getTheme().colors.textSecondary
                : (isLightTheme() ? '#3b82f6' : '#93c5fd'),
              padding: '10px 18px',
              borderRadius: '10px',
              fontSize: '14px',
              fontWeight: 500,
              cursor: getCurrentFormPageIndex() <= 0 ? 'not-allowed' : 'pointer',
              opacity: getCurrentFormPageIndex() <= 0 ? 0.5 : 1,
              transition: 'all 0.2s ease'
            }}
          >
            <span style={{ fontSize: '16px' }}>←</span>
            Previous
          </button>

          <span style={{ 
            fontSize: '14px', 
            color: getTheme().colors.textSecondary,
            padding: '0 8px'
          }}>
            {getCurrentFormPageIndex() + 1} / {formPages.length}
          </span>

          <button
            onClick={navigateToNextFormPage}
            disabled={getCurrentFormPageIndex() >= formPages.length - 1}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: getCurrentFormPageIndex() >= formPages.length - 1
                ? (isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)')
                : (isLightTheme() ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.2)'),
              border: `1px solid ${getCurrentFormPageIndex() >= formPages.length - 1
                ? (isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)')
                : (isLightTheme() ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.4)')}`,
              color: getCurrentFormPageIndex() >= formPages.length - 1
                ? getTheme().colors.textSecondary
                : (isLightTheme() ? '#3b82f6' : '#93c5fd'),
              padding: '10px 18px',
              borderRadius: '10px',
              fontSize: '14px',
              fontWeight: 500,
              cursor: getCurrentFormPageIndex() >= formPages.length - 1 ? 'not-allowed' : 'pointer',
              opacity: getCurrentFormPageIndex() >= formPages.length - 1 ? 0.5 : 1,
              transition: 'all 0.2s ease'
            }}
          >
            Next
            <span style={{ fontSize: '16px' }}>→</span>
          </button>
        </div>
      </div>

      {/* Main Content Card */}
      <div style={{
        background: isLightTheme() ? '#ffffff' : getTheme().colors.cardBg,
        borderRadius: '24px',
        border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : getTheme().colors.cardBorder}`,
        boxShadow: isLightTheme() 
          ? '0 4px 20px rgba(0,0,0,0.08)' 
          : getTheme().colors.cardGlow,
        overflow: 'hidden'
      }}>
        {/* Header with Form Name and Actions */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '24px 32px',
          borderBottom: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
          background: isLightTheme() 
            ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(147, 51, 234, 0.05))'
            : 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))'
        }}>
          <h2 style={{ 
            margin: 0, 
            fontSize: '26px', 
            color: getTheme().colors.textPrimary,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <span style={{ fontSize: '28px' }}>📄</span>
            Form Page: <span style={{ color: getTheme().colors.accentPrimary }}>{editingFormPage.form_name}</span>
          </h2>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {/* Mapping Button Logic */}
            {mappingFormIds.has(editingFormPage.id) ? (
              mappingStatus[editingFormPage.id]?.status === 'stopping' ? (
                <button disabled style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  color: '#fbbf24',
                  padding: '14px 28px',
                  borderRadius: '12px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'not-allowed'
                }}>
                  <span className="spinner" style={{
                    width: '18px',
                    height: '18px',
                    border: '2px solid rgba(251, 191, 36, 0.3)',
                    borderTopColor: '#fbbf24',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></span>
                  Stopping...
                </button>
              ) : (
                <button
                  onClick={() => {
                    console.log('🛑 Stop Mapping clicked, formPageId:', editingFormPage.id)
                    onCancelMapping(editingFormPage.id)
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                    border: 'none',
                    color: '#fff',
                    padding: '14px 28px',
                    borderRadius: '12px',
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
              <>
                {/* Rediscover Form Page Button */}
                <button
                  onClick={handleRediscoverFormPage}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                    border: 'none',
                    color: '#fff',
                    padding: '14px 28px',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 4px 15px rgba(245, 158, 11, 0.3)'
                  }}
                >
                  🔍 Rediscover Form Page
                </button>
                
                {/* Map/Remap Button */}
                <button
                  onClick={() => onStartMapping(editingFormPage.id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                    border: 'none',
                    color: '#fff',
                    padding: '14px 28px',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                  }}
                >
                  {completedPaths.length > 0 ? '🔄 Heal/Remap Form Page' : '🗺️ Map Form Page'}
                </button>
              </>
            )}

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
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={savingFormPage}
              style={{
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                border: 'none',
                color: '#fff',
                padding: '14px 28px',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: 600,
                cursor: savingFormPage ? 'not-allowed' : 'pointer',
                opacity: savingFormPage ? 0.7 : 1,
                boxShadow: '0 4px 15px rgba(59, 130, 246, 0.3)'
              }}
            >
              {savingFormPage ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Two Column Layout */}
        <div style={{ display: 'flex' }}>
          {/* Left Column - Form Info */}
          <div style={{
            width: '380px',
            padding: '28px',
            borderRight: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.08)'}`,
            background: isLightTheme() ? '#f0fdf4' : 'rgba(16, 185, 129, 0.05)'
          }}>
            {/* Hierarchy Info */}
            <div style={{
              background: isLightTheme() ? '#dcfce7' : 'rgba(16, 185, 129, 0.1)',
              borderRadius: '10px',
              padding: '20px',
              border: `1px solid ${isLightTheme() ? '#86efac' : 'rgba(16, 185, 129, 0.2)'}`,
              marginBottom: '20px'
            }}>
              <h4 style={{ margin: '0 0 16px', fontSize: '15px', color: isLightTheme() ? '#166534' : '#4ade80', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>Hierarchy</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <span style={{ fontSize: '16px', color: getTheme().colors.textSecondary, minWidth: '60px' }}>Type:</span>
                <span style={{
                  background: editingFormPage.is_root 
                    ? (isLightTheme() ? '#dbeafe' : 'rgba(99, 102, 241, 0.2)')
                    : (isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.2)'),
                  color: editingFormPage.is_root 
                    ? (isLightTheme() ? '#1e40af' : '#a5b4fc')
                    : (isLightTheme() ? '#92400e' : '#fbbf24'),
                  padding: '8px 14px',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 600
                }}>
                  {editingFormPage.is_root ? 'Root Form' : 'Child Form'}
                </span>
              </div>
              {editingFormPage.parent_form_name && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '15px', color: getTheme().colors.textSecondary, minWidth: '60px' }}>Parent:</span>
                  <span style={{ fontSize: '16px', color: getTheme().colors.textPrimary, fontWeight: 500 }}>{editingFormPage.parent_form_name}</span>
                </div>
              )}
              {editingFormPage.children && editingFormPage.children.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <span style={{ fontSize: '15px', color: getTheme().colors.textSecondary }}>Children:</span>
                  <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {editingFormPage.children.map((c, i) => (
                      <span key={i} style={{
                        background: isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.15)',
                        color: isLightTheme() ? '#92400e' : '#fbbf24',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        fontSize: '14px',
                        fontWeight: 500
                      }}>{c.form_name}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* URL Info */}
            <div style={{
              background: isLightTheme() ? '#fef3c7' : 'rgba(245, 158, 11, 0.1)',
              borderRadius: '10px',
              padding: '20px',
              border: `1px solid ${isLightTheme() ? '#fcd34d' : 'rgba(245, 158, 11, 0.2)'}`
            }}>
              <h4 style={{ margin: '0 0 12px', fontSize: '15px', color: isLightTheme() ? '#92400e' : '#fbbf24', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>URL</h4>
              <div style={{ fontSize: '16px', color: getTheme().colors.textPrimary, wordBreak: 'break-all', lineHeight: 1.6 }}>
                {editingFormPage.url}
              </div>
            </div>

            {/* User Provided Inputs */}
            {token && (
              <UserProvidedInputsSection
                formPageId={editingFormPage.id}
                token={token}
                apiBase=""
                isLightTheme={isLightTheme()}
                themeColors={getTheme().colors}
              />
            )}
          </div>

          {/* Right Column - Steps */}
          <div style={{ flex: 1, padding: '28px', minWidth: 0, background: isLightTheme() ? '#dbeafe' : 'rgba(59, 130, 246, 0.08)' }}>
            {/* Path to Form Page Banner */}
            <div style={{
              display: 'inline-flex',
              gap: '12px',
              background: isLightTheme() ? '#bfdbfe' : 'rgba(59, 130, 246, 0.2)',
              border: isLightTheme() ? '1px solid #93c5fd' : '1px solid rgba(59, 130, 246, 0.3)',
              padding: '12px 20px',
              borderRadius: '10px',
              marginBottom: '24px',
              alignItems: 'center'
            }}>
              <span style={{ fontSize: '22px' }}>🛤️</span>
              <strong style={{ fontSize: '17px', color: isLightTheme() ? '#1e40af' : '#93c5fd' }}>Path to Form Page</strong>
            </div>

            {/* Path Steps Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '20px', color: isLightTheme() ? '#1e40af' : getTheme().colors.textPrimary, fontWeight: 600 }}>
                Steps ({editNavigationSteps.length})
              </h3>
              <button onClick={addStepAtEnd} style={{
                background: isLightTheme() ? '#3b82f6' : getTheme().colors.accentPrimary,
                color: '#fff',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                + Add Step
              </button>
            </div>

            {/* Steps List */}
            <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '8px' }}>
              {editNavigationSteps.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: '40px',
                  color: getTheme().colors.textSecondary,
                  background: isLightTheme() ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.03)',
                  borderRadius: '12px',
                  border: `2px dashed ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)'}`
                }}>
                  <p style={{ fontSize: '17px', margin: 0 }}>No navigation steps defined.</p>
                  <p style={{ fontSize: '15px', margin: '10px 0 0', opacity: 0.7 }}>Click "+ Add Step" to add navigation steps to this form page.</p>
                </div>
              ) : (
                editNavigationSteps.map((step, index) => (
                  <div key={index} className="step-card" style={{
                    background: isLightTheme() ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '12px',
                    marginBottom: '12px',
                    overflow: 'hidden',
                    transition: 'border-color 0.2s ease'
                  }}>
                    {/* Step Header */}
                    <div 
                      onClick={() => toggleNavStepExpanded(index)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        padding: '14px 18px',
                        cursor: 'pointer',
                        background: isLightTheme() ? 'rgba(59, 130, 246, 0.05)' : 'rgba(255,255,255,0.02)'
                      }}
                    >
                      <div style={{
                        width: '36px',
                        height: '36px',
                        background: isLightTheme() ? '#3b82f6' : getTheme().colors.accentPrimary,
                        color: '#fff',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '16px',
                        fontWeight: 700,
                        flexShrink: 0
                      }}>
                        {index + 1}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ 
                          fontSize: '16px', 
                          fontWeight: 500, 
                          color: getTheme().colors.textPrimary,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {step.name || step.description || `${step.action} • ${step.selector?.substring(0, 40)}...`}
                        </div>
                        <div style={{ 
                          fontSize: '14px', 
                          color: getTheme().colors.textSecondary,
                          marginTop: '4px'
                        }}>
                          {step.action}
                        </div>
                      </div>
                      <button className="expand-btn" style={{
                        background: 'transparent',
                        border: 'none',
                        padding: '8px',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        transition: 'background 0.2s ease'
                      }}>
                        <span style={{ 
                          fontSize: '18px',
                          color: getTheme().colors.textSecondary,
                          transform: expandedSteps.has(index) ? 'rotate(180deg)' : 'rotate(0deg)',
                          display: 'inline-block',
                          transition: 'transform 0.2s ease'
                        }}>▼</span>
                      </button>
                    </div>

                    {/* Step Details (Expanded) */}
                    {expandedSteps.has(index) && (
                      <div style={{ padding: '18px', borderTop: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'}` }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                          <div>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Action</label>
                            <select
                              value={step.action}
                              onChange={(e) => updateNavigationStep(index, 'action', e.target.value)}
                              style={{
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: '8px',
                                border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                                background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                color: getTheme().colors.textPrimary,
                                fontSize: '14px'
                              }}
                            >
                              <option value="click">Click</option>
                              <option value="fill">Fill</option>
                              <option value="type">Type</option>
                              <option value="select">Select</option>
                              <option value="hover">Hover</option>
                              <option value="wait">Wait</option>
                            </select>
                          </div>
                          <div>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Value</label>
                            <input
                              type="text"
                              value={step.value || ''}
                              onChange={(e) => updateNavigationStep(index, 'value', e.target.value)}
                              placeholder="Value (if needed)"
                              style={{
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: '8px',
                                border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                                background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                color: getTheme().colors.textPrimary,
                                fontSize: '14px',
                                boxSizing: 'border-box'
                              }}
                            />
                          </div>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Selector</label>
                          <input
                            type="text"
                            value={step.selector || ''}
                            onChange={(e) => updateNavigationStep(index, 'selector', e.target.value)}
                            placeholder="CSS selector or XPath"
                            style={{
                              width: '100%',
                              padding: '10px 12px',
                              borderRadius: '8px',
                              border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                              background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                              color: getTheme().colors.textPrimary,
                              fontSize: '14px',
                              fontFamily: 'monospace',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: getTheme().colors.textSecondary, fontWeight: 500 }}>Description</label>
                          <input
                            type="text"
                            value={step.description || ''}
                            onChange={(e) => updateNavigationStep(index, 'description', e.target.value)}
                            placeholder="Step description"
                            style={{
                              width: '100%',
                              padding: '10px 12px',
                              borderRadius: '8px',
                              border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                              background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                              color: getTheme().colors.textPrimary,
                              fontSize: '14px',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => addStepAfter(index)}
                            style={{
                              background: 'transparent',
                              border: `1px solid ${getTheme().colors.accentPrimary}`,
                              color: getTheme().colors.accentPrimary,
                              padding: '8px 14px',
                              borderRadius: '6px',
                              fontSize: '13px',
                              cursor: 'pointer'
                            }}
                          >
                            + Add After
                          </button>
                          <button
                            onClick={() => confirmDeleteStep(index)}
                            style={{
                              background: 'transparent',
                              border: '1px solid #ef4444',
                              color: '#ef4444',
                              padding: '8px 14px',
                              borderRadius: '6px',
                              fontSize: '13px',
                              cursor: 'pointer'
                            }}
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Completed Mapping Paths Section */}
        <div style={{
          borderTop: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
          padding: '28px 32px',
          background: isLightTheme() ? 'rgba(16, 185, 129, 0.03)' : 'rgba(16, 185, 129, 0.02)'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px',
            marginBottom: '20px'
          }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              background: isLightTheme() ? '#d1fae5' : 'rgba(16, 185, 129, 0.15)',
              border: `1px solid ${isLightTheme() ? '#6ee7b7' : 'rgba(16, 185, 129, 0.3)'}`,
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
            <div style={{ display: 'flex', gap: '8px' }}>
              {completedPaths.length > 0 && (
                <button
                  onClick={handleExportPom}
                  style={{
                    background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  📄 Export POM
                </button>
              )}
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
              <p style={{ fontSize: '14px', margin: '8px 0 0', opacity: 0.7 }}>Click "Map Form Page" to discover paths through this form.</p>
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
                        {/* Show junctions when collapsed */}
                        {expandedPathId !== path.id && path.path_junctions && path.path_junctions.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '12px' }}>
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
                        )}
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
                      <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        marginBottom: '12px' 
                      }}>
                        <div style={{ fontSize: '16px', fontWeight: 600, color: getTheme().colors.textSecondary }}>
                          Steps ({getPathSteps(path.id, path.steps || []).length}):
                          {hasUnsavedChanges(path.id) && (
                            <span style={{ color: '#f59e0b', marginLeft: '8px', fontSize: '15px' }}>● Unsaved changes</span>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          {!isPathEditable(path.id) ? (
                            /* Show "Edit Path Steps" button when not in edit mode */
                            <button
                              onClick={() => setShowEditPathWarning(path.id)}
                              style={{
                                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                                color: '#fff',
                                border: 'none',
                                padding: '8px 16px',
                                borderRadius: '8px',
                                fontSize: '13px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                boxShadow: '0 2px 8px rgba(245, 158, 11, 0.3)'
                              }}
                            >
                              ✏️ Edit Path Steps
                            </button>
                          ) : (
                            /* Show editing controls when in edit mode */
                            <>
                              <button
                                onClick={() => handleAddStepAfter(path.id, -1, path.steps || [], false)}
                                style={{
                                  background: isLightTheme() ? '#3b82f6' : 'rgba(59, 130, 246, 0.8)',
                                  color: '#fff',
                                  border: 'none',
                                  padding: '6px 12px',
                                  borderRadius: '6px',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                + Action Step
                              </button>
                              <button
                                onClick={() => handleAddStepAfter(path.id, -1, path.steps || [], true)}
                                style={{
                                  background: isLightTheme() ? '#059669' : 'rgba(16, 185, 129, 0.8)',
                                  color: '#fff',
                                  border: 'none',
                                  padding: '6px 12px',
                                  borderRadius: '6px',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                + Verify Step
                              </button>
                              {hasUnsavedChanges(path.id) && (
                                <button
                                  onClick={() => handleSaveAllPathSteps(path.id)}
                                  style={{
                                    background: 'linear-gradient(135deg, #059669, #047857)',
                                    color: '#fff',
                                    border: 'none',
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                    cursor: 'pointer'
                                  }}
                                >
                                  💾 Save All Steps
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                      
                      {/* Initialize local steps only when editing is enabled */}
                      {isPathEditable(path.id) && (() => { initializeLocalPathSteps(path.id, path.steps || []); return null; })()}
                      
                      <div>
                        {getPathSteps(path.id, path.steps || []).map((step, stepIndex) => {
                          const isVerify = isVerifyStep(step)
                          const stepKey = `${path.id}-${stepIndex}`
                          const isExpanded = expandedPathSteps.has(stepKey)
                          const editData = localEditedStepData[stepKey] || {}
                          const isDragOver = dragOverIndex === stepIndex && draggedStep?.pathId === path.id
                          
                          return (
                            <div 
                              key={stepIndex}
                              draggable={isPathEditable(path.id)}
                              onDragStart={() => isPathEditable(path.id) && handleDragStart(path.id, stepIndex)}
                              onDragOver={(e) => isPathEditable(path.id) && handleDragOver(e, stepIndex)}
                              onDrop={() => isPathEditable(path.id) && handleDrop(path.id, stepIndex, path.steps || [])}
                              onDragEnd={() => { setDraggedStep(null); setDragOverIndex(null); }}
                              onClick={() => isPathEditable(path.id) && toggleStepExpanded(path.id, stepIndex, step)}
                              style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '14px',
                                padding: '16px',
                                background: isVerify 
                                  ? (isLightTheme() ? 'rgba(16, 185, 129, 0.12)' : 'rgba(16, 185, 129, 0.15)')
                                  : (isLightTheme() ? 'rgba(59, 130, 246, 0.12)' : 'rgba(59, 130, 246, 0.15)'),
                                borderRadius: '8px',
                                marginBottom: '8px',
                                cursor: isPathEditable(path.id) ? 'pointer' : 'default',
                                border: isDragOver 
                                  ? '2px dashed #3b82f6'
                                  : isVerify 
                                    ? `2px solid ${isLightTheme() ? 'rgba(16, 185, 129, 0.4)' : 'rgba(16, 185, 129, 0.5)'}`
                                    : `2px solid ${isLightTheme() ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.4)'}`,
                                transition: 'all 0.2s ease',
                                opacity: draggedStep?.pathId === path.id && draggedStep?.index === stepIndex ? 0.5 : 1
                              }}
                            >
                              {/* Drag handle and step number */}
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                                {isPathEditable(path.id) && (
                                  <span style={{ fontSize: '12px', color: getTheme().colors.textSecondary, cursor: 'grab' }}>⋮⋮</span>
                                )}
                                <div style={{
                                  width: '32px',
                                  height: '32px',
                                  background: isVerify 
                                    ? (isLightTheme() ? '#059669' : '#10b981')
                                    : (isLightTheme() ? '#3b82f6' : '#60a5fa'),
                                  color: '#fff',
                                  borderRadius: '50%',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: '14px',
                                  fontWeight: 600,
                                  flexShrink: 0
                                }}>
                                  {stepIndex + 1}
                                </div>
                              </div>
                              
                              <div style={{ flex: 1, minWidth: 0 }}>
                                {/* Step header with action buttons */}
                                <div style={{ 
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'flex-start',
                                  marginBottom: '6px'
                                }}>
                                  <div 
                                    style={{ 
                                      fontSize: '16px', 
                                      fontWeight: 500, 
                                      color: getTheme().colors.textPrimary,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '8px'
                                    }}
                                  >
                                    <span style={{
                                      fontSize: '12px',
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      background: isVerify 
                                        ? (isLightTheme() ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.3)')
                                        : (isLightTheme() ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.3)'),
                                      color: isVerify
                                        ? (isLightTheme() ? '#059669' : '#34d399')
                                        : (isLightTheme() ? '#2563eb' : '#60a5fa'),
                                      fontWeight: 600
                                    }}>
                                      {step.action || 'unknown'}
                                    </span>
                                    {formatStepDescription(step)}
                                    <span 
                                      onClick={(e) => { e.stopPropagation(); toggleStepExpanded(path.id, stepIndex, step); }}
                                      style={{ 
                                        fontSize: '12px', 
                                        color: getTheme().colors.textSecondary,
                                        cursor: 'pointer',
                                        padding: '2px 6px'
                                      }}
                                    >
                                      {isExpanded ? '▼' : '▶'}
                                    </span>
                                  </div>
                                  
                                  {/* Action buttons - only show when path is editable */}
                                  {isPathEditable(path.id) && (
                                  <div style={{ display: 'flex', gap: '4px' }}>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleDuplicateStep(path.id, stepIndex, path.steps || []); }}
                                      title="Duplicate step"
                                      style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: getTheme().colors.textSecondary,
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '14px',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      📋
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleAddStepAfter(path.id, stepIndex, path.steps || [], false); }}
                                      title="Add action step after"
                                      style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: isLightTheme() ? '#3b82f6' : '#60a5fa',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '14px',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      ⚡
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleAddStepAfter(path.id, stepIndex, path.steps || [], true); }}
                                      title="Add verify step after"
                                      style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: isLightTheme() ? '#059669' : '#34d399',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '14px',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      ✓
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleDeletePathStep(path.id, stepIndex, path.steps || []); }}
                                      title="Delete step"
                                      style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: '#ef4444',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '14px',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      🗑️
                                    </button>
                                  </div>
                                  )}
                                </div>
                                
                                {/* Collapsed view - show selector and value inline */}
                                {!isExpanded && (
                                  <>
                                    {step.selector && (
                                      <div 
                                        style={{ 
                                          fontSize: '15px', 
                                          color: getTheme().colors.textSecondary,
                                          fontFamily: 'monospace',
                                          wordBreak: 'break-all',
                                          marginBottom: '6px'
                                        }}
                                        title={step.selector}
                                      >
                                        {isVerify && step.selector.length > 30 
                                          ? step.selector.substring(0, 30) + '...' 
                                          : step.selector}
                                      </div>
                                    )}
                                    {(step.value || step.input_value) && (
                                      <div style={{ 
                                        fontSize: '15px', 
                                        color: isLightTheme() ? '#059669' : '#34d399',
                                        fontWeight: 500
                                      }}>
                                        Value: {step.value || step.input_value}
                                      </div>
                                    )}
                                  </>
                                )}
                                
                                {/* Expanded view - editable fields */}
                                {isExpanded && (
                                  <div 
                                    onClick={(e) => e.stopPropagation()}
                                    style={{ 
                                      marginTop: '12px',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      gap: '12px',
                                      background: isLightTheme() ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.2)',
                                      padding: '16px',
                                      borderRadius: '8px'
                                    }}
                                  >
                                    {/* Step Type indicator (read-only) */}
                                    <div style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '8px',
                                      padding: '8px 12px',
                                      background: isVerify 
                                        ? (isLightTheme() ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.15)')
                                        : (isLightTheme() ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.15)'),
                                      borderRadius: '6px',
                                      width: 'fit-content'
                                    }}>
                                      <span style={{
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        color: isVerify 
                                          ? (isLightTheme() ? '#059669' : '#34d399')
                                          : (isLightTheme() ? '#2563eb' : '#60a5fa')
                                      }}>
                                        {isVerify ? '✓ Verify Step' : '⚡ Create/Action Step'}
                                      </span>
                                    </div>
                                    
                                    {/* Action field - dropdown for non-verify, read-only for verify */}
                                    <div>
                                      <label style={{ 
                                        fontSize: '13px', 
                                        fontWeight: 600, 
                                        color: getTheme().colors.textSecondary,
                                        display: 'block',
                                        marginBottom: '4px'
                                      }}>
                                        Action {isVerify && '(locked to verify)'}
                                      </label>
                                      {isVerify ? (
                                        <input
                                          type="text"
                                          value="verify"
                                          readOnly
                                          style={{
                                            width: '100%',
                                            padding: '10px 12px',
                                            fontSize: '15px',
                                            border: `1px solid ${isLightTheme() ? '#e5e7eb' : 'rgba(255,255,255,0.1)'}`,
                                            borderRadius: '6px',
                                            background: isLightTheme() ? '#f3f4f6' : 'rgba(255,255,255,0.02)',
                                            color: getTheme().colors.textSecondary,
                                            boxSizing: 'border-box',
                                            cursor: 'not-allowed'
                                          }}
                                        />
                                      ) : (
                                        <select
                                          value={editData.action || step.action || 'click'}
                                          onChange={(e) => updateLocalStepField(path.id, stepIndex, 'action', e.target.value)}
                                          style={{
                                            width: '100%',
                                            padding: '10px 12px',
                                            fontSize: '15px',
                                            border: `1px solid ${isLightTheme() ? '#d1d5db' : 'rgba(255,255,255,0.2)'}`,
                                            borderRadius: '6px',
                                            background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                            color: getTheme().colors.textPrimary,
                                            boxSizing: 'border-box',
                                            cursor: 'pointer'
                                          }}
                                        >
                                          {ACTION_TYPES.filter(a => a !== 'verify').map(action => (
                                            <option key={action} value={action}>{action}</option>
                                          ))}
                                        </select>
                                      )}
                                    </div>
                                    
                                    {/* Selector field */}
                                    <div>
                                      <label style={{ 
                                        fontSize: '13px', 
                                        fontWeight: 600, 
                                        color: getTheme().colors.textSecondary,
                                        display: 'block',
                                        marginBottom: '4px'
                                      }}>
                                        Selector
                                      </label>
                                      <input
                                        type="text"
                                        value={editData.selector !== undefined ? editData.selector : (step.selector || '')}
                                        onChange={(e) => updateLocalStepField(path.id, stepIndex, 'selector', e.target.value)}
                                        style={{
                                          width: '100%',
                                          padding: '10px 12px',
                                          fontSize: '15px',
                                          fontFamily: 'monospace',
                                          border: `1px solid ${isLightTheme() ? '#d1d5db' : 'rgba(255,255,255,0.2)'}`,
                                          borderRadius: '6px',
                                          background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                          color: getTheme().colors.textPrimary,
                                          boxSizing: 'border-box'
                                        }}
                                      />
                                    </div>
                                    
                                    {/* Value field */}
                                    <div>
                                      <label style={{ 
                                        fontSize: '13px', 
                                        fontWeight: 600, 
                                        color: getTheme().colors.textSecondary,
                                        display: 'block',
                                        marginBottom: '4px'
                                      }}>
                                        {isVerify ? 'Expected Value' : 'Value'}
                                      </label>
                                      <input
                                        type="text"
                                        value={editData.value !== undefined ? editData.value : (step.value || step.input_value || '')}
                                        onChange={(e) => updateLocalStepField(path.id, stepIndex, 'value', e.target.value)}
                                        style={{
                                          width: '100%',
                                          padding: '10px 12px',
                                          fontSize: '15px',
                                          border: `1px solid ${isLightTheme() ? '#d1d5db' : 'rgba(255,255,255,0.2)'}`,
                                          borderRadius: '6px',
                                          background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                          color: isLightTheme() ? '#059669' : '#34d399',
                                          boxSizing: 'border-box'
                                        }}
                                      />
                                    </div>
                                    
                                    {/* Description field */}
                                    <div>
                                      <label style={{ 
                                        fontSize: '13px', 
                                        fontWeight: 600, 
                                        color: getTheme().colors.textSecondary,
                                        display: 'block',
                                        marginBottom: '4px'
                                      }}>
                                        Description
                                      </label>
                                      <input
                                        type="text"
                                        value={editData.description !== undefined ? editData.description : (step.description || '')}
                                        onChange={(e) => updateLocalStepField(path.id, stepIndex, 'description', e.target.value)}
                                        style={{
                                          width: '100%',
                                          padding: '10px 12px',
                                          fontSize: '15px',
                                          border: `1px solid ${isLightTheme() ? '#d1d5db' : 'rgba(255,255,255,0.2)'}`,
                                          borderRadius: '6px',
                                          background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                                          color: getTheme().colors.textPrimary,
                                          boxSizing: 'border-box'
                                        }}
                                      />
                                    </div>
                                    
                                    {/* Save single step button */}
                                    <button
                                      onClick={() => handleSaveStep(path.id, stepIndex)}
                                      style={{
                                        background: 'linear-gradient(135deg, #059669, #047857)',
                                        color: '#fff',
                                        border: 'none',
                                        padding: '10px 20px',
                                        borderRadius: '6px',
                                        fontSize: '14px',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        alignSelf: 'flex-start'
                                      }}
                                    >
                                      💾 Save This Step
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Path Steps Warning Modal */}
      {showEditPathWarning !== null && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => setShowEditPathWarning(null)}>
          <div style={{
            background: isLightTheme() ? '#fff' : '#1f2937',
            borderRadius: '16px',
            padding: '32px',
            width: '90%',
            maxWidth: '580px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }} onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
              <div style={{
                width: '56px',
                height: '56px',
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                borderRadius: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '28px'
              }}>
                ⚠️
              </div>
              <h3 style={{ margin: 0, color: getTheme().colors.textPrimary, fontSize: '24px', fontWeight: 600 }}>
                Edit Path Steps
              </h3>
            </div>
            
            {/* Warning Content */}
            <div style={{
              background: isLightTheme() ? 'rgba(245, 158, 11, 0.1)' : 'rgba(245, 158, 11, 0.15)',
              border: `1px solid ${isLightTheme() ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.4)'}`,
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '24px'
            }}>
              <p style={{ margin: '0 0 14px', color: getTheme().colors.textPrimary, fontWeight: 600, fontSize: '17px' }}>
                🤖 These path steps were automatically discovered and generated by AI.
              </p>
              <p style={{ margin: 0, color: getTheme().colors.textSecondary, fontSize: '16px', lineHeight: 1.6 }}>
                They represent a complete, validated sequence of actions to fill out this form path. 
                The steps are designed to work together in order.
              </p>
            </div>
            
            <p style={{ margin: '0 0 14px', color: getTheme().colors.textSecondary, fontSize: '16px', lineHeight: 1.6 }}>
              <strong style={{ color: getTheme().colors.textPrimary }}>Before editing, please understand:</strong>
            </p>
            
            <ul style={{ 
              margin: '0 0 24px', 
              paddingLeft: '24px',
              color: getTheme().colors.textSecondary,
              fontSize: '16px',
              lineHeight: 2
            }}>
              <li><strong>Step order matters</strong> – Some steps depend on previous steps</li>
              <li><strong>Selectors are precise</strong> – Changing them may break the test</li>
              <li><strong>Values may be contextual</strong> – AI chose values based on form rules</li>
              <li><strong>Junction paths are interconnected</strong> – Changes may affect form flow</li>
            </ul>
            
            <p style={{ 
              margin: '0 0 28px', 
              padding: '16px',
              background: isLightTheme() ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.15)',
              borderRadius: '10px',
              color: isLightTheme() ? '#1d4ed8' : '#93c5fd',
              fontSize: '15px',
              lineHeight: 1.5
            }}>
              💡 <strong>Tip:</strong> If test runs fail after editing, you can re-map the form to regenerate correct steps.
            </p>
            
            {/* Buttons */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowEditPathWarning(null)}
                style={{
                  background: isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)',
                  border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.15)'}`,
                  color: getTheme().colors.textPrimary,
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => enablePathEditing(showEditPathWarning)}
                style={{
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)'
                }}
              >
                ✏️ I Understand, Enable Editing
              </button>
            </div>
          </div>
        </div>
      )}

      {/* POM Export Modal */}
      {showPomModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => setShowPomModal(false)}>
          <div style={{
            background: isLightTheme() ? '#fff' : '#1f2937',
            borderRadius: '16px',
            padding: '24px',
            width: '90%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto'
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, color: getTheme().colors.textPrimary, fontSize: '20px' }}>
                📄 Export Page Object Model (POM)
              </h3>
              <button
                onClick={() => setShowPomModal(false)}
                style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: getTheme().colors.textSecondary }}
              >
                ×
              </button>
            </div>
            
            {pomStatus === 'idle' && (
              <>
                <p style={{ color: getTheme().colors.textSecondary, marginBottom: '20px' }}>
                  Generate Page Object Model code for "{editingFormPage.form_name}" with {completedPaths.length} path(s).
                </p>
                
                <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: getTheme().colors.textSecondary, fontWeight: 600 }}>
                      Language
                    </label>
                    <select
                      value={pomLanguage}
                      onChange={(e) => setPomLanguage(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${getTheme().colors.cardBorder}`,
                        background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                        color: getTheme().colors.textPrimary,
                        fontSize: '15px'
                      }}
                    >
                      <option value="python">Python</option>
                      <option value="javascript">JavaScript</option>
                      <option value="typescript">TypeScript</option>
                      <option value="java">Java</option>
                      <option value="csharp">C#</option>
                    </select>
                  </div>
                  
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: getTheme().colors.textSecondary, fontWeight: 600 }}>
                      Framework
                    </label>
                    <select
                      value={pomFramework}
                      onChange={(e) => setPomFramework(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${getTheme().colors.cardBorder}`,
                        background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                        color: getTheme().colors.textPrimary,
                        fontSize: '15px'
                      }}
                    >
                      <option value="selenium">Selenium</option>
                      <option value="playwright">Playwright</option>
                      <option value="cypress">Cypress</option>
                    </select>
                  </div>
                </div>
                
                {/* Style dropdown - only show for Java */}
                {pomLanguage === 'java' && (
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: getTheme().colors.textSecondary, fontWeight: 600 }}>
                      Style
                    </label>
                    <select
                      value={pomStyle}
                      onChange={(e) => setPomStyle(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${getTheme().colors.cardBorder}`,
                        background: isLightTheme() ? '#fff' : 'rgba(255,255,255,0.05)',
                        color: getTheme().colors.textPrimary,
                        fontSize: '15px'
                      }}
                    >
                      <option value="basic">Basic POM</option>
                      <option value="pagefactory">Page Factory (@FindBy)</option>
                    </select>
                  </div>
                )}
                
                <button
                  onClick={startPomGeneration}
                  style={{
                    background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                    color: '#fff',
                    border: 'none',
                    padding: '12px 24px',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    width: '100%'
                  }}
                >
                  🚀 Generate POM Code
                </button>
              </>
            )}
            
            {(pomStatus === 'starting' || pomStatus === 'processing') && (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚙️</div>
                <p style={{ color: getTheme().colors.textPrimary, fontSize: '18px', fontWeight: 600 }}>
                  Generating POM code...
                </p>
                <p style={{ color: getTheme().colors.textSecondary }}>
                  AI is creating your {pomLanguage} + {pomFramework} Page Object Model
                </p>
              </div>
            )}
            
            {pomStatus === 'failed' && (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
                <p style={{ color: '#ef4444', fontSize: '18px', fontWeight: 600 }}>
                  Generation Failed
                </p>
                <p style={{ color: getTheme().colors.textSecondary, marginBottom: '20px' }}>
                  {pomError}
                </p>
                <button
                  onClick={() => setPomStatus('idle')}
                  style={{
                    background: getTheme().colors.cardBorder,
                    color: getTheme().colors.textPrimary,
                    border: 'none',
                    padding: '10px 20px',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  Try Again
                </button>
              </div>
            )}
            
            {pomStatus === 'completed' && (
              <>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                  <button
                    onClick={copyPomToClipboard}
                    style={{
                      background: isLightTheme() ? '#e5e7eb' : 'rgba(255,255,255,0.1)',
                      color: getTheme().colors.textPrimary,
                      border: 'none',
                      padding: '10px 20px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    📋 Copy to Clipboard
                  </button>
                  <button
                    onClick={downloadPomFile}
                    style={{
                      background: 'linear-gradient(135deg, #059669, #047857)',
                      color: '#fff',
                      border: 'none',
                      padding: '10px 20px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    💾 Download File
                  </button>
                  <button
                    onClick={() => setPomStatus('idle')}
                    style={{
                      background: 'transparent',
                      color: getTheme().colors.textSecondary,
                      border: `1px solid ${getTheme().colors.cardBorder}`,
                      padding: '10px 20px',
                      borderRadius: '8px',
                      cursor: 'pointer'
                    }}
                  >
                    Regenerate
                  </button>
                </div>
                
                <pre style={{
                  background: isLightTheme() ? '#1e1e1e' : '#0d1117',
                  color: '#e6e6e6',
                  padding: '16px',
                  borderRadius: '8px',
                  overflow: 'auto',
                  maxHeight: '400px',
                  fontSize: '13px',
                  fontFamily: 'Monaco, Consolas, monospace',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {pomCode}
                </pre>
              </>
            )}
          </div>
        </div>
      )}

      {/* Delete Step Confirmation Modal */}
      {showDeleteStepConfirm && (
        <div style={modalOverlayStyle} onClick={() => setShowDeleteStepConfirm(false)}>
          <div style={{
            ...smallModalContentStyle,
            background: isLightTheme() 
              ? 'linear-gradient(135deg, #ffffff, #f8fafc)'
              : 'linear-gradient(135deg, rgba(75, 85, 99, 0.98), rgba(55, 65, 81, 0.98))'
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 16px', color: getTheme().colors.textPrimary, fontSize: '20px' }}>
              Delete Step?
            </h3>
            <p style={{ color: getTheme().colors.textSecondary, marginBottom: '24px' }}>
              Are you sure you want to delete step {stepToDeleteIndex !== null ? stepToDeleteIndex + 1 : ''}? This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeleteStepConfirm(false)}
                style={{
                  background: 'transparent',
                  border: `1px solid ${getTheme().colors.cardBorder}`,
                  color: getTheme().colors.textSecondary,
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={deleteStep}
                style={{
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rediscover Form Page Confirmation Modal */}
      {showRediscoverModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => !deletingFormPage && setShowRediscoverModal(false)}>
          <div style={{
            background: isLightTheme() ? '#fff' : '#1f2937',
            borderRadius: '16px',
            padding: '24px',
            width: '90%',
            maxWidth: '500px'
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <span style={{ fontSize: '32px' }}>⚠️</span>
              <h3 style={{ margin: 0, color: getTheme().colors.textPrimary, fontSize: '20px' }}>
                Rediscover Form Page?
              </h3>
            </div>
            
            <p style={{ color: getTheme().colors.textSecondary, marginBottom: '12px', lineHeight: 1.6 }}>
              This will <strong style={{ color: '#ef4444' }}>permanently delete</strong> all data for this form page:
            </p>
            
            <ul style={{ 
              color: getTheme().colors.textSecondary, 
              marginBottom: '20px',
              paddingLeft: '20px',
              lineHeight: 1.8
            }}>
              <li>Navigation steps (path to form page)</li>
              <li>All {completedPaths.length} mapped path(s)</li>
              <li>All form field mappings</li>
              <li>User-provided input values</li>
            </ul>
            
            <p style={{ color: getTheme().colors.textSecondary, marginBottom: '24px' }}>
              You will be redirected to the main page to start a fresh discovery.
            </p>
            
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowRediscoverModal(false)}
                disabled={deletingFormPage}
                style={{
                  background: 'transparent',
                  border: `1px solid ${getTheme().colors.cardBorder}`,
                  color: getTheme().colors.textSecondary,
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  cursor: deletingFormPage ? 'not-allowed' : 'pointer',
                  opacity: deletingFormPage ? 0.5 : 1
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmRediscoverFormPage}
                disabled={deletingFormPage}
                style={{
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                  border: 'none',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: deletingFormPage ? 'not-allowed' : 'pointer',
                  opacity: deletingFormPage ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {deletingFormPage ? (
                  <>⏳ Deleting...</>
                ) : (
                  <>🗑️ Delete & Rediscover</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
