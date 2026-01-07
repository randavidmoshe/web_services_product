'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import UserProvidedInputsSection from './UserProvidedInputsSection'
import FormPageEditPanel from './FormPageEditPanel'

interface Network {
  id: number
  name: string
  url: string
  network_type: string
  login_username: string | null
}

interface NavigationStep {
  action: string
  selector?: string
  value?: string
  name?: string
  description?: string
}

interface FormPage {
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

interface JunctionChoice {
  junction_id?: string
  junction_name: string
  option: string
  selector?: string
}

interface CompletedPath {
  id: number
  path_number: number
  path_junctions: JunctionChoice[]
  steps: any[]
  steps_count: number
  is_verified: boolean
  created_at: string
  updated_at: string
}

interface SessionStatus {
  session: {
    id: number
    status: string
    pages_crawled: number
    forms_found: number
    error_message: string | null
    error_code: string | null
    started_at: string | null
    completed_at: string | null
  }
  forms: FormPage[]
}

// Error code to friendly message mapping
const ERROR_MESSAGES: Record<string, string> = {
  'PAGE_NOT_FOUND': '🔗 Page not found (404) - check the URL',
  'ACCESS_DENIED': '🔒 Access denied (403) - check permissions',
  'SERVER_ERROR': '⚠️ Server error (500) - site may be experiencing issues',
  'SSL_ERROR': '🔐 SSL certificate error - site security issue',
  'SITE_UNAVAILABLE': '🌐 Site unavailable - server may be down',
  'LOGIN_FAILED': '🔑 Login failed - check credentials or login page changed',
  'SESSION_EXPIRED': '⏰ Session expired during discovery',
  'TIMEOUT': '⏱️ Page load timeout - site may be slow',
  'ELEMENT_NOT_FOUND': '🔍 Required element not found on page',
  'AGENT_DISCONNECTED': '🔌 Agent disconnected - no heartbeat received',
  'USER_CANCELLED': '⏹ Cancelled by user',
  'UNKNOWN': '❓ Unknown error occurred'
}

const getErrorMessage = (errorCode: string | null | undefined, errorMessage: string | null | undefined): string => {
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }
  return errorMessage || 'Discovery failed'
}

interface DiscoveryQueueItem {
  networkId: number
  networkName: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  sessionId?: number
  pagesSearched: number
  formsFound: number
  errorMessage?: string
  errorCode?: string
}

interface LoginLogoutData {
  login_stages: NavigationStep[]
  logout_stages: NavigationStep[]
  network_name: string
  url: string
  updated_at: string | null
}

export default function DashboardPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeProjectName, setActiveProjectName] = useState<string | null>(null)
  
  const [networks, setNetworks] = useState<Network[]>([])
  const [selectedNetworkIds, setSelectedNetworkIds] = useState<number[]>([])
  const [loadingNetworks, setLoadingNetworks] = useState(false)
  
  const [formPages, setFormPages] = useState<FormPage[]>([])
  const [loadingFormPages, setLoadingFormPages] = useState(false)
  const [sortField, setSortField] = useState<'name' | 'date'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  
  const [headless, setHeadless] = useState(false)
  
  // Sequential discovery state
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [discoveryQueue, setDiscoveryQueue] = useState<DiscoveryQueueItem[]>([])
  const [currentNetworkIndex, setCurrentNetworkIndex] = useState<number>(-1)
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const shouldContinueRef = useRef<boolean>(false)
  
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Panel view instead of modal
  const [showEditPanel, setShowEditPanel] = useState(false)
  const [editingFormPage, setEditingFormPage] = useState<FormPage | null>(null)
  const [editFormName, setEditFormName] = useState('')
  const [editNavigationSteps, setEditNavigationSteps] = useState<NavigationStep[]>([])
  const [savingFormPage, setSavingFormPage] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  
  const [showDeleteStepConfirm, setShowDeleteStepConfirm] = useState(false)
  const [stepToDeleteIndex, setStepToDeleteIndex] = useState<number | null>(null)
  
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [formPageToDelete, setFormPageToDelete] = useState<FormPage | null>(null)
  const [deletingFormPage, setDeletingFormPage] = useState(false)
  
  // Form Mapping state
  const [mappingFormIds, setMappingFormIds] = useState<Set<number>>(new Set())
  const [mappingStatus, setMappingStatus] = useState<Record<number, { status: string; sessionId?: number; error?: string }>>({})
  const mappingPollingRef = useRef<Record<number, NodeJS.Timeout>>({})
  
  // Completed Paths state
  const [completedPaths, setCompletedPaths] = useState<CompletedPath[]>([])
  const [loadingPaths, setLoadingPaths] = useState(false)
  const [expandedPathId, setExpandedPathId] = useState<number | null>(null)
  const [editingPathStep, setEditingPathStep] = useState<{ pathId: number; stepIndex: number } | null>(null)
  const [editedPathStepData, setEditedPathStepData] = useState<any>({})
  
  // Discovery section collapse state (collapsed by default when forms exist)
  const [isDiscoveryExpanded, setIsDiscoveryExpanded] = useState(false)
  
  // Rediscover form page state
  const [rediscoverMessage, setRediscoverMessage] = useState<string | null>(null)
  
  // Test Template Selection state
  const [testTemplates, setTestTemplates] = useState<{id: number, name: string, display_name: string, test_cases: any[]}[]>([])
  const [showMapModal, setShowMapModal] = useState(false)
  const [selectedFormForMapping, setSelectedFormForMapping] = useState<FormPage | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  
  // Theme state - reads from localStorage to sync with layout
  const [currentTheme, setCurrentTheme] = useState<string>('platinum-steel')

  // Login/Logout stages state
  const [loginLogoutData, setLoginLogoutData] = useState<Record<number, LoginLogoutData>>({})
  const [editingLoginLogout, setEditingLoginLogout] = useState<{
    networkId: number
    type: 'login' | 'logout'
    steps: NavigationStep[]
    networkName: string
    url: string
  } | null>(null)

  // Theme definitions (same as layout.tsx)
  const themes: Record<string, {
    name: string
    colors: {
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
  }> = {
    'platinum-steel': {
      name: 'Platinum Steel',
      colors: {
        bgGradient: 'linear-gradient(180deg, #374151 0%, #1f2937 50%, #111827 100%)',
        headerBg: 'rgba(75, 85, 99, 0.9)',
        sidebarBg: 'rgba(75, 85, 99, 0.6)',
        cardBg: 'rgba(75, 85, 99, 0.5)',
        cardBorder: 'rgba(156, 163, 175, 0.35)',
        cardGlow: 'none',
        accentPrimary: '#6366f1',
        accentSecondary: '#8b5cf6',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#f3f4f6',
        textSecondary: '#9ca3af',
        textGlow: 'none',
        statusOnline: '#22c55e',
        statusGlow: '0 0 6px rgba(34, 197, 94, 0.4)',
        borderGlow: 'none'
      }
    },
    'ocean-depths': {
      name: 'Ocean Depths',
      colors: {
        bgGradient: 'linear-gradient(180deg, #0f4c5c 0%, #0a3541 50%, #051e26 100%)',
        headerBg: 'rgba(15, 76, 92, 0.9)',
        sidebarBg: 'rgba(15, 76, 92, 0.6)',
        cardBg: 'rgba(15, 76, 92, 0.5)',
        cardBorder: 'rgba(34, 211, 238, 0.35)',
        cardGlow: 'none',
        accentPrimary: '#06b6d4',
        accentSecondary: '#22d3ee',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#ecfeff',
        textSecondary: '#67e8f9',
        textGlow: 'none',
        statusOnline: '#22d3ee',
        statusGlow: '0 0 6px rgba(34, 211, 238, 0.4)',
        borderGlow: 'none'
      }
    },
    'aurora-borealis': {
      name: 'Aurora Borealis',
      colors: {
        bgGradient: 'linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #0f0a2e 100%)',
        headerBg: 'rgba(49, 46, 129, 0.9)',
        sidebarBg: 'rgba(49, 46, 129, 0.6)',
        cardBg: 'rgba(49, 46, 129, 0.5)',
        cardBorder: 'rgba(167, 139, 250, 0.35)',
        cardGlow: 'none',
        accentPrimary: '#8b5cf6',
        accentSecondary: '#a78bfa',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#f5f3ff',
        textSecondary: '#c4b5fd',
        textGlow: 'none',
        statusOnline: '#34d399',
        statusGlow: '0 0 6px rgba(52, 211, 153, 0.4)',
        borderGlow: 'none'
      }
    },
    'sunset-ember': {
      name: 'Sunset Ember',
      colors: {
        bgGradient: 'linear-gradient(180deg, #7c2d12 0%, #431407 50%, #1c0a04 100%)',
        headerBg: 'rgba(124, 45, 18, 0.9)',
        sidebarBg: 'rgba(124, 45, 18, 0.6)',
        cardBg: 'rgba(124, 45, 18, 0.5)',
        cardBorder: 'rgba(251, 146, 60, 0.4)',
        cardGlow: 'none',
        accentPrimary: '#f97316',
        accentSecondary: '#fb923c',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#fff7ed',
        textSecondary: '#fdba74',
        textGlow: 'none',
        statusOnline: '#fbbf24',
        statusGlow: '0 0 6px rgba(251, 191, 36, 0.4)',
        borderGlow: 'none'
      }
    },
    'emerald-forest': {
      name: 'Emerald Forest',
      colors: {
        bgGradient: 'linear-gradient(180deg, #064e3b 0%, #022c22 50%, #011513 100%)',
        headerBg: 'rgba(6, 78, 59, 0.9)',
        sidebarBg: 'rgba(6, 78, 59, 0.6)',
        cardBg: 'rgba(6, 78, 59, 0.5)',
        cardBorder: 'rgba(52, 211, 153, 0.35)',
        cardGlow: 'none',
        accentPrimary: '#10b981',
        accentSecondary: '#34d399',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#ecfdf5',
        textSecondary: '#6ee7b7',
        textGlow: 'none',
        statusOnline: '#34d399',
        statusGlow: '0 0 6px rgba(52, 211, 153, 0.4)',
        borderGlow: 'none'
      }
    },
    'crimson-night': {
      name: 'Crimson Night',
      colors: {
        bgGradient: 'linear-gradient(180deg, #450a0a 0%, #2d0606 50%, #1a0303 100%)',
        headerBg: 'rgba(69, 10, 10, 0.9)',
        sidebarBg: 'rgba(69, 10, 10, 0.6)',
        cardBg: 'rgba(69, 10, 10, 0.5)',
        cardBorder: 'rgba(251, 113, 133, 0.35)',
        cardGlow: 'none',
        accentPrimary: '#f43f5e',
        accentSecondary: '#fb7185',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#fff1f2',
        textSecondary: '#fda4af',
        textGlow: 'none',
        statusOnline: '#fb7185',
        statusGlow: '0 0 6px rgba(251, 113, 133, 0.4)',
        borderGlow: 'none'
      }
    },
    'bright-silver': {
      name: 'Bright Silver',
      colors: {
        bgGradient: 'linear-gradient(180deg, #6b7280 0%, #4b5563 50%, #374151 100%)',
        headerBg: 'rgba(107, 114, 128, 0.95)',
        sidebarBg: 'rgba(107, 114, 128, 0.7)',
        cardBg: 'rgba(107, 114, 128, 0.6)',
        cardBorder: 'rgba(209, 213, 219, 0.5)',
        cardGlow: 'none',
        accentPrimary: '#1e3a5f',
        accentSecondary: '#2d5a87',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#ffffff',
        textSecondary: '#e5e7eb',
        textGlow: 'none',
        statusOnline: '#22c55e',
        statusGlow: '0 0 8px rgba(34, 197, 94, 0.5)',
        borderGlow: 'none'
      }
    },
    'chrome-glow': {
      name: 'Chrome Glow',
      colors: {
        bgGradient: 'linear-gradient(180deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%)',
        headerBg: 'rgba(156, 163, 175, 0.95)',
        sidebarBg: 'rgba(156, 163, 175, 0.7)',
        cardBg: 'rgba(156, 163, 175, 0.6)',
        cardBorder: 'rgba(229, 231, 235, 0.6)',
        cardGlow: 'none',
        accentPrimary: '#0f4c5c',
        accentSecondary: '#1a6b7c',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#111827',
        textSecondary: '#374151',
        textGlow: 'none',
        statusOnline: '#22c55e',
        statusGlow: '0 0 8px rgba(34, 197, 94, 0.5)',
        borderGlow: 'none'
      }
    },
    'pearl-white': {
      name: 'Pearl White',
      colors: {
        bgGradient: 'linear-gradient(180deg, #dbe5f0 0%, #c8d8e8 50%, #b4c8dc 100%)',
        headerBg: 'rgba(248, 250, 252, 0.98)',
        sidebarBg: 'rgba(241, 245, 249, 0.95)',
        cardBg: 'rgba(242, 246, 250, 0.98)',
        cardBorder: 'rgba(100, 116, 139, 0.3)',
        cardGlow: 'none',
        accentPrimary: '#0369a1',
        accentSecondary: '#0ea5e9',
        accentGlow: 'none',
        iconGlow: 'none',
        buttonGlow: 'none',
        textPrimary: '#1e293b',
        textSecondary: '#475569',
        textGlow: 'none',
        statusOnline: '#16a34a',
        statusGlow: '0 0 8px rgba(22, 163, 74, 0.5)',
        borderGlow: 'none'
      }
    },
    'cyber-pink': {
      name: 'Cyber Pink',
      colors: {
        bgGradient: 'linear-gradient(180deg, #1a0a1a 0%, #0d0515 50%, #050208 100%)',
        headerBg: 'rgba(40, 15, 40, 0.95)',
        sidebarBg: 'rgba(40, 15, 40, 0.8)',
        cardBg: 'rgba(50, 20, 50, 0.6)',
        cardBorder: 'rgba(255, 0, 128, 0.6)',
        cardGlow: '0 0 18px rgba(255, 0, 128, 0.08)',
        accentPrimary: '#ff0080',
        accentSecondary: '#ff00ff',
        accentGlow: 'rgba(255, 0, 128, 0.18)',
        iconGlow: '0 0 4px rgba(255, 0, 128, 0.09)',
        buttonGlow: '0 0 15px rgba(255, 0, 128, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#ff99cc',
        textGlow: '0 0 9px rgba(255, 0, 128, 0.24)',
        statusOnline: '#00ffff',
        statusGlow: '0 0 9px rgba(0, 255, 255, 0.27)',
        borderGlow: '0 0 15px rgba(255, 0, 128, 0.12)'
      }
    },
    'radioactive': {
      name: 'Radioactive',
      colors: {
        bgGradient: 'linear-gradient(180deg, #0a1a05 0%, #050d02 50%, #020500 100%)',
        headerBg: 'rgba(20, 40, 10, 0.95)',
        sidebarBg: 'rgba(20, 40, 10, 0.8)',
        cardBg: 'rgba(25, 50, 15, 0.6)',
        cardBorder: 'rgba(136, 255, 0, 0.6)',
        cardGlow: '0 0 18px rgba(0, 255, 0, 0.06)',
        accentPrimary: '#00ff00',
        accentSecondary: '#88ff00',
        accentGlow: 'rgba(0, 255, 0, 0.18)',
        iconGlow: '0 0 4px rgba(0, 255, 0, 0.09)',
        buttonGlow: '0 0 15px rgba(0, 255, 0, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#bbff66',
        textGlow: '0 0 9px rgba(136, 255, 0, 0.24)',
        statusOnline: '#ffff00',
        statusGlow: '0 0 9px rgba(255, 255, 0, 0.27)',
        borderGlow: '0 0 15px rgba(0, 255, 0, 0.12)'
      }
    },
    'electric-blue': {
      name: 'Electric Blue',
      colors: {
        bgGradient: 'linear-gradient(180deg, #000a1a 0%, #00051a 50%, #000208 100%)',
        headerBg: 'rgba(0, 20, 50, 0.95)',
        sidebarBg: 'rgba(0, 20, 50, 0.8)',
        cardBg: 'rgba(0, 30, 60, 0.6)',
        cardBorder: 'rgba(0, 204, 255, 0.6)',
        cardGlow: '0 0 18px rgba(0, 102, 255, 0.08)',
        accentPrimary: '#0066ff',
        accentSecondary: '#00ccff',
        accentGlow: 'rgba(0, 102, 255, 0.18)',
        iconGlow: '0 0 4px rgba(0, 102, 255, 0.09)',
        buttonGlow: '0 0 15px rgba(0, 102, 255, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#66ddff',
        textGlow: '0 0 9px rgba(0, 204, 255, 0.24)',
        statusOnline: '#00ffff',
        statusGlow: '0 0 9px rgba(0, 255, 255, 0.27)',
        borderGlow: '0 0 15px rgba(0, 102, 255, 0.12)'
      }
    },
    'golden-sunrise': {
      name: 'Golden Sunrise',
      colors: {
        bgGradient: 'linear-gradient(180deg, #1a1005 0%, #0d0802 50%, #050200 100%)',
        headerBg: 'rgba(40, 30, 10, 0.95)',
        sidebarBg: 'rgba(40, 30, 10, 0.8)',
        cardBg: 'rgba(50, 35, 15, 0.6)',
        cardBorder: 'rgba(255, 204, 0, 0.6)',
        cardGlow: '0 0 18px rgba(255, 136, 0, 0.08)',
        accentPrimary: '#ff8800',
        accentSecondary: '#ffcc00',
        accentGlow: 'rgba(255, 136, 0, 0.18)',
        iconGlow: '0 0 4px rgba(255, 136, 0, 0.09)',
        buttonGlow: '0 0 15px rgba(255, 136, 0, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#ffdd44',
        textGlow: '0 0 9px rgba(255, 204, 0, 0.24)',
        statusOnline: '#ffff66',
        statusGlow: '0 0 9px rgba(255, 255, 102, 0.27)',
        borderGlow: '0 0 15px rgba(255, 136, 0, 0.12)'
      }
    },
    'plasma-purple': {
      name: 'Plasma Purple',
      colors: {
        bgGradient: 'linear-gradient(180deg, #0f051a 0%, #08020d 50%, #030105 100%)',
        headerBg: 'rgba(30, 10, 50, 0.95)',
        sidebarBg: 'rgba(30, 10, 50, 0.8)',
        cardBg: 'rgba(40, 15, 60, 0.6)',
        cardBorder: 'rgba(204, 102, 255, 0.6)',
        cardGlow: '0 0 18px rgba(153, 0, 255, 0.08)',
        accentPrimary: '#9900ff',
        accentSecondary: '#cc66ff',
        accentGlow: 'rgba(153, 0, 255, 0.18)',
        iconGlow: '0 0 4px rgba(153, 0, 255, 0.09)',
        buttonGlow: '0 0 15px rgba(153, 0, 255, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#dd99ff',
        textGlow: '0 0 9px rgba(204, 102, 255, 0.24)',
        statusOnline: '#ff99ff',
        statusGlow: '0 0 9px rgba(255, 153, 255, 0.27)',
        borderGlow: '0 0 15px rgba(153, 0, 255, 0.12)'
      }
    },
    'fire-storm': {
      name: 'Fire Storm',
      colors: {
        bgGradient: 'linear-gradient(180deg, #1a0505 0%, #0d0202 50%, #050000 100%)',
        headerBg: 'rgba(40, 10, 10, 0.95)',
        sidebarBg: 'rgba(40, 10, 10, 0.8)',
        cardBg: 'rgba(50, 15, 15, 0.6)',
        cardBorder: 'rgba(255, 102, 0, 0.6)',
        cardGlow: '0 0 18px rgba(255, 0, 0, 0.08)',
        accentPrimary: '#ff0000',
        accentSecondary: '#ff6600',
        accentGlow: 'rgba(255, 0, 0, 0.18)',
        iconGlow: '0 0 4px rgba(255, 0, 0, 0.09)',
        buttonGlow: '0 0 15px rgba(255, 0, 0, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#ff9944',
        textGlow: '0 0 9px rgba(255, 102, 0, 0.24)',
        statusOnline: '#ffcc00',
        statusGlow: '0 0 9px rgba(255, 204, 0, 0.27)',
        borderGlow: '0 0 15px rgba(255, 0, 0, 0.12)'
      }
    },
    'arctic-aurora': {
      name: 'Arctic Aurora',
      colors: {
        bgGradient: 'linear-gradient(180deg, #001a1a 0%, #000d0d 50%, #000505 100%)',
        headerBg: 'rgba(0, 40, 40, 0.95)',
        sidebarBg: 'rgba(0, 40, 40, 0.8)',
        cardBg: 'rgba(0, 50, 50, 0.6)',
        cardBorder: 'rgba(0, 255, 255, 0.6)',
        cardGlow: '0 0 18px rgba(0, 255, 204, 0.08)',
        accentPrimary: '#00ffcc',
        accentSecondary: '#00ffff',
        accentGlow: 'rgba(0, 255, 204, 0.18)',
        iconGlow: '0 0 4px rgba(0, 255, 204, 0.09)',
        buttonGlow: '0 0 15px rgba(0, 255, 204, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#66ffff',
        textGlow: '0 0 9px rgba(0, 255, 255, 0.24)',
        statusOnline: '#66ffff',
        statusGlow: '0 0 9px rgba(102, 255, 255, 0.27)',
        borderGlow: '0 0 15px rgba(0, 255, 204, 0.12)'
      }
    },
    'midnight-rose': {
      name: 'Midnight Rose',
      colors: {
        bgGradient: 'linear-gradient(180deg, #1a0510 0%, #0d0208 50%, #050103 100%)',
        headerBg: 'rgba(40, 10, 25, 0.95)',
        sidebarBg: 'rgba(40, 10, 25, 0.8)',
        cardBg: 'rgba(50, 15, 35, 0.6)',
        cardBorder: 'rgba(255, 102, 153, 0.6)',
        cardGlow: '0 0 18px rgba(255, 51, 119, 0.08)',
        accentPrimary: '#ff3377',
        accentSecondary: '#ff66aa',
        accentGlow: 'rgba(255, 51, 119, 0.18)',
        iconGlow: '0 0 4px rgba(255, 51, 119, 0.09)',
        buttonGlow: '0 0 15px rgba(255, 51, 119, 0.21)',
        textPrimary: '#ffffff',
        textSecondary: '#ffaacc',
        textGlow: '0 0 9px rgba(255, 102, 153, 0.24)',
        statusOnline: '#ff99cc',
        statusGlow: '0 0 9px rgba(255, 153, 204, 0.27)',
        borderGlow: '0 0 15px rgba(255, 51, 119, 0.12)'
      }
    }
  }

  // Get current theme colors
  const getTheme = () => themes[currentTheme] || themes['platinum-steel']

  // Detect if current theme is light (for contrast adjustments)
  const isLightTheme = () => {
    const lightThemes = ['pearl-white']
    return lightThemes.includes(currentTheme)
  }

  // Get contrasting background for elements (darker on light themes)
  const getContrastBg = (opacity: number = 0.1) => {
    return isLightTheme() 
      ? `rgba(0, 0, 0, ${opacity})`
      : `rgba(255, 255, 255, ${opacity * 0.3})`
  }

  // Systematic background colors for consistency
  const getBgColor = (level: 'card' | 'section' | 'input' | 'header' | 'hover' | 'muted') => {
    if (isLightTheme()) {
      switch (level) {
        case 'card': return 'rgba(255, 255, 255, 0.95)'
        case 'section': return 'rgba(0, 0, 0, 0.03)'
        case 'input': return 'rgba(255, 255, 255, 0.9)'
        case 'header': return 'rgba(0, 0, 0, 0.04)'
        case 'hover': return 'rgba(0, 0, 0, 0.06)'
        case 'muted': return 'rgba(0, 0, 0, 0.02)'
        default: return 'rgba(255, 255, 255, 0.95)'
      }
    } else {
      switch (level) {
        case 'card': return 'rgba(255, 255, 255, 0.03)'
        case 'section': return 'rgba(0, 0, 0, 0.1)'
        case 'input': return 'rgba(255, 255, 255, 0.05)'
        case 'header': return 'rgba(255, 255, 255, 0.05)'
        case 'hover': return 'rgba(255, 255, 255, 0.08)'
        case 'muted': return 'rgba(255, 255, 255, 0.02)'
        default: return 'rgba(255, 255, 255, 0.03)'
      }
    }
  }

  // Systematic border colors
  const getBorderColor = (emphasis: 'normal' | 'strong' | 'subtle' | 'light' = 'normal') => {
    if (isLightTheme()) {
      switch (emphasis) {
        case 'strong': return 'rgba(0, 0, 0, 0.15)'
        case 'subtle': return 'rgba(0, 0, 0, 0.06)'
        case 'light': return 'rgba(0, 0, 0, 0.08)'
        default: return 'rgba(0, 0, 0, 0.1)'
      }
    } else {
      switch (emphasis) {
        case 'strong': return 'rgba(255, 255, 255, 0.15)'
        case 'subtle': return 'rgba(255, 255, 255, 0.06)'
        case 'light': return 'rgba(255, 255, 255, 0.08)'
        default: return 'rgba(255, 255, 255, 0.1)'
      }
    }
  }

  // Load theme from localStorage on mount and listen for changes
  useEffect(() => {
    const loadTheme = () => {
      const savedTheme = localStorage.getItem('quathera-theme')
      if (savedTheme && themes[savedTheme]) {
        setCurrentTheme(savedTheme)
      }
    }
    loadTheme()
    
    // Listen for storage changes (when theme is changed in layout)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'quathera-theme' && e.newValue && themes[e.newValue]) {
        setCurrentTheme(e.newValue)
      }
    }
    window.addEventListener('storage', handleStorageChange)
    
    // Also poll for changes (in case same-tab changes don't trigger storage event)
    const interval = setInterval(loadTheme, 500)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  }, [])

  // Fetch test templates on mount
  useEffect(() => {
    const fetchTestTemplates = async () => {
      try {
        const response = await fetch('/api/test-templates')
        if (response.ok) {
          const data = await response.json()
          setTestTemplates(data.templates || [])
          // Auto-select first template
          if (data.templates?.length > 0) {
            setSelectedTemplateId(data.templates[0].id)
          }
        }
      } catch (err) {
        console.error('Failed to fetch test templates:', err)
      }
    }
    fetchTestTemplates()
  }, [])

  // Toggle step expansion
  const toggleStepExpansion = (index: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }


  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserId = localStorage.getItem('user_id')
    const storedCompanyId = localStorage.getItem('company_id')
    const storedProjectId = localStorage.getItem('active_project_id')
    const storedProjectName = localStorage.getItem('active_project_name')
    
    if (!storedToken) {
      window.location.href = '/login'
      return
    }
    
    setToken(storedToken)
    setUserId(storedUserId)
    setCompanyId(storedCompanyId)
    setActiveProjectId(storedProjectId)
    setActiveProjectName(storedProjectName)
    
    if (storedProjectId) {
      loadNetworks(storedProjectId, storedToken)
      loadFormPages(storedProjectId, storedToken)
      checkActiveSessions(storedProjectId, storedToken)
    }
  }, [])

  // Check for active/running sessions on page load
  const checkActiveSessions = async (projectId: string, authToken: string) => {
    try {
      const response = await fetch(
        `/api/form-pages/projects/${projectId}/active-sessions`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const activeSessions = await response.json()
        
        if (activeSessions.length > 0) {
          // There are active sessions - restore discovery state
          setIsDiscovering(true)
          shouldContinueRef.current = true
          
          // Build queue from active sessions
          const queue: DiscoveryQueueItem[] = activeSessions.map((session: any) => ({
            networkId: session.network_id,
            networkName: `Network ${session.network_id}`,
            status: session.status === 'running' ? 'running' : 'pending',
            sessionId: session.id,
            pagesSearched: session.pages_crawled || 0,
            formsFound: session.forms_found || 0
          }))
          
          setDiscoveryQueue(queue)
          
          // Find the running session and start polling it
          const runningSession = activeSessions.find((s: any) => s.status === 'running')
          if (runningSession) {
            setCurrentSessionId(runningSession.id)
            startPolling(queue, queue.findIndex(q => q.sessionId === runningSession.id), runningSession.id)
          }
        }
      }
    } catch (err) {
      console.error('Failed to check active sessions:', err)
    }
  }

  useEffect(() => {
    const handleProjectChange = (e: CustomEvent) => {
      const project = e.detail
      setActiveProjectId(project.id.toString())
      setActiveProjectName(project.name)
      setSelectedNetworkIds([])
      stopDiscovery()
      if (token) {
        loadNetworks(project.id.toString(), token)
        loadFormPages(project.id.toString(), token)
      }
    }
    
    window.addEventListener('activeProjectChanged', handleProjectChange as EventListener)
    return () => window.removeEventListener('activeProjectChanged', handleProjectChange as EventListener)
  }, [token])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // Fetch login/logout stages when formPages change
  useEffect(() => {
    if (formPages.length > 0 && token) {
      // Get unique network IDs from form pages
      const networkIds = [...new Set(formPages.map(fp => fp.network_id))] as number[]
      fetchLoginLogoutStages(networkIds, token)
    }
  }, [formPages, token])

  const loadNetworks = async (projectId: string, authToken: string) => {
    setLoadingNetworks(true)
    try {
      const response = await fetch(
        `/api/projects/${projectId}/networks`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        const allNetworks = [
          ...data.qa.map((n: Network) => ({ ...n, network_type: 'qa' })),
          ...data.staging.map((n: Network) => ({ ...n, network_type: 'staging' })),
          ...data.production.map((n: Network) => ({ ...n, network_type: 'production' }))
        ]
        setNetworks(allNetworks)
      }
    } catch (err) {
      console.error('Failed to load networks:', err)
    } finally {
      setLoadingNetworks(false)
    }
  }

  const loadFormPages = async (projectId: string, authToken: string) => {
    setLoadingFormPages(true)
    try {
      const response = await fetch(
        `/api/projects/${projectId}/form-pages`,
        { headers: { 'Authorization': `Bearer ${authToken}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        
        // Fetch paths counts for all form pages
        if (data.length > 0) {
          const ids = data.map((fp: any) => fp.id).join(',')
          const countsResponse = await fetch(
            `/api/form-mapper/routes/paths-counts?form_page_route_ids=${ids}`,
            { headers: { 'Authorization': `Bearer ${authToken}` } }
          )
          if (countsResponse.ok) {
            const counts = await countsResponse.json()
            setFormPages(data.map((fp: any) => ({
              ...fp,
              paths_count: counts[String(fp.id)] || 0
            })))
          } else {
            setFormPages(data)
          }
        } else {
          setFormPages(data)
        }
        
        // Check for active mapping sessions after loading form pages
        checkActiveMappingSessions(authToken)
      }
    } catch (err) {
      console.error('Failed to load form pages:', err)
    } finally {
      setLoadingFormPages(false)
    }
  }

  // Check for active mapping sessions and restore UI state
  const checkActiveMappingSessions = async (authToken: string) => {
    try {
      const response = await fetch('/api/form-mapper/active-sessions', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      
      if (response.ok) {
        const activeSessions = await response.json()
        // activeSessions is array of { form_page_route_id, session_id, status }
        
        const newMappingIds = new Set<number>()
        const newMappingStatus: Record<number, { status: string; sessionId?: number }> = {}
        
        for (const session of activeSessions) {
          const activeStatuses = ['running', 'initializing', 'pending', 'logging_in', 'navigating', 'extracting_initial_dom', 'getting_initial_screenshot', 'ai_analyzing', 'executing_step', 'waiting_for_dom', 'waiting_for_screenshot']
          if (activeStatuses.includes(session.status)) {
            newMappingIds.add(session.form_page_route_id)
            newMappingStatus[session.form_page_route_id] = {
              status: 'mapping',
              sessionId: session.session_id
            }
            // Resume polling for this session
            startMappingStatusPolling(session.form_page_route_id, session.session_id)
          }
        }
        
        if (newMappingIds.size > 0) {
          setMappingFormIds(newMappingIds)
          setMappingStatus(prev => ({ ...prev, ...newMappingStatus }))
        }
      }
    } catch (err) {
      console.error('Failed to check active mapping sessions:', err)
    }
  }

  // Fetch login/logout stages for networks
  const fetchLoginLogoutStages = async (networkIds: number[], authToken: string) => {
    const results: Record<number, LoginLogoutData> = {}
    
    for (const networkId of networkIds) {
      try {
        const response = await fetch(
          `/api/form-pages/networks/${networkId}/login-logout-stages`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`,
              'Content-Type': 'application/json'
            }
          }
        )
        if (response.ok) {
          const data = await response.json()
          results[networkId] = {
            login_stages: data.login_stages || [],
            logout_stages: data.logout_stages || [],
            network_name: data.network_name,
            url: data.url,
            updated_at: data.updated_at
          }
        }
      } catch (err) {
        console.error(`Failed to fetch login/logout for network ${networkId}:`, err)
      }
    }
    
    setLoginLogoutData(results)
  }

  // Open login/logout edit panel - creates a "fake" FormPage for reusing FormPageEditPanel
  const openLoginLogoutEditPanel = (networkId: number, type: 'login' | 'logout') => {
    const data = loginLogoutData[networkId]
    if (!data) return
    
    // Create a fake FormPage object with special negative ID
    // Login IDs: -1000 - networkId (e.g., -1001 for network 1)
    // Logout IDs: -2000 - networkId (e.g., -2001 for network 1)
    const fakeFormPage: FormPage = {
      id: type === 'login' ? (-1000 - networkId) : (-2000 - networkId),
      form_name: type === 'login' ? `🔐 Login - ${data.network_name}` : `🚪 Logout - ${data.network_name}`,
      url: data.url,
      network_id: networkId,
      navigation_steps: type === 'login' ? [...data.login_stages] : [...data.logout_stages],
      is_root: true,
      parent_form_id: null,
      created_at: data.updated_at || new Date().toISOString()
    }
    
    setEditingLoginLogout({
      networkId,
      type,
      steps: type === 'login' ? [...data.login_stages] : [...data.logout_stages],
      networkName: data.network_name,
      url: data.url
    })
    setEditingFormPage(fakeFormPage)
    setEditFormName(fakeFormPage.form_name)
    setEditNavigationSteps(type === 'login' ? [...data.login_stages] : [...data.logout_stages])
    setExpandedSteps(new Set())
    setCompletedPaths([])  // No paths for login/logout
    setShowEditPanel(true)
  }

  // Save login/logout steps
  const saveLoginLogoutSteps = async () => {
    if (!editingLoginLogout || !token) return
    
    setSavingFormPage(true)
    try {
      const endpoint = editingLoginLogout.type === 'login' 
        ? `/api/form-pages/networks/${editingLoginLogout.networkId}/login-stages`
        : `/api/form-pages/networks/${editingLoginLogout.networkId}/logout-stages`
      
      const body = editingLoginLogout.type === 'login'
        ? { login_stages: editNavigationSteps }
        : { logout_stages: editNavigationSteps }
      
      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        setMessage(`${editingLoginLogout.type === 'login' ? 'Login' : 'Logout'} steps updated successfully!`)
        
        // Update local state
        setLoginLogoutData(prev => ({
          ...prev,
          [editingLoginLogout.networkId]: {
            ...prev[editingLoginLogout.networkId],
            [editingLoginLogout.type === 'login' ? 'login_stages' : 'logout_stages']: editNavigationSteps
          }
        }))
        
        setShowEditPanel(false)
        setEditingLoginLogout(null)
      } else {
        setError('Failed to save steps')
      }
    } catch (err) {
      setError('Failed to save steps')
    } finally {
      setSavingFormPage(false)
    }
  }

  // ============================================
  // FORM MAPPING FUNCTIONS
  // ============================================
  
  const startFormMapping = async (formPage: FormPage) => {
    if (!token || !userId) return
    
    // Check if agent is online first
    try {
      const agentResponse = await fetch(`/api/agent/status?user_id=${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (agentResponse.ok) {
        const agentData = await agentResponse.json()
        if (agentData.status !== 'online') {
          setError('⚠️ Agent is offline. Please start your desktop agent before mapping.')
          return
        }
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
      // Continue anyway if check fails
    }

    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPage.id))
    setMappingStatus(prev => ({
      ...prev,
      [formPage.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetch('/api/form-mapper/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_page_route_id: formPage.id,
          user_id: parseInt(userId),
          company_id: companyId ? parseInt(companyId) : undefined,
          network_id: formPage.network_id,
          test_cases: [
            { test_id: 1, test_name: 'Default Test', description: 'Auto-generated test case' }
          ]
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [formPage.id]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      // Start polling for status
      startMappingStatusPolling(formPage.id, data.session_id)
      
      setMessage(`Started mapping: ${formPage.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPage.id)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPage.id]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to start mapping: ${err.message}`)
    }
  }

  const openMapModal = (formPage: FormPage) => {
    setSelectedFormForMapping(formPage)
    setShowMapModal(true)
  }

  const startMappingWithTemplate = async () => {
    if (!selectedFormForMapping || !selectedTemplateId || !token || !userId) return
    
    const template = testTemplates.find(t => t.id === selectedTemplateId)
    if (!template) return
    
    // Check if agent is online first
    try {
      const agentResponse = await fetch(`/api/agent/status?user_id=${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (agentResponse.ok) {
        const agentData = await agentResponse.json()
        if (agentData.status !== 'online') {
          setError('⚠️ Agent is offline. Please start your desktop agent before mapping.')
          return
        }
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
    }

    setShowMapModal(false)
    
    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(selectedFormForMapping.id))
    setMappingStatus(prev => ({
      ...prev,
      [selectedFormForMapping.id]: { status: 'starting' }
    }))
    
    try {
      const response = await fetch('/api/form-mapper/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_page_route_id: selectedFormForMapping.id,
          user_id: parseInt(userId),
          company_id: companyId ? parseInt(companyId) : undefined,
          network_id: selectedFormForMapping.network_id,
          test_cases: template.test_cases
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [selectedFormForMapping.id]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      startMappingStatusPolling(selectedFormForMapping.id, data.session_id)
      setMessage(`Started mapping: ${selectedFormForMapping.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(selectedFormForMapping.id)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [selectedFormForMapping.id]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to start mapping: ${err.message}`)
    }
    
    setSelectedFormForMapping(null)
  }

  const startMappingFromEditPanel = async () => {
    if (!editingFormPage || !token || !userId) return
    
    // Warn if paths exist - they will be deleted on remap
    if (completedPaths.length > 0) {
      const confirmed = confirm(`⚠️ This form has ${completedPaths.length} existing path(s). Re-mapping will DELETE all existing paths. Continue?`)
      if (!confirmed) return
    }
    
    // Check if agent is online first
    try {
      const agentResponse = await fetch(`/api/agent/status?user_id=${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (agentResponse.ok) {
        const agentData = await agentResponse.json()
        if (agentData.status !== 'online') {
          setError('⚠️ Agent is offline. Please start your desktop agent before mapping.')
          return
        }
      }
    } catch (err) {
      console.error('Failed to check agent status:', err)
    }

    // Use default template (first one) or create_verify if available
    const defaultTemplate = testTemplates.find(t => t.name === 'create_verify') || testTemplates[0]
    if (!defaultTemplate) {
      setError('No test template available')
      return
    }
    
    const formPageId = editingFormPage.id
    
    // Mark as mapping
    setMappingFormIds(prev => new Set(prev).add(formPageId))
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'starting' }
    }))
    
    try {
      const response = await fetch('/api/form-mapper/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_page_route_id: formPageId,
          user_id: parseInt(userId),
          company_id: companyId ? parseInt(companyId) : undefined,
          network_id: editingFormPage.network_id,
          test_cases: defaultTemplate.test_cases
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start mapping')
      }
      
      const data = await response.json()
      
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: data.session_id }
      }))
      
      // Clear existing paths (they will be refreshed when mapping completes)
      setCompletedPaths([])
      
      startMappingStatusPolling(formPageId, data.session_id)
      setMessage(`Started mapping: ${editingFormPage.form_name}`)
      
    } catch (err: any) {
      console.error('Failed to start mapping:', err)
      setMappingFormIds(prev => {
        const next = new Set(prev)
        next.delete(formPageId)
        return next
      })
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'failed', error: err.message }
      }))
      setError(`Failed to start mapping: ${err.message}`)
    }
  }
  
  const startMappingStatusPolling = (formPageId: number, sessionId: number) => {
    // Clear any existing polling for this form
    if (mappingPollingRef.current[formPageId]) {
      clearInterval(mappingPollingRef.current[formPageId])
    }
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/form-mapper/sessions/${sessionId}/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const data = await response.json()
          
          setMappingStatus(prev => ({
            ...prev,
            [formPageId]: { 
              status: data.status, 
              sessionId,
              error: data.error 
            }
          }))
          
          // Auto-refresh completed paths if edit panel is open for this form (during mapping too)
          if (editingFormPage && editingFormPage.id === formPageId) {
            fetchCompletedPaths(formPageId)
          }

          // Stop polling if completed or failed
          if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
            stopMappingStatusPolling(formPageId)
            setMappingFormIds(prev => {
              const next = new Set(prev)
              next.delete(formPageId)
              return next
            })

            if (data.status === 'completed') {
              setMessage(`Mapping completed for form page ${formPageId}`)
              // Always refresh paths when mapping completes
              fetchCompletedPaths(formPageId)
            } else if (data.status === 'failed') {
              setError(`Mapping failed: ${data.error || 'Unknown error'}`)
            }
          }
        }
      } catch (err) {
        console.error('Failed to poll mapping status:', err)
      }
    }
    
    // Poll immediately, then every 3 seconds
    poll()
    mappingPollingRef.current[formPageId] = setInterval(poll, 3000)
  }
  
  const stopMappingStatusPolling = (formPageId: number) => {
    if (mappingPollingRef.current[formPageId]) {
      clearInterval(mappingPollingRef.current[formPageId])
      delete mappingPollingRef.current[formPageId]
    }
  }
  
  // Cancel a running mapping session
  const cancelMapping = async (formPageId: number) => {
    const status = mappingStatus[formPageId]
    if (!status?.sessionId) {
      console.error('No session ID found for form page', formPageId)
      return
    }
    
    // Immediately show "Stopping..." state
    setMappingStatus(prev => ({
      ...prev,
      [formPageId]: { status: 'stopping', sessionId: status.sessionId }
    }))
    
    try {
      const response = await fetch(`/api/form-mapper/sessions/${status.sessionId}/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        // Stop old polling
        stopMappingStatusPolling(formPageId)
        
        // Store the sessionId we're cancelling
        const cancelledSessionId = status.sessionId
        
        // Start polling until fully stopped (cancelled, failed, or completed)
        const pollUntilStopped = setInterval(async () => {
          try {
            const statusResponse = await fetch(`/api/form-mapper/sessions/${cancelledSessionId}/status`, {
              headers: { 'Authorization': `Bearer ${token}` }
            })
            if (statusResponse.ok) {
              const data = await statusResponse.json()
              const sessionStatus = data.session?.status || data.status
              
              // Terminal states - fully stopped
              if (['cancelled', 'cancelled_ack', 'failed', 'completed'].includes(sessionStatus)) {
                clearInterval(pollUntilStopped)
                // Only update UI if no new session started for this form
                setMappingStatus(prev => {
                  if (prev[formPageId]?.sessionId === cancelledSessionId) {
                    setMappingFormIds(prevIds => {
                      const next = new Set(prevIds)
                      next.delete(formPageId)
                      return next
                    })
                    setMessage('Mapping stopped')
                    return { ...prev, [formPageId]: { status: 'cancelled', sessionId: cancelledSessionId } }
                  }
                  return prev
                })
              }
            }
          } catch (err) {
            console.error('Error polling for stop status:', err)
          }
        }, 1000)
        
        // Safety timeout - stop polling after 30 seconds regardless
        setTimeout(() => {
          clearInterval(pollUntilStopped)
          // Only update UI if no new session started for this form
          setMappingStatus(prev => {
            if (prev[formPageId]?.sessionId === cancelledSessionId) {
              setMappingFormIds(prevIds => {
                const next = new Set(prevIds)
                next.delete(formPageId)
                return next
              })
              return { ...prev, [formPageId]: { status: 'cancelled', sessionId: cancelledSessionId } }
            }
            return prev
          })
        }, 30000)
        
      } else {
        const errorData = await response.json()
        setError(`Failed to cancel mapping: ${errorData.detail || 'Unknown error'}`)
        // Revert to mapping state on error
        setMappingStatus(prev => ({
          ...prev,
          [formPageId]: { status: 'mapping', sessionId: status.sessionId }
        }))
      }
    } catch (err: any) {
      console.error('Failed to cancel mapping:', err)
      setError(`Failed to cancel mapping: ${err.message}`)
      // Revert to mapping state on error
      setMappingStatus(prev => ({
        ...prev,
        [formPageId]: { status: 'mapping', sessionId: status.sessionId }
      }))
    }
  }
  
  // Cleanup mapping polling on unmount
  useEffect(() => {
    return () => {
      Object.keys(mappingPollingRef.current).forEach(key => {
        clearInterval(mappingPollingRef.current[parseInt(key)])
      })
    }
  }, [])

  const qaNetworks = networks.filter(n => n.network_type?.toLowerCase() === 'qa')

  const getOverallStats = () => {
    const runningCount = discoveryQueue.filter(q => q.status === 'running').length
    const completedCount = discoveryQueue.filter(q => q.status === 'completed').length
    const failedCount = discoveryQueue.filter(q => q.status === 'failed').length
    const cancelledCount = discoveryQueue.filter(q => q.status === 'cancelled').length
    const totalFormsFound = discoveryQueue.reduce((sum, q) => sum + q.formsFound, 0)
    
    return { runningCount, completedCount, failedCount, cancelledCount, totalFormsFound }
  }

  const toggleNetworkSelection = (networkId: number) => {
    setSelectedNetworkIds(prev =>
      prev.includes(networkId)
        ? prev.filter(id => id !== networkId)
        : [...prev, networkId]
    )
  }

  const selectAllNetworks = () => {
    if (selectedNetworkIds.length === qaNetworks.length) {
      setSelectedNetworkIds([])
    } else {
      setSelectedNetworkIds(qaNetworks.map(n => n.id))
    }
  }

  const stopDiscovery = async () => {
    // Stop frontend polling
    shouldContinueRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    
    // Call backend to cancel running sessions
    if (currentSessionId && token) {
      try {
        await fetch(
          `/api/form-pages/sessions/${currentSessionId}/cancel`,
          { 
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` } 
          }
        )
      } catch (err) {
        console.error('Failed to cancel session:', err)
      }
    }
    
    // Update queue to show cancelled status
    setDiscoveryQueue(prev => prev.map(q => 
      q.status === 'running' || q.status === 'pending'
        ? { ...q, status: 'cancelled' }
        : q
    ))
    
    setIsDiscovering(false)
    setCurrentSessionId(null)
    setCurrentNetworkIndex(-1)
  }

  const startDiscovery = async () => {
    if (selectedNetworkIds.length === 0 || !userId) {
      setError('Please select at least one network')
      return
    }
    
    setError(null)
    setMessage(null)
    setIsDiscovering(true)
    shouldContinueRef.current = true
    
    // Build the queue with all selected networks
    const queue: DiscoveryQueueItem[] = selectedNetworkIds.map(networkId => {
      const network = networks.find(n => n.id === networkId)
      return {
        networkId,
        networkName: network?.name || `Network ${networkId}`,
        status: 'pending',
        pagesSearched: 0,
        formsFound: 0
      }
    })
    
    setDiscoveryQueue(queue)
    setCurrentNetworkIndex(0)
    
    // Start the first network
    await startNetworkDiscovery(queue, 0)
  }

  const startNetworkDiscovery = async (queue: DiscoveryQueueItem[], index: number) => {
    if (!shouldContinueRef.current || index >= queue.length) {
      // All done!
      finishDiscovery(queue)
      return
    }
    
    const item = queue[index]
    
    // Update queue status to running
    const updatedQueue = queue.map((q, i) => 
      i === index ? { ...q, status: 'running' as const } : q
    )
    setDiscoveryQueue(updatedQueue)
    setCurrentNetworkIndex(index)
    
    try {
      const params = new URLSearchParams({
        user_id: userId!,
        headless: headless.toString()
      })
      
      const response = await fetch(
        `/api/form-pages/networks/${item.networkId}/locate?${params}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        const sessionId = data.crawl_session_id
        
        // Update queue with session ID
        const queueWithSession = updatedQueue.map((q, i) => 
          i === index ? { ...q, sessionId } : q
        )
        setDiscoveryQueue(queueWithSession)
        setCurrentSessionId(sessionId)
        
        // Start polling this session
        startPolling(queueWithSession, index, sessionId)
      } else {
        const errData = await response.json()
        console.error(`Failed to start discovery for network ${item.networkId}:`, errData.detail)
        
        // Mark as failed and move to next
        const failedQueue = updatedQueue.map((q, i) => 
          i === index ? { ...q, status: 'failed' as const, errorMessage: errData.detail } : q
        )
        setDiscoveryQueue(failedQueue)
        
        // Move to next network
        await startNetworkDiscovery(failedQueue, index + 1)
      }
    } catch (err) {
      console.error(`Connection error for network ${item.networkId}:`, err)
      
      // Mark as failed and move to next
      const failedQueue = updatedQueue.map((q, i) => 
        i === index ? { ...q, status: 'failed' as const, errorMessage: 'Connection error' } : q
      )
      setDiscoveryQueue(failedQueue)
      
      // Move to next network
      await startNetworkDiscovery(failedQueue, index + 1)
    }
  }

  const startPolling = (queue: DiscoveryQueueItem[], index: number, sessionId: number) => {
    // Clear any existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    pollingRef.current = setInterval(async () => {
      if (!shouldContinueRef.current) {
        if (pollingRef.current) clearInterval(pollingRef.current)
        return
      }
      
      try {
        const response = await fetch(
          `/api/form-pages/sessions/${sessionId}/status`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )
        
        if (response.ok) {
          const data: SessionStatus = await response.json()
          
          // Add new forms from this session to the list (without full reload)
          if (data.forms && data.forms.length > 0) {
            setFormPages(prev => {
              const existingIds = new Set(prev.map(f => f.id))
              const newForms = data.forms.filter(f => !existingIds.has(f.id))
              if (newForms.length > 0) {
                return [...newForms, ...prev]
              }
              return prev
            })
          }
          
          // Update queue with current progress
          setDiscoveryQueue(prev => prev.map((q, i) => 
            i === index ? {
              ...q,
              pagesSearched: data.session.pages_crawled,
              formsFound: data.session.forms_found
            } : q
          ))
          
          // Check if completed or failed
          if (data.session.status === 'completed' || data.session.status === 'failed') {
            // Stop polling this session
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
            
            // Update final status
            const finalStatus = data.session.status === 'completed' ? 'completed' : 'failed'
            const updatedQueue = queue.map((q, i) => 
              i === index ? {
                ...q,
                status: finalStatus as 'completed' | 'failed',
                pagesSearched: data.session.pages_crawled,
                formsFound: data.session.forms_found,
                errorMessage: getErrorMessage(data.session.error_code, data.session.error_message),
                errorCode: data.session.error_code || undefined
              } : q
            )
            setDiscoveryQueue(updatedQueue)
            setCurrentSessionId(null)
            
            // Move to next network
            if (shouldContinueRef.current) {
              await startNetworkDiscovery(updatedQueue, index + 1)
            }
          }
        }
      } catch (err) {
        console.error('Failed to poll status:', err)
      }
    }, 3000)
  }

  const finishDiscovery = (queue: DiscoveryQueueItem[]) => {
    stopDiscovery()
    
    const completed = queue.filter(q => q.status === 'completed').length
    const failed = queue.filter(q => q.status === 'failed').length
    const totalForms = queue.reduce((sum, q) => sum + q.formsFound, 0)
    const failedItems = queue.filter(q => q.status === 'failed')
    
    if (failed > 0) {
      // Build error details for failed networks
      const errorDetails = failedItems.map(f => `${f.networkName}: ${f.errorMessage || 'Unknown error'}`).join('; ')
      setMessage(`Discovery finished. Completed: ${completed}, Failed: ${failed}. Found ${totalForms} form pages.`)
      if (failedItems.length > 0 && failedItems[0].errorMessage) {
        setError(errorDetails)
      }
    } else {
      setMessage(`Discovery completed! Found ${totalForms} new form pages across ${completed} test site(s).`)
    }
    
    // Reload form pages
    if (activeProjectId && token) {
      loadFormPages(activeProjectId, token)
    }
  }

  const getNetworkTypeLabel = (type: string) => {
    switch (type) {
      case 'qa': return 'QA'
      case 'staging': return 'Staging'
      case 'production': return 'Prod'
      default: return type
    }
  }

  const getNetworkTypeColors = (type: string) => {
    const colors: Record<string, { bg: string; color: string; border: string }> = {
      qa: { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' },
      staging: { bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' },
      production: { bg: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' }
    }
    return colors[type] || { bg: 'rgba(255,255,255,0.05)', color: '#94a3b8', border: 'rgba(255,255,255,0.1)' }
  }

  const openEditPanel = (formPage: FormPage) => {
    setEditingFormPage(formPage)
    setEditFormName(formPage.form_name)
    setEditNavigationSteps(formPage.navigation_steps || [])
    setExpandedSteps(new Set()) // Collapse all steps initially
    setCompletedPaths([]) // Reset paths
    setExpandedPathId(null)
    setShowEditPanel(true)
    if (formPage.id >= 0) {
      fetchCompletedPaths(formPage.id) // Fetch completed paths for regular forms only
    }
  }

  // Build combined list of all navigable items (login/logout + form pages)
  // This is used for Previous/Next navigation in the edit panel
  // Order matches the table display: Form pages (sorted) → Login → Logout (per network)
  const getAllNavigableItems = (): FormPage[] => {
    const items: FormPage[] = []
    
    // Get all network IDs from both form pages and login/logout data
    const networkIdsFromForms = [...new Set(formPages.map(fp => fp.network_id))]
    const networkIdsFromLoginLogout = Object.keys(loginLogoutData).map(id => parseInt(id))
    const allNetworkIds = [...new Set([...networkIdsFromForms, ...networkIdsFromLoginLogout])]
    
    // Sort network IDs for consistent ordering
    allNetworkIds.sort((a, b) => a - b)
    
    for (const networkId of allNetworkIds) {
      const loginLogout = loginLogoutData[networkId]
      
      // Add form pages for this network first (sorted by name)
      const networkFormPages = formPages
        .filter(fp => fp.network_id === networkId)
        .sort((a, b) => (a.form_name || '').localeCompare(b.form_name || ''))
      items.push(...networkFormPages)
      
      // Add login entry for this network (if exists)
      if (loginLogout && loginLogout.login_stages && loginLogout.login_stages.length > 0) {
        items.push({
          id: -1000 - networkId, // Unique negative ID per network for login
          form_name: `🔐 Login - ${loginLogout.network_name}`,
          url: loginLogout.url,
          network_id: networkId,
          navigation_steps: loginLogout.login_stages,
          is_root: true,
          parent_form_id: null,
          created_at: loginLogout.updated_at || new Date().toISOString()
        })
      }
      
      // Add logout entry for this network (if exists)
      if (loginLogout && loginLogout.logout_stages && loginLogout.logout_stages.length > 0) {
        items.push({
          id: -2000 - networkId, // Unique negative ID per network for logout
          form_name: `🚪 Logout - ${loginLogout.network_name}`,
          url: loginLogout.url,
          network_id: networkId,
          navigation_steps: loginLogout.logout_stages,
          is_root: true,
          parent_form_id: null,
          created_at: loginLogout.updated_at || new Date().toISOString()
        })
      }
    }
    
    return items
  }

  const navigateToPreviousFormPage = () => {
    if (!editingFormPage) return
    const allItems = getAllNavigableItems()
    const currentIndex = allItems.findIndex(fp => fp.id === editingFormPage.id)
    if (currentIndex > 0) {
      const prevItem = allItems[currentIndex - 1]
      // Check if it's a login/logout item (negative ID)
      if (prevItem.id < 0) {
        // Extract network ID from the special ID
        const networkId = prevItem.id <= -2000 ? -(prevItem.id + 2000) : -(prevItem.id + 1000)
        const type = prevItem.id <= -2000 ? 'logout' : 'login'
        openLoginLogoutEditPanel(networkId, type)
      } else {
        openEditPanel(prevItem)
      }
    }
  }

  const navigateToNextFormPage = () => {
    if (!editingFormPage) return
    const allItems = getAllNavigableItems()
    const currentIndex = allItems.findIndex(fp => fp.id === editingFormPage.id)
    if (currentIndex < allItems.length - 1) {
      const nextItem = allItems[currentIndex + 1]
      // Check if it's a login/logout item (negative ID)
      if (nextItem.id < 0) {
        // Extract network ID from the special ID
        const networkId = nextItem.id <= -2000 ? -(nextItem.id + 2000) : -(nextItem.id + 1000)
        const type = nextItem.id <= -2000 ? 'logout' : 'login'
        openLoginLogoutEditPanel(networkId, type)
      } else {
        openEditPanel(nextItem)
      }
    }
  }

  const getCurrentFormPageIndex = () => {
    if (!editingFormPage) return -1
    const allItems = getAllNavigableItems()
    return allItems.findIndex(fp => fp.id === editingFormPage.id)
  }

  const getTotalNavigableItems = () => {
    return getAllNavigableItems().length
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

  // ============ COMPLETED PATHS FUNCTIONS ============
  const fetchCompletedPaths = async (formPageRouteId: number) => {
    if (!token) return
    try {
      setLoadingPaths(true)
      const response = await fetch(
        `/api/form-mapper/routes/${formPageRouteId}/paths`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      if (response.ok) {
        const data = await response.json()
        setCompletedPaths(data.paths || [])
      } else {
        setCompletedPaths([])
      }
    } catch (err) {
      console.error('Failed to fetch completed paths:', err)
      setCompletedPaths([])
    } finally {
      setLoadingPaths(false)
    }
  }

  const handlePathRowDoubleClick = (pathId: number) => {
    setExpandedPathId(expandedPathId === pathId ? null : pathId)
    setEditingPathStep(null)
  }

  const handleEditPathStep = (pathId: number, stepIndex: number, step: any) => {
    setEditingPathStep({ pathId, stepIndex })
    setEditedPathStepData({
      action: step.action,
      selector: step.selector,
      value: step.value || '',
      description: step.description || ''
    })
  }

  const handleSavePathStep = async (pathId: number, stepIndex: number, stepData?: any) => {
    if (!token) return
    const dataToSave = stepData || editedPathStepData
    try {
      const response = await fetch(
        `/api/form-mapper/paths/${pathId}/steps/${stepIndex}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(dataToSave)
        }
      )
      if (response.ok) {
        setCompletedPaths(completedPaths.map(path => {
          if (path.id === pathId) {
            const updatedSteps = [...path.steps]
            updatedSteps[stepIndex] = { ...updatedSteps[stepIndex], ...dataToSave }
            return { ...path, steps: updatedSteps }
          }
          return path
        }))
        setEditingPathStep(null)
        setEditedPathStepData({})
      }
    } catch (err) {
      console.error('Failed to save step:', err)
    }
  }

  const handleCancelPathStepEdit = () => {
    setEditingPathStep(null)
    setEditedPathStepData({})
  }

  const downloadPathJson = (path: CompletedPath) => {
    const jsonData = {
      path_number: path.path_number,
      path_junctions: path.path_junctions,
      steps: path.steps,
      steps_count: path.steps?.length || 0,
      is_verified: path.is_verified,
      created_at: path.created_at,
      form_page: editingFormPage?.form_name || 'unknown'
    }
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `path_${path.path_number}_${editingFormPage?.form_name?.replace(/\s+/g, '_') || 'form'}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getDisplaySteps = (steps: any[]): any[] => {
    return (steps || []).map(step => {
      const { is_junction, junction_info, ...displayStep } = step
      return displayStep
    })
  }

  const saveFormPage = async () => {
    if (!editingFormPage || !token) return
    
    setSavingFormPage(true)
    try {
      const response = await fetch(
        `/api/form-pages/routes/${editingFormPage.id}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            form_name: editFormName,
            navigation_steps: editNavigationSteps
          })
        }
      )
      
      if (response.ok) {
        setMessage('Form page updated successfully!')
        setShowEditPanel(false)
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId, token)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to update form page')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setSavingFormPage(false)
    }
  }

  const openDeleteModal = (formPage: FormPage) => {
    setFormPageToDelete(formPage)
    setShowDeleteModal(true)
  }

  const deleteFormPage = async () => {
    if (!formPageToDelete || !token) return
    
    setDeletingFormPage(true)
    try {
      const response = await fetch(
        `/api/form-pages/routes/${formPageToDelete.id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        setMessage('Form page deleted successfully!')
        setShowDeleteModal(false)
        setFormPageToDelete(null)
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId, token)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete form page')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingFormPage(false)
    }
  }

  // Rediscover form page - deletes and redirects to main page with discovery expanded
  const rediscoverFormPage = async (formPageId: number) => {
    if (!token) return
    
    try {
      const response = await fetch(
        `/api/form-pages/routes/${formPageId}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )
      
      if (response.ok) {
        // Close edit panel
        setShowEditPanel(false)
        setEditingFormPage(null)
        
        // Expand discovery section
        setIsDiscoveryExpanded(true)
        
        // Show message to user
        setRediscoverMessage('Form page deleted. Select a test site and click "Start Discovery" to rediscover form pages.')
        
        // Reload form pages
        if (activeProjectId) {
          loadFormPages(activeProjectId, token)
        }
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete form page')
      }
    } catch (err) {
      setError('Connection error')
    }
  }

  // No project selected
  if (!activeProjectId) {
    return (
      <div style={{ maxWidth: '700px', margin: '0 auto' }}>
        <div style={{
          background: getTheme().colors.cardBg,
          backdropFilter: 'blur(20px)',
          borderRadius: '28px',
          padding: '80px',
          textAlign: 'center',
          border: `2px solid ${getTheme().colors.cardBorder}`,
          boxShadow: `${getTheme().colors.cardGlow}, 0 20px 60px rgba(0,0,0,0.3)`
        }}>
          <div style={{ fontSize: '64px', marginBottom: '24px' }}>👋</div>
          <h2 style={{ margin: '0 0 16px', fontSize: '28px', fontWeight: 700, color: getTheme().colors.textPrimary, textShadow: getTheme().colors.textGlow }}>Welcome!</h2>
          <p style={{ fontSize: '16px', color: getTheme().colors.textSecondary, margin: 0 }}>Please select a project from the top bar to get started.</p>
          <p style={{ color: getTheme().colors.textSecondary, fontSize: '14px', marginTop: '12px', opacity: 0.7 }}>
            If you don't have any projects yet, click on the project dropdown and choose "Add Project".
          </p>
        </div>
      </div>
    )
  }

  const stats = getOverallStats()
  const totalNetworks = discoveryQueue.length
  const completedNetworks = stats.completedCount + stats.failedCount + stats.cancelledCount

  // ============ FULL PAGE EDIT VIEW ============
  if (showEditPanel && editingFormPage) {
    // Determine if this is a login/logout edit (using special negative IDs)
    // Login IDs: -1001, -1002, etc (for network 1, 2, etc)
    // Logout IDs: -2001, -2002, etc (for network 1, 2, etc)
    const isLoginLogoutEdit = editingFormPage.id < 0
    const loginLogoutType = (editingFormPage.id <= -1000 && editingFormPage.id > -2000) 
      ? 'login' 
      : (editingFormPage.id <= -2000 ? 'logout' : null)
    
    return (
      <FormPageEditPanel
        editingFormPage={editingFormPage}
        formPages={getAllNavigableItems()}
        completedPaths={isLoginLogoutEdit ? [] : completedPaths}
        loadingPaths={isLoginLogoutEdit ? false : loadingPaths}
        token={token || ''}
        editFormName={editFormName}
        setEditFormName={setEditFormName}
        editNavigationSteps={editNavigationSteps}
        setEditNavigationSteps={setEditNavigationSteps}
        savingFormPage={savingFormPage}
        expandedSteps={expandedSteps}
        setExpandedSteps={setExpandedSteps}
        mappingFormIds={mappingFormIds}
        mappingStatus={mappingStatus}
        expandedPathId={expandedPathId}
        setExpandedPathId={setExpandedPathId}
        editingPathStep={editingPathStep}
        setEditingPathStep={setEditingPathStep}
        editedPathStepData={editedPathStepData}
        setEditedPathStepData={setEditedPathStepData}
        showDeleteStepConfirm={showDeleteStepConfirm}
        setShowDeleteStepConfirm={setShowDeleteStepConfirm}
        stepToDeleteIndex={stepToDeleteIndex}
        setStepToDeleteIndex={setStepToDeleteIndex}
        error={error}
        setError={setError}
        message={message}
        setMessage={setMessage}
        onClose={() => { 
          setShowEditPanel(false)
          if (isLoginLogoutEdit) {
            setEditingLoginLogout(null)
          }
        }}
        onSave={isLoginLogoutEdit ? saveLoginLogoutSteps : saveFormPage}
        onStartMapping={isLoginLogoutEdit ? () => {} : startMappingFromEditPanel}
        onCancelMapping={cancelMapping}
        onOpenEditPanel={openEditPanel}
        onDeletePath={(pathId: number) => { /* TODO: implement */ }}
        onSavePathStep={handleSavePathStep}
        onExportPath={downloadPathJson}
        onRefreshPaths={() => !isLoginLogoutEdit && fetchCompletedPaths(editingFormPage.id)}
        onDeleteFormPage={isLoginLogoutEdit ? () => {} : rediscoverFormPage}
        getTheme={getTheme}
        isLightTheme={isLightTheme}
        isLoginLogout={isLoginLogoutEdit}
        loginLogoutType={loginLogoutType}
      />
    )
  }


  // ============ MAIN DISCOVERY PAGE ============
  return (
    <div style={{ width: '100%' }}>
        {/* CSS Animations */}
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.05); }
          }
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          .network-card:hover {
            border-color: ${getTheme().colors.accentPrimary}80 !important;
            transform: translateY(-2px);
            box-shadow: 0 8px 30px ${getTheme().colors.accentGlow} !important;
          }
          .table-row {
            background: ${isLightTheme() ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.01)'};
            ${isLightTheme() ? 'box-shadow: 0 1px 3px rgba(0,0,0,0.08);' : ''}
          }
          .table-row:hover {
            background: ${isLightTheme() ? 'rgba(0, 0, 0, 0.06)' : `${getTheme().colors.accentPrimary}15`} !important;
          }
          .table-row:nth-child(even) {
            background: ${isLightTheme() ? 'rgba(0, 0, 0, 0.03)' : 'rgba(255, 255, 255, 0.03)'};
          }
          .action-btn:hover {
            transform: scale(1.1);
            background: ${isLightTheme() ? 'rgba(0, 0, 0, 0.15)' : `${getTheme().colors.accentPrimary}35`} !important;
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

        {/* Form Pages Discovery Section - Collapsible */}
        <div style={{
          marginBottom: '28px',
          background: isLightTheme() 
            ? 'linear-gradient(135deg, rgba(242, 246, 250, 0.98) 0%, rgba(242, 246, 250, 0.95) 100%)'
            : 'rgba(255,255,255,0.03)',
          border: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.25)' : 'rgba(255,255,255,0.1)'}`,
          borderRadius: '12px',
          padding: '20px',
          boxShadow: isLightTheme() 
            ? '0 4px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08)'
            : '0 4px 12px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.2)'
        }}>
          {/* Clickable Header to expand/collapse */}
          <div 
            onClick={() => !isDiscovering && setIsDiscoveryExpanded(!isDiscoveryExpanded)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              paddingBottom: isDiscoveryExpanded ? '16px' : '0',
              borderBottom: isDiscoveryExpanded ? `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}` : 'none',
              marginBottom: isDiscoveryExpanded ? '16px' : 0,
              cursor: isDiscovering ? 'default' : 'pointer'
          }}
        >
          <div style={{
            fontSize: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '44px',
            height: '44px',
            background: isLightTheme() 
              ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
              : `linear-gradient(135deg, ${getTheme().colors.accentPrimary}, ${getTheme().colors.accentSecondary})`,
            borderRadius: '10px',
            boxShadow: isLightTheme() 
              ? '0 2px 6px rgba(37, 99, 235, 0.3)'
              : '0 2px 8px rgba(99, 102, 241, 0.3)'
          }}>
            <span style={{ fontSize: '22px' }}>🧭</span>
          </div>
          <div style={{ flex: 1 }}>
            <h1 style={{
              margin: 0,
              fontSize: '24px',
              fontWeight: 700,
              color: getTheme().colors.textPrimary
            }}>Form Pages Discovery</h1>
            <p style={{
              margin: '6px 0 0',
              fontSize: '15px',
              color: getTheme().colors.textSecondary
            }}>
              {isDiscoveryExpanded 
                ? 'Automatically discover all form pages in your web application using AI-powered crawling'
                : `Click to ${formPages.length > 0 ? 'start a new discovery' : 'begin discovering form pages'}`}
            </p>
          </div>
          {isDiscovering ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 20px',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              color: getTheme().colors.statusOnline,
              background: `${getTheme().colors.statusOnline}15`,
              border: `1px solid ${getTheme().colors.statusOnline}30`
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: getTheme().colors.statusOnline,
                animation: 'pulse 1.5s infinite'
              }} />
              <span>Discovery in Progress</span>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              background: isDiscoveryExpanded 
                ? (isLightTheme() ? 'rgba(220, 38, 38, 0.08)' : 'rgba(239, 68, 68, 0.15)')
                : getTheme().colors.accentPrimary,
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
              color: isDiscoveryExpanded 
                ? (isLightTheme() ? '#dc2626' : '#f87171')
                : '#fff'
            }}>
              <span style={{ fontSize: '13px' }}>{isDiscoveryExpanded ? '▲' : '▼'}</span>
              {isDiscoveryExpanded ? 'Collapse' : 'Expand'}
            </div>
          )}
        </div>

        {/* Collapsible Content */}
        {(isDiscoveryExpanded || isDiscovering) && (
          networks.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '100px 60px',
              background: `${getTheme().colors.cardBg}`,
              borderRadius: '20px',
              border: `1px solid ${getTheme().colors.cardBorder}`
            }}>
              <div style={{ fontSize: '64px', marginBottom: '24px' }}>🌐</div>
              <h3 style={{ margin: '0 0 16px', fontSize: '26px', color: getTheme().colors.textPrimary, fontWeight: 600 }}>No Networks Found</h3>
              <p style={{ margin: 0, color: getTheme().colors.textSecondary, fontSize: '18px' }}>
                Open the <strong style={{ color: getTheme().colors.textPrimary }}>Test Sites</strong> tab from the sidebar to add your first test site.
              </p>
            </div>
          ) : (
            <>
              {/* Rediscover Message */}
              {rediscoverMessage && (
                <div style={{
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '20px 24px',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  boxShadow: '0 4px 15px rgba(245, 158, 11, 0.4)'
                }}>
                  <span style={{ fontSize: '32px' }}>🔄</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, color: '#fff', fontWeight: 600, fontSize: '16px' }}>
                      {rediscoverMessage}
                    </p>
                  </div>
                  <button
                    onClick={() => setRediscoverMessage(null)}
                    style={{
                      background: 'rgba(255,255,255,0.2)',
                      border: 'none',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: '18px',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontWeight: 600
                    }}
                  >
                    ✕
                  </button>
                </div>
              )}
              
              {/* Network Selection */}
              <div style={{ 
                marginBottom: '16px',
                background: isLightTheme() 
                  ? 'rgba(16, 185, 129, 0.06)' 
                  : 'rgba(16, 185, 129, 0.08)',
                borderRadius: '12px',
                padding: '20px',
                border: `1px solid ${isLightTheme() ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.2)'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <h3 style={{ 
                      margin: 0,
                      fontSize: '20px',
                      fontWeight: 600,
                      color: getTheme().colors.textPrimary
                    }}>Select Test Sites</h3>
                    <p style={{ 
                      margin: '6px 0 0',
                      fontSize: '15px',
                      color: getTheme().colors.textSecondary
                    }}>Select QA environment test sites to discover form pages</p>
                  </div>
                  <button 
                    onClick={selectAllNetworks} 
                    style={{
                      background: isLightTheme() ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.06)',
                      color: getTheme().colors.textPrimary,
                      border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)'}`,
                      padding: '10px 18px',
                      borderRadius: '6px',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    disabled={isDiscovering}
                  >
                    {selectedNetworkIds.length === qaNetworks.length ? '✓ All Selected' : 'Select All'}
                  </button>
                </div>

                <div style={{ 
                  border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.12)'}`,
                  borderRadius: '8px',
                  overflow: 'hidden',
                  background: isLightTheme() ? 'rgba(242, 246, 250, 0.9)' : 'rgba(255,255,255,0.02)',
                  boxShadow: isLightTheme() 
                    ? '0 2px 6px rgba(0,0,0,0.06)'
                    : '0 2px 6px rgba(0,0,0,0.2)'
                }}>
                  {qaNetworks.map(network => {
                    const colors = getNetworkTypeColors(network.network_type)
                    const isSelected = selectedNetworkIds.includes(network.id)
                    const queueItem = discoveryQueue.find(q => q.networkId === network.id)
                    
                    return (
                      <div 
                        key={network.id}
                        onClick={() => !isDiscovering && toggleNetworkSelection(network.id)}
                        className="network-card"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '14px',
                          padding: '12px 16px',
                          borderBottom: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)'}`,
                          background: isSelected 
                            ? (isLightTheme() ? 'rgba(59, 130, 246, 0.08)' : 'rgba(99, 102, 241, 0.12)')
                            : 'transparent',
                          cursor: isDiscovering ? 'not-allowed' : 'pointer',
                          opacity: isDiscovering ? 0.7 : 1,
                          transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: isSelected 
                          ? getTheme().colors.accentPrimary
                          : 'transparent',
                        border: isSelected 
                          ? `2px solid ${getTheme().colors.accentPrimary}` 
                          : `2px solid ${isLightTheme() ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.25)'}`,
                        transition: 'all 0.15s ease',
                        flexShrink: 0
                      }}>
                        {isSelected && <span style={{ color: '#fff', fontSize: '14px', fontWeight: 700 }}>✓</span>}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '16px', color: getTheme().colors.textPrimary, minWidth: '150px' }}>
                        {network.name}
                      </span>
                      <span style={{ fontSize: '15px', color: getTheme().colors.textSecondary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {network.url}
                      </span>
                      {network.login_username && (
                        <span style={{ fontSize: '14px', color: getTheme().colors.textSecondary, display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>👤</span> {network.login_username}
                        </span>
                      )}
                      <span style={{
                        padding: '6px 14px',
                        borderRadius: '5px',
                        fontSize: '13px',
                        fontWeight: 600,
                        background: colors.bg,
                        color: colors.color,
                        border: `1px solid ${colors.border}`,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        {getNetworkTypeLabel(network.network_type)}
                      </span>
                      {queueItem && (
                        <span style={{
                          padding: '6px 14px',
                          borderRadius: '5px',
                          fontSize: '13px',
                          fontWeight: 600,
                          background: queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.1)' :
                                     queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' :
                                     queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                          color: queueItem.status === 'running' ? '#f59e0b' :
                                queueItem.status === 'completed' ? '#10b981' :
                                queueItem.status === 'failed' ? '#ef4444' :
                                queueItem.status === 'cancelled' ? '#f59e0b' : getTheme().colors.textSecondary,
                          border: `1px solid ${
                            queueItem.status === 'running' ? 'rgba(245, 158, 11, 0.3)' :
                            queueItem.status === 'completed' ? 'rgba(16, 185, 129, 0.3)' :
                            queueItem.status === 'failed' ? 'rgba(239, 68, 68, 0.3)' : getBorderColor('light')
                          }`
                        }}
                        title={queueItem.status === 'failed' && queueItem.errorMessage ? queueItem.errorMessage : undefined}
                        >
                          {queueItem.status === 'running' ? '⏳ Running' :
                           queueItem.status === 'completed' ? '✅ Done' :
                           queueItem.status === 'failed' ? '❌ Failed' :
                           queueItem.status === 'cancelled' ? '⏹ Cancelled' : '⏸ Pending'}
                        </span>
                      )}
                    </div>
                  )
                })}
                </div>

              {selectedNetworkIds.length > 0 && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px', 
                  marginTop: '12px',
                  fontSize: '13px'
                }}>
                  <span style={{
                    background: getTheme().colors.accentPrimary,
                    color: '#fff',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 600,
                    fontSize: '12px'
                  }}>{selectedNetworkIds.length}</span>
                  <span style={{ color: getTheme().colors.textSecondary }}>
                    network{selectedNetworkIds.length > 1 ? 's' : ''} selected
                  </span>
                </div>
              )}
            </div>

            {/* Action - Centered */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0 4px' }}>
              {isDiscovering ? (
                <button
                  onClick={stopDiscovery}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: '#dc2626',
                    color: '#fff',
                    border: 'none',
                    padding: '10px 28px',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  <span>⏹</span> Stop Discovery
                </button>
              ) : (
                <button
                  onClick={startDiscovery}
                  disabled={selectedNetworkIds.length === 0}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: selectedNetworkIds.length === 0 
                      ? (isLightTheme() ? '#9ca3af' : '#4b5563')
                      : (isLightTheme() ? 'linear-gradient(135deg, #3b82f6, #2563eb)' : `linear-gradient(135deg, ${getTheme().colors.accentPrimary}, ${getTheme().colors.accentSecondary})`),
                    color: '#fff',
                    border: 'none',
                    padding: '14px 36px',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: selectedNetworkIds.length === 0 ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: selectedNetworkIds.length === 0 
                      ? 'none' 
                      : (isLightTheme() ? '0 4px 12px rgba(37, 99, 235, 0.35)' : '0 4px 15px rgba(99, 102, 241, 0.4)'),
                    opacity: selectedNetworkIds.length === 0 ? 0.6 : 1
                  }}
                >
                  <span style={{ fontSize: '18px' }}>🚀</span> Start Discovery
                </button>
              )}
            </div>
          </>
          )
        )}
      </div>

      {/* Discovery Status */}
      {discoveryQueue.length > 0 && (
        <div style={{
          background: getTheme().colors.cardBg,
          backdropFilter: 'blur(20px)',
          border: `2px solid ${getTheme().colors.cardBorder}`,
          borderRadius: '28px',
          padding: '36px',
          boxShadow: `${getTheme().colors.cardGlow}, 0 20px 60px rgba(0,0,0,0.25)`,
          marginTop: '32px',
          position: 'relative'
        }}>
          {/* Close button - only show when not discovering */}
          {!isDiscovering && (
            <button
              onClick={() => setDiscoveryQueue([])}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: isLightTheme() ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)',
                border: `1px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.15)'}`,
                borderRadius: '8px',
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: '14px',
                color: getTheme().colors.textSecondary,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease'
              }}
              title="Close discovery progress"
            >
              <span>✕</span> Close
            </button>
          )}
          <h2 style={{ marginTop: 0, fontSize: '26px', color: getTheme().colors.textPrimary, fontWeight: 700, marginBottom: '28px', letterSpacing: '-0.5px', textShadow: getTheme().colors.textGlow }}>
            <span style={{ marginRight: '14px' }}>📊</span> Discovery Progress
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
            <div style={{
              background: getTheme().colors.cardBg,
              padding: '30px',
              borderRadius: '18px',
              border: `1px solid ${getTheme().colors.cardBorder}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Sites</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: getTheme().colors.textPrimary, letterSpacing: '-1px' }}>{completedNetworks} / {totalNetworks}</div>
            </div>
            <div style={{
              background: getTheme().colors.cardBg,
              padding: '30px',
              borderRadius: '18px',
              border: `1px solid ${getTheme().colors.cardBorder}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>New Forms Found</div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: getTheme().colors.statusOnline, letterSpacing: '-1px' }}>{stats.totalFormsFound}</div>
            </div>
            <div style={{
              background: getTheme().colors.cardBg,
              padding: '30px',
              borderRadius: '18px',
              border: `1px solid ${getTheme().colors.cardBorder}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>Current</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: stats.runningCount > 0 ? '#f59e0b' : getTheme().colors.textSecondary, letterSpacing: '-1px' }}>
                {stats.runningCount > 0 
                  ? discoveryQueue.find(q => q.status === 'running')?.networkName || '-'
                  : 'None'}
              </div>
            </div>
            <div style={{
              background: getTheme().colors.cardBg,
              padding: '30px',
              borderRadius: '18px',
              border: `1px solid ${getTheme().colors.cardBorder}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: getTheme().colors.textSecondary, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>Status</div>
              <div style={{ 
                fontSize: '17px',
                fontWeight: 700,
                letterSpacing: '-1px',
                color: isDiscovering ? '#f59e0b' : 
                       stats.cancelledCount > 0 ? '#f59e0b' :
                       stats.failedCount > 0 ? '#ef4444' : '#10b981'
              }}>
                {isDiscovering ? 'IN PROGRESS' : 
                 stats.cancelledCount > 0 ? 'CANCELLED' :
                 stats.failedCount > 0 ? 'WITH ERRORS' : 'COMPLETED'}
              </div>
            </div>
          </div>

          {totalNetworks > 0 && (
            <div style={{ marginTop: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '13px', color: '#94a3b8' }}>
                <span>Overall Progress</span>
                <span style={{ fontWeight: 600 }}>{Math.round((completedNetworks / totalNetworks) * 100)}%</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.1)', borderRadius: '10px', height: '10px', overflow: 'hidden' }}>
                <div style={{
                  background: 'linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7)',
                  height: '100%',
                  width: `${(completedNetworks / totalNetworks) * 100}%`,
                  transition: 'width 0.4s ease',
                  borderRadius: '10px'
                }} />
              </div>
            </div>
          )}

          {/* Network Queue Status */}
          <div style={{ marginTop: '28px' }}>
            <h4 style={{ margin: '0 0 16px', fontSize: '14px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Site Queue</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {discoveryQueue.map((item, idx) => (
                <div 
                  key={item.networkId}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    padding: '14px 18px',
                    background: item.status === 'running' ? 'rgba(245, 158, 11, 0.1)' : 
                               item.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' :
                               item.status === 'failed' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.02)',
                    borderRadius: '12px',
                    border: `1px solid ${
                      item.status === 'running' ? 'rgba(245, 158, 11, 0.2)' :
                      item.status === 'completed' ? 'rgba(16, 185, 129, 0.2)' :
                      item.status === 'failed' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.05)'
                    }`
                  }}
                >
                  <span style={{ 
                    width: '32px', 
                    height: '32px', 
                    borderRadius: '50%', 
                    background: item.status === 'running' ? 'linear-gradient(135deg, #f59e0b, #d97706)' :
                               item.status === 'completed' ? 'linear-gradient(135deg, #10b981, #059669)' :
                               item.status === 'failed' ? 'linear-gradient(135deg, #ef4444, #dc2626)' : 'rgba(255,255,255,0.1)',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '13px',
                    fontWeight: 700,
                    boxShadow: item.status === 'running' ? '0 4px 15px rgba(245, 158, 11, 0.3)' : 'none'
                  }}>
                    {idx + 1}
                  </span>
                  <span style={{ flex: 1, fontWeight: 600, fontSize: '15px', color: '#fff' }}>
                    {item.networkName}
                  </span>
                  <span style={{ 
                    fontSize: '13px',
                    fontWeight: 600,
                    color: item.status === 'running' ? '#f59e0b' :
                          item.status === 'completed' ? '#10b981' :
                          item.status === 'failed' ? '#ef4444' :
                          item.status === 'cancelled' ? '#f59e0b' : '#64748b'
                  }}
                  title={item.status === 'failed' && item.errorMessage ? item.errorMessage : undefined}
                  >
                    {item.status === 'running' ? '⏳ Running...' :
                     item.status === 'completed' ? '✅ Completed' :
                     item.status === 'failed' ? '❌ Failed' :
                     item.status === 'cancelled' ? '⏹ Cancelled' : '⏸ Waiting'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Form Pages Table */}
      <div style={{
        marginTop: '32px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', color: getTheme().colors.textPrimary, fontWeight: 600, letterSpacing: '-0.3px', textShadow: getTheme().colors.textGlow }}>
              <span style={{ marginRight: '10px' }}>📋</span>Discovered Form Pages
            </h2>
            <p style={{ margin: '8px 0 0', fontSize: '16px', color: getTheme().colors.textSecondary }}>{formPages.length} forms found in this project</p>
          </div>
          {formPages.length > 10 && (
            <span style={{ fontSize: '15px', color: getTheme().colors.textSecondary, background: getTheme().colors.cardBg, padding: '10px 16px', borderRadius: '20px', border: `1px solid ${getTheme().colors.cardBorder}` }}>
              Showing {formPages.length} forms
            </span>
          )}
        </div>
        
        {loadingFormPages ? (
          <p style={{ color: getTheme().colors.textSecondary, marginTop: '24px', fontSize: '18px' }}>Loading form pages...</p>
        ) : formPages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '100px 60px',
            background: getTheme().colors.cardBg,
            borderRadius: '20px',
            border: `1px solid ${getTheme().colors.cardBorder}`
          }}>
            <div style={{ fontSize: '64px', marginBottom: '24px' }}>📋</div>
            <p style={{ margin: 0, fontSize: '22px', color: getTheme().colors.textPrimary, fontWeight: 500 }}>No form pages discovered yet</p>
            <p style={{ margin: '14px 0 0', fontSize: '18px', color: getTheme().colors.textSecondary }}>Expand the discovery section above and start a discovery to find form pages</p>
          </div>
        ) : (
          <div style={{
            maxHeight: '700px',
            overflowY: 'auto',
            background: isLightTheme() 
              ? 'linear-gradient(135deg, rgba(242, 246, 250, 0.98) 0%, rgba(242, 246, 250, 0.95) 100%)'
              : 'rgba(255,255,255,0.03)',
            border: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.25)' : 'rgba(255,255,255,0.1)'}`,
            borderRadius: '12px',
            boxShadow: isLightTheme() 
              ? '0 4px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08)'
              : '0 4px 12px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.2)'
          }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0' }}>
              <thead>
                <tr>
                  <th 
                    style={{
                      textAlign: 'left',
                      padding: '18px 24px',
                      borderBottom: `2px solid ${isLightTheme() ? 'rgba(0,0,0,0.1)' : getTheme().colors.cardBorder}`,
                      fontWeight: 600,
                      color: getTheme().colors.textSecondary,
                      background: getBgColor('header'),
                      position: 'sticky',
                      top: 0,
                      zIndex: 1,
                      fontSize: '15px',
                      textTransform: 'uppercase',
                      letterSpacing: '1px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      textShadow: getTheme().colors.textGlow
                    }}
                    onClick={() => {
                      if (sortField === 'name') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('name')
                        setSortDirection('asc')
                      }
                    }}
                  >
                    Form Name {sortField === 'name' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th style={{
                    textAlign: 'left',
                    padding: '18px 24px',
                    borderBottom: `2px solid ${getTheme().colors.cardBorder}`,
                    fontWeight: 600,
                    color: getTheme().colors.textSecondary,
                    background: getBgColor('header'),
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '15px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                  }}>Paths</th>
                  <th style={{
                    textAlign: 'left',
                    padding: '18px 24px',
                    borderBottom: `2px solid ${getTheme().colors.cardBorder}`,
                    fontWeight: 600,
                    color: getTheme().colors.textSecondary,
                    background: getBgColor('header'),
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '15px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                  }}>Test Site URL</th>
                  <th 
                    style={{
                      textAlign: 'left',
                      padding: '18px 24px',
                      borderBottom: `2px solid ${getTheme().colors.cardBorder}`,
                      fontWeight: 600,
                      color: getTheme().colors.textSecondary,
                      background: getBgColor('header'),
                      position: 'sticky',
                      top: 0,
                      zIndex: 1,
                      fontSize: '15px',
                      textTransform: 'uppercase',
                      letterSpacing: '1px',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                    onClick={() => {
                      if (sortField === 'date') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('date')
                        setSortDirection('desc')
                      }
                    }}
                  >
                    Discovered {sortField === 'date' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th style={{
                    textAlign: 'center',
                    padding: '18px 24px',
                    borderBottom: `2px solid ${getTheme().colors.cardBorder}`,
                    fontWeight: 600,
                    color: getTheme().colors.textSecondary,
                    background: getBgColor('header'),
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    fontSize: '15px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    width: '160px'
                  }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {/* Group form pages by network_id, then show login/logout at end of each group */}
                {(() => {
                  // Get unique network IDs from form pages
                  const networkIdsFromForms = [...new Set(formPages.map(fp => fp.network_id))]
                  // Get network IDs from login/logout data
                  const networkIdsFromLoginLogout = Object.keys(loginLogoutData).map(id => parseInt(id))
                  // Combine and deduplicate
                  const allNetworkIds = [...new Set([...networkIdsFromForms, ...networkIdsFromLoginLogout])]
                  
                  // Sort form pages
                  const sortedFormPages = [...formPages].sort((a, b) => {
                    if (sortField === 'name') {
                      const nameA = (a.form_name || '').toLowerCase()
                      const nameB = (b.form_name || '').toLowerCase()
                      return sortDirection === 'asc' 
                        ? nameA.localeCompare(nameB)
                        : nameB.localeCompare(nameA)
                    } else {
                      const dateA = new Date(a.created_at || 0).getTime()
                      const dateB = new Date(b.created_at || 0).getTime()
                      return sortDirection === 'asc' 
                        ? dateA - dateB
                        : dateB - dateA
                    }
                  })
                  
                  let rowIndex = 0
                  
                  return allNetworkIds.map(networkId => {
                    const networkForms = sortedFormPages.filter(fp => fp.network_id === networkId)
                    const loginLogout = loginLogoutData[networkId]
                    
                    return (
                      <>
                        {/* Form pages for this network */}
                        {networkForms.map((form) => {
                          const currentIndex = rowIndex++
                          return (
                            <tr 
                              key={form.id} 
                              className="table-row"
                              style={{
                                transition: 'all 0.2s ease',
                                cursor: 'pointer',
                                background: isLightTheme() 
                                  ? (currentIndex % 2 === 0 ? 'rgba(219, 234, 254, 0.6)' : 'rgba(191, 219, 254, 0.5)')
                                  : (currentIndex % 2 === 0 ? 'rgba(59, 130, 246, 0.08)' : 'rgba(59, 130, 246, 0.12)')
                              }}
                              onDoubleClick={() => openEditPanel(form)}
                            >
                              <td style={{
                                padding: '20px 24px',
                                borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`,
                                verticalAlign: 'middle',
                                fontSize: '16px',
                                color: getTheme().colors.textPrimary
                              }}>
                                <strong style={{ fontSize: '17px', color: getTheme().colors.textPrimary }}>{form.form_name}</strong>
                                {form.parent_form_name && (
                                  <div style={{ fontSize: '15px', color: getTheme().colors.textSecondary, marginTop: '4px' }}>
                                    Parent: {form.parent_form_name}
                                  </div>
                                )}
                              </td>
                              <td style={{
                                padding: '20px 24px',
                                borderBottom: `1px solid ${getTheme().colors.cardBorder}`,
                                verticalAlign: 'middle',
                                fontSize: '16px',
                                color: getTheme().colors.textPrimary
                              }}>
                                <span style={{
                                  background: isLightTheme() 
                                    ? 'rgba(16, 185, 129, 0.15)'
                                    : 'rgba(16, 185, 129, 0.2)',
                                  color: isLightTheme() ? '#059669' : '#6ee7b7',
                                  padding: '8px 16px',
                                  borderRadius: '20px',
                                  fontSize: '15px',
                                  fontWeight: 600
                                }}>
                                  {completedPaths.filter(p => p.id === form.id).length > 0 
                                    ? `${completedPaths.filter(p => p.id === form.id).length} paths`
                                    : (mappingFormIds.has(form.id) ? 'Mapping...' : 'Not mapped')}
                                </span>
                              </td>
                              <td style={{ 
                                padding: '20px 24px', 
                                borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, 
                                color: isLightTheme() ? '#0369a1' : '#7dd3fc',
                                fontSize: '14px',
                                maxWidth: '250px'
                              }}>
                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={form.url}>
                                  {form.url}
                                </div>
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, color: getTheme().colors.textSecondary }}>
                                {form.created_at ? (
                                  <>
                                    {new Date(form.created_at).toLocaleDateString()}
                                    <div style={{ fontSize: '13px', opacity: 0.7 }}>
                                      {new Date(form.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                  </>
                                ) : '-'}
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, textAlign: 'center' }}>
                                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                                  <button 
                                    onClick={() => openEditPanel(form)}
                                    className="action-btn"
                                    style={{
                                      background: isLightTheme() ? 'rgba(59, 130, 246, 0.1)' : 'rgba(99, 102, 241, 0.15)',
                                      border: `2px solid ${isLightTheme() ? 'rgba(59, 130, 246, 0.2)' : 'rgba(99, 102, 241, 0.3)'}`,
                                      borderRadius: '12px',
                                      padding: '16px 18px',
                                      cursor: 'pointer',
                                      fontSize: '20px',
                                      transition: 'all 0.2s ease'
                                    }}
                                    title="Edit form page"
                                  >
                                    ✏️
                                  </button>
                                  <button 
                                    onClick={() => confirmDeleteFormPage(form)}
                                    className="action-btn"
                                    style={{
                                      background: isLightTheme() ? 'rgba(239, 68, 68, 0.08)' : 'rgba(239, 68, 68, 0.15)',
                                      border: `2px solid ${isLightTheme() ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.3)'}`,
                                      borderRadius: '12px',
                                      padding: '16px 18px',
                                      cursor: 'pointer',
                                      fontSize: '20px',
                                      transition: 'all 0.2s ease'
                                    }}
                                    title="Delete form page"
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                        
                        {/* Login/Logout rows at end of each network group */}
                        {loginLogout && (
                          <>
                            {/* Login Row */}
                            <tr 
                              key={`login-${networkId}`}
                              className="table-row"
                              style={{
                                transition: 'all 0.2s ease',
                                cursor: 'pointer',
                                background: isLightTheme() 
                                  ? 'rgba(16, 185, 129, 0.08)' 
                                  : 'rgba(16, 185, 129, 0.1)',
                                borderLeft: '4px solid #10b981'
                              }}
                              onDoubleClick={() => openLoginLogoutEditPanel(networkId, 'login')}
                            >
                              <td style={{
                                padding: '20px 24px',
                                borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`,
                                verticalAlign: 'middle',
                                fontSize: '16px',
                                color: getTheme().colors.textPrimary
                              }}>
                                <strong style={{ fontSize: '17px', color: '#10b981' }}>🔐 Login</strong>
                                <div style={{ fontSize: '14px', color: getTheme().colors.textSecondary, marginTop: '4px' }}>
                                  {loginLogout.network_name}
                                </div>
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}` }}>
                                <span style={{
                                  background: 'rgba(107, 114, 128, 0.2)',
                                  color: '#9ca3af',
                                  padding: '8px 16px',
                                  borderRadius: '20px',
                                  fontSize: '15px',
                                  fontWeight: 600
                                }}>
                                  {loginLogout.login_stages.length} steps
                                </span>
                              </td>
                              <td style={{ 
                                padding: '20px 24px', 
                                borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, 
                                color: isLightTheme() ? '#0369a1' : '#7dd3fc',
                                fontSize: '14px',
                                maxWidth: '250px'
                              }}>
                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={loginLogout.url}>
                                  {loginLogout.url}
                                </div>
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, color: getTheme().colors.textSecondary }}>
                                {loginLogout.updated_at ? new Date(loginLogout.updated_at).toLocaleDateString() : '-'}
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `1px solid ${isLightTheme() ? 'rgba(100,116,139,0.15)' : 'rgba(255,255,255,0.06)'}`, textAlign: 'center' }}>
                                <button 
                                  onClick={() => openLoginLogoutEditPanel(networkId, 'login')}
                                  className="action-btn"
                                  style={{
                                    background: 'rgba(16, 185, 129, 0.15)',
                                    border: '2px solid rgba(16, 185, 129, 0.3)',
                                    borderRadius: '12px',
                                    padding: '16px 18px',
                                    cursor: 'pointer',
                                    fontSize: '20px',
                                    transition: 'all 0.2s ease'
                                  }}
                                  title="Edit login steps"
                                >
                                  ✏️
                                </button>
                              </td>
                            </tr>
                            
                            {/* Logout Row */}
                            <tr 
                              key={`logout-${networkId}`}
                              className="table-row"
                              style={{
                                transition: 'all 0.2s ease',
                                cursor: 'pointer',
                                background: isLightTheme() 
                                  ? 'rgba(16, 185, 129, 0.08)' 
                                  : 'rgba(16, 185, 129, 0.1)',
                                borderLeft: '4px solid #10b981'
                              }}
                              onDoubleClick={() => openLoginLogoutEditPanel(networkId, 'logout')}
                            >
                              <td style={{
                                padding: '20px 24px',
                                borderBottom: `2px solid ${getTheme().colors.cardBorder}`,
                                verticalAlign: 'middle',
                                fontSize: '16px',
                                color: getTheme().colors.textPrimary
                              }}>
                                <strong style={{ fontSize: '17px', color: '#10b981' }}>🚪 Logout</strong>
                                <div style={{ fontSize: '14px', color: getTheme().colors.textSecondary, marginTop: '4px' }}>
                                  {loginLogout.network_name}
                                </div>
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `2px solid ${getTheme().colors.cardBorder}` }}>
                                <span style={{
                                  background: 'rgba(107, 114, 128, 0.2)',
                                  color: '#9ca3af',
                                  padding: '8px 16px',
                                  borderRadius: '20px',
                                  fontSize: '15px',
                                  fontWeight: 600
                                }}>
                                  {loginLogout.logout_stages.length} steps
                                </span>
                              </td>
                              <td style={{ 
                                padding: '20px 24px', 
                                borderBottom: `2px solid ${getTheme().colors.cardBorder}`, 
                                color: isLightTheme() ? '#0369a1' : '#7dd3fc',
                                fontSize: '14px',
                                maxWidth: '250px'
                              }}>
                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={loginLogout.url}>
                                  {loginLogout.url}
                                </div>
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `2px solid ${getTheme().colors.cardBorder}`, color: getTheme().colors.textSecondary }}>
                                {loginLogout.updated_at ? new Date(loginLogout.updated_at).toLocaleDateString() : '-'}
                              </td>
                              <td style={{ padding: '20px 24px', borderBottom: `2px solid ${getTheme().colors.cardBorder}`, textAlign: 'center' }}>
                                <button 
                                  onClick={() => openLoginLogoutEditPanel(networkId, 'logout')}
                                  className="action-btn"
                                  style={{
                                    background: 'rgba(16, 185, 129, 0.15)',
                                    border: '2px solid rgba(16, 185, 129, 0.3)',
                                    borderRadius: '12px',
                                    padding: '16px 18px',
                                    cursor: 'pointer',
                                    fontSize: '20px',
                                    transition: 'all 0.2s ease'
                                  }}
                                  title="Edit logout steps"
                                >
                                  ✏️
                                </button>
                              </td>
                            </tr>
                          </>
                        )}
                      </>
                    )
                  })
                })()}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Form Page Modal */}
      {showDeleteModal && formPageToDelete && (
        <div style={modalOverlayStyle}>
          <div style={{
            background: getTheme().colors.cardBg,
            backdropFilter: 'blur(20px)',
            borderRadius: '24px',
            width: '500px',
            padding: '32px',
            border: `2px solid rgba(239, 68, 68, 0.3)`,
            boxShadow: '0 0 50px rgba(239, 68, 68, 0.2), 0 30px 80px rgba(0,0,0,0.5)'
          }}>
            <h2 style={{ marginTop: 0, color: '#ef4444', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '22px', fontWeight: 700 }}>
              <span style={{ fontSize: '28px' }}>⚠️</span>
              Delete Form Page?
            </h2>
            
            <p style={{ fontSize: '16px', margin: '20px 0', color: getTheme().colors.textPrimary }}>
              Are you sure you want to delete <strong style={{ color: getTheme().colors.textPrimary }}>"{formPageToDelete.form_name}"</strong>?
            </p>
            
            <div style={deleteWarningBoxStyle}>
              <div style={{ display: 'flex', gap: '14px' }}>
                <span style={{ fontSize: '24px' }}>🚨</span>
                <div>
                  <strong style={{ fontSize: '15px', color: '#ef4444' }}>Warning - This will permanently delete:</strong>
                  <ul style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8', paddingLeft: '20px' }}>
                    <li style={{ marginBottom: '4px' }}>All discovered <strong style={{ color: '#fff' }}>paths</strong> for this form</li>
                    <li style={{ marginBottom: '4px' }}>All <strong style={{ color: '#fff' }}>navigation steps</strong> leading to this form</li>
                    <li>The form page entry itself</li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '28px' }}>
              <button onClick={() => { setShowDeleteModal(false); setFormPageToDelete(null) }} style={secondaryButtonStyle}>
                Cancel
              </button>
              <button 
                onClick={deleteFormPage} 
                style={dangerButtonStyle}
                disabled={deletingFormPage}
              >
                {deletingFormPage ? 'Deleting...' : 'Delete Form Page'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== STYLES ====================

const welcomeCardStyle: React.CSSProperties = {
  background: 'rgba(75, 85, 99, 0.5)',
  backdropFilter: 'blur(20px)',
  borderRadius: '28px',
  padding: '80px',
  textAlign: 'center',
  border: '2px solid rgba(156, 163, 175, 0.35)',
  boxShadow: '0 0 50px rgba(156, 163, 175, 0.15), 0 20px 60px rgba(0,0,0,0.3)'
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(75, 85, 99, 0.5)',
  backdropFilter: 'blur(20px)',
  border: '2px solid rgba(156, 163, 175, 0.3)',
  borderRadius: '28px',
  padding: '36px',
  boxShadow: '0 0 40px rgba(156, 163, 175, 0.12), 0 20px 60px rgba(0,0,0,0.25)'
}

const discoveryHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '24px',
  padding: '26px 32px',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.15))',
  border: '2px solid rgba(99, 102, 241, 0.4)',
  borderRadius: '20px',
  marginBottom: '0',
  boxShadow: '0 0 35px rgba(99, 102, 241, 0.25), inset 0 0 30px rgba(99, 102, 241, 0.05)'
}

const discoveryIconStyle: React.CSSProperties = {
  fontSize: '36px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  borderRadius: '18px',
  padding: '18px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: '0 0 30px rgba(99, 102, 241, 0.5), 0 4px 20px rgba(99, 102, 241, 0.4)'
}

const discoveryTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '32px',
  fontWeight: 700,
  color: '#f3f4f6',
  letterSpacing: '-0.5px',
  textShadow: '0 0 20px rgba(243, 244, 246, 0.3)'
}

const discoverySubtitleStyle: React.CSSProperties = {
  margin: '10px 0 0',
  fontSize: '18px',
  color: '#94a3b8',
  lineHeight: 1.5
}

const discoveringBadgeStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  background: 'rgba(16, 185, 129, 0.2)',
  border: '2px solid rgba(16, 185, 129, 0.5)',
  padding: '16px 28px',
  borderRadius: '30px',
  fontSize: '17px',
  fontWeight: 600,
  color: '#10b981',
  boxShadow: '0 0 25px rgba(16, 185, 129, 0.35)'
}

const pulsingDotStyle: React.CSSProperties = {
  width: '14px',
  height: '14px',
  borderRadius: '50%',
  background: '#10b981',
  boxShadow: '0 0 20px rgba(16, 185, 129, 0.8), 0 0 40px rgba(16, 185, 129, 0.4)',
  animation: 'pulse 1.5s infinite'
}

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '100px 60px',
  background: 'rgba(255,255,255,0.02)',
  borderRadius: '24px',
  border: '2px dashed rgba(255,255,255,0.1)'
}

const sectionStyle: React.CSSProperties = {
  marginBottom: '12px'
}

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '28px'
}

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '26px',
  fontWeight: 700,
  color: '#fff',
  letterSpacing: '-0.5px'
}

const sectionSubtitleStyle: React.CSSProperties = {
  margin: '10px 0 0',
  fontSize: '18px',
  color: '#94a3b8'
}

const selectAllBtnStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  color: '#e2e8f0',
  border: '1px solid rgba(255,255,255,0.12)',
  padding: '16px 28px',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const networkCheckboxStyle: React.CSSProperties = {
  width: '28px',
  height: '28px',
  borderRadius: '10px',
  border: '2px solid rgba(255,255,255,0.2)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.2s ease',
  flexShrink: 0
}

const selectedCountStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  marginTop: '24px',
  fontSize: '17px'
}

const selectedCountBadgeStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  width: '36px',
  height: '36px',
  borderRadius: '50%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: '16px',
  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
}

const startDiscoveryBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: '2px solid rgba(139, 92, 246, 0.5)',
  padding: '18px 48px',
  borderRadius: '16px',
  fontSize: '18px',
  fontWeight: 700,
  cursor: 'pointer',
  boxShadow: '0 0 35px rgba(99, 102, 241, 0.5), 0 10px 40px rgba(99, 102, 241, 0.4)',
  transition: 'all 0.3s ease',
  textShadow: '0 0 10px rgba(255,255,255,0.5)'
}

const stopDiscoveryBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  color: '#fff',
  border: '2px solid rgba(239, 68, 68, 0.5)',
  padding: '18px 48px',
  borderRadius: '16px',
  fontSize: '18px',
  fontWeight: 700,
  cursor: 'pointer',
  boxShadow: '0 0 35px rgba(239, 68, 68, 0.5), 0 10px 40px rgba(239, 68, 68, 0.4)',
  transition: 'all 0.3s ease',
  textShadow: '0 0 10px rgba(255,255,255,0.5)'
}

const tableContainerStyle: React.CSSProperties = {
  maxHeight: '700px',
  overflowY: 'auto',
  background: 'rgba(75, 85, 99, 0.3)',
  borderRadius: '20px',
  border: '2px solid rgba(156, 163, 175, 0.25)',
  boxShadow: '0 0 30px rgba(156, 163, 175, 0.1), inset 0 0 20px rgba(0,0,0,0.1)'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '24px 32px',
  borderBottom: '2px solid rgba(156, 163, 175, 0.2)',
  fontWeight: 600,
  color: '#d1d5db',
  background: 'rgba(75, 85, 99, 0.5)',
  position: 'sticky',
  top: 0,
  zIndex: 1,
  fontSize: '14px',
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
  textShadow: '0 0 10px rgba(209, 213, 219, 0.2)'
}

const tableRowStyle: React.CSSProperties = {
  transition: 'all 0.2s ease',
  cursor: 'pointer',
  background: 'transparent'
}

const tdStyle: React.CSSProperties = {
  padding: '28px 32px',
  borderBottom: '1px solid rgba(156, 163, 175, 0.1)',
  verticalAlign: 'middle',
  fontSize: '18px',
  color: '#f3f4f6'
}

const pathStepsBadgeStyle: React.CSSProperties = {
  background: 'rgba(99, 102, 241, 0.2)',
  color: '#a5b4fc',
  padding: '12px 24px',
  borderRadius: '24px',
  fontSize: '16px',
  fontWeight: 600,
  border: '2px solid rgba(99, 102, 241, 0.5)',
  boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)'
}

const actionButtonStyle: React.CSSProperties = {
  background: 'rgba(156, 163, 175, 0.15)',
  border: '2px solid rgba(156, 163, 175, 0.3)',
  borderRadius: '12px',
  padding: '16px 18px',
  cursor: 'pointer',
  fontSize: '20px',
  transition: 'all 0.2s ease',
  boxShadow: '0 0 15px rgba(156, 163, 175, 0.15)'
}

const statBoxStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  padding: '30px',
  borderRadius: '20px',
  textAlign: 'center',
  border: '1px solid rgba(255,255,255,0.08)'
}

const statLabelStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#64748b',
  marginBottom: '12px',
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
  fontWeight: 600
}

const statValueStyle: React.CSSProperties = {
  fontSize: '36px',
  fontWeight: 700,
  color: '#fff'
}

const errorBoxStyle: React.CSSProperties = {
  background: 'rgba(239, 68, 68, 0.15)',
  color: '#dc2626',
  padding: '20px 28px',
  borderRadius: '18px',
  marginBottom: '28px',
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  fontSize: '17px',
  fontWeight: 600,
  border: '2px solid rgba(239, 68, 68, 0.5)'
}

const successBoxStyle: React.CSSProperties = {
  background: 'rgba(16, 185, 129, 0.15)',
  color: '#059669',
  padding: '18px 24px',
  borderRadius: '16px',
  marginBottom: '28px',
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  fontSize: '16px',
  fontWeight: 600,
  border: '2px solid rgba(16, 185, 129, 0.5)'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '6px 12px',
  borderRadius: '8px',
  marginLeft: 'auto',
  color: 'inherit',
  transition: 'all 0.2s ease'
}

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: 'white',
  padding: '16px 32px',
  border: 'none',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.3)',
  transition: 'all 0.2s ease'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  color: '#e2e8f0',
  padding: '16px 32px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
}

const dangerButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  color: 'white',
  padding: '16px 32px',
  border: 'none',
  borderRadius: '14px',
  fontSize: '17px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
  transition: 'all 0.2s ease'
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

const largeModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(75, 85, 99, 0.98), rgba(55, 65, 81, 0.98))',
  borderRadius: '28px',
  width: '100%',
  maxWidth: '1200px',
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
}

const modalHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '28px 36px',
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))'
}

const modalCloseButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: 'none',
  fontSize: '28px',
  cursor: 'pointer',
  padding: '12px 18px',
  borderRadius: '12px',
  color: '#94a3b8',
  lineHeight: 1,
  transition: 'all 0.2s ease'
}

const prominentNoteStyle: React.CSSProperties = {
  display: 'flex',
  gap: '20px',
  background: 'rgba(0, 187, 249, 0.1)',
  border: '1px solid rgba(0, 187, 249, 0.2)',
  color: '#94a3b8',
  padding: '24px 28px',
  margin: '0',
  alignItems: 'flex-start'
}

const modalBodyStyle: React.CSSProperties = {
  display: 'flex',
  flex: 1,
  overflow: 'hidden'
}

const modalLeftColumnStyle: React.CSSProperties = {
  width: '360px',
  padding: '28px',
  borderRight: '1px solid rgba(255,255,255,0.05)',
  overflowY: 'auto',
  background: 'rgba(255,255,255,0.02)'
}

const modalRightColumnStyle: React.CSSProperties = {
  flex: 1,
  padding: '28px',
  overflowY: 'auto'
}

const modalLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '12px',
  fontWeight: 600,
  color: '#e2e8f0',
  fontSize: '16px'
}

const modalInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '16px 20px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '12px',
  fontSize: '17px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.05)',
  color: '#fff',
  outline: 'none'
}

const infoSectionStyle: React.CSSProperties = {
  padding: '22px',
  background: 'rgba(255,255,255,0.03)',
  borderRadius: '16px',
  marginBottom: '20px',
  border: '1px solid rgba(255,255,255,0.08)'
}

const infoRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  marginBottom: '14px',
  fontSize: '16px'
}

const infoLabelStyle: React.CSSProperties = {
  color: '#64748b',
  minWidth: '70px',
  fontSize: '15px'
}

const childBadgeStyle: React.CSSProperties = {
  display: 'inline-block',
  background: 'rgba(255,255,255,0.05)',
  color: '#94a3b8',
  padding: '8px 14px',
  borderRadius: '10px',
  fontSize: '15px',
  border: '1px solid rgba(255,255,255,0.1)'
}

const addStepButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  padding: '12px 22px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)'
}

const pathStepsScrollContainerStyle: React.CSSProperties = {
  maxHeight: 'calc(90vh - 400px)',
  overflowY: 'auto',
  paddingRight: '12px'
}

const pathStepCardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '16px',
  marginBottom: '16px',
  overflow: 'hidden'
}

const stepHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  padding: '16px 20px',
  background: 'rgba(255,255,255,0.03)',
  borderBottom: '1px solid rgba(255,255,255,0.05)'
}

const stepNumberBadgeStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '16px',
  fontWeight: 700,
  flexShrink: 0,
  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
}

const stepActionButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  padding: '10px 12px',
  cursor: 'pointer',
  fontSize: '16px',
  borderRadius: '10px',
  transition: 'all 0.2s ease'
}

const stepFieldsStyle: React.CSSProperties = {
  padding: '20px'
}

const stepFieldRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '18px',
  marginBottom: '16px'
}

const stepFieldLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '10px',
  fontWeight: 500,
  color: '#94a3b8',
  fontSize: '15px'
}

const stepFieldInputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 16px',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '12px',
  fontSize: '16px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.05)',
  color: '#fff',
  outline: 'none'
}

const modalFooterStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '14px',
  padding: '24px 36px',
  borderTop: '1px solid rgba(255,255,255,0.05)',
  background: 'rgba(255,255,255,0.02)'
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

const deleteModalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(75, 85, 99, 0.98), rgba(55, 65, 81, 0.98))',
  borderRadius: '28px',
  padding: '44px',
  width: '100%',
  maxWidth: '560px',
  boxShadow: '0 30px 80px rgba(0,0,0,0.4)',
  border: '1px solid rgba(255,255,255,0.12)'
}

const deleteWarningBoxStyle: React.CSSProperties = {
  background: 'rgba(0, 187, 249, 0.1)',
  border: '1px solid rgba(0, 187, 249, 0.2)',
  padding: '24px',
  borderRadius: '16px',
  marginTop: '24px'
}
