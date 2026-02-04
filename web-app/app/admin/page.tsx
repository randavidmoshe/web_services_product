'use client'
import { useState, useEffect } from 'react'

interface PendingCompany {
  company_id: number
  company_name: string
  billing_email: string
  admin_name: string | null
  admin_email: string | null
  account_category: string | null
  created_at: string | null
  daily_ai_budget: number
  trial_days_total: number
}

interface Company {
  company_id: number
  company_name: string
  billing_email: string
  admin_name: string | null
  admin_email: string | null
  account_category: string | null
  access_model: string | null
  access_status: string | null
  onboarding_completed: boolean
  daily_ai_budget: number | null
  trial_days_total: number | null
  trial_start_date: string | null
  ai_used_today: number | null
  created_at: string | null
}

interface AuditLog {
  id: number
  admin_id: number
  action: string
  target_company_id: number | null
  details: any
  ip_address: string | null
  created_at: string | null
}

export default function SuperAdminDashboard() {
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'pending' | 'companies' | 'audit'>('pending')

  // Data
  const [pendingCompanies, setPendingCompanies] = useState<PendingCompany[]>([])
  const [allCompanies, setAllCompanies] = useState<Company[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])

  // Actions
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Edit limits modal
  const [editingCompany, setEditingCompany] = useState<Company | null>(null)
  const [editBudget, setEditBudget] = useState('')
  const [editDays, setEditDays] = useState('')

  useEffect(() => {
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
        if (data.type !== 'super_admin') {
          window.location.href = '/login'
          return
        }
        loadData()
      })
      .catch(() => {
        window.location.href = '/login'
      })
  }, [])

  const loadData = async () => {
    setLoading(true)
    await Promise.all([
      loadPendingCompanies(),
      loadAllCompanies(),
      loadAuditLogs()
    ])
    setLoading(false)
  }

  const loadPendingCompanies = async () => {
    try {
      const response = await fetch('/api/super-admin/pending-access', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setPendingCompanies(data.pending || [])
      }
    } catch (err) {
      console.error('Failed to load pending companies:', err)
    }
  }

  const loadAllCompanies = async () => {
    try {
      const response = await fetch('/api/super-admin/all-companies', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setAllCompanies(data.companies || [])
      }
    } catch (err) {
      console.error('Failed to load companies:', err)
    }
  }

  const loadAuditLogs = async () => {
    try {
      const response = await fetch('/api/super-admin/audit-logs?limit=50', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setAuditLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Failed to load audit logs:', err)
    }
  }

  const approveAccess = async (companyId: number) => {
    setActionLoading(companyId)
    setMessage(null)

    try {
      const response = await fetch('/api/super-admin/approve-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ company_id: companyId })
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Access approved!' })
        loadData()
      } else {
        const err = await response.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to approve' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Connection error' })
    }
    setActionLoading(null)
  }

  const rejectAccess = async (companyId: number) => {
    setActionLoading(companyId)
    setMessage(null)

    try {
      const response = await fetch('/api/super-admin/reject-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ company_id: companyId })
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Access rejected' })
        loadData()
      } else {
        const err = await response.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to reject' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Connection error' })
    }
    setActionLoading(null)
  }

  const toggleCompanyStatus = async (company: Company) => {
    setActionLoading(company.company_id)

    const endpoint = company.access_status === 'active'
      ? '/api/super-admin/disable-company'
      : '/api/super-admin/enable-company'

    try {
      const response = await fetch(`${endpoint}?company_id=${company.company_id}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        setMessage({ type: 'success', text: company.access_status === 'active' ? 'Company disabled' : 'Company enabled' })
        loadData()
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update status' })
    }
    setActionLoading(null)
  }

  const openEditLimits = (company: Company) => {
    setEditingCompany(company)
    setEditBudget(String(company.daily_ai_budget || 10))
    setEditDays(String(company.trial_days_total || 10))
  }

  const saveLimits = async () => {
    if (!editingCompany) return
    setActionLoading(editingCompany.company_id)

    try {
      const response = await fetch('/api/super-admin/company-limits', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          company_id: editingCompany.company_id,
          daily_ai_budget: parseFloat(editBudget),
          trial_days_total: parseInt(editDays)
        })
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Limits updated' })
        setEditingCompany(null)
        loadData()
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update limits' })
    }
    setActionLoading(null)
  }

  const handleLogout = () => {
    localStorage.clear()
    window.location.href = '/login'
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
  }

  const getStatusBadge = (status: string | null) => {
    const colors: Record<string, { bg: string, text: string }> = {
      active: { bg: '#d1fae5', text: '#059669' },
      pending: { bg: '#fef3c7', text: '#d97706' },
      rejected: { bg: '#fee2e2', text: '#dc2626' }
    }
    const c = colors[status || 'pending'] || colors.pending
    return (
      <span style={{ background: c.bg, color: c.text, padding: '4px 12px', borderRadius: '20px', fontSize: '13px', fontWeight: 600 }}>
        {status || 'pending'}
      </span>
    )
  }

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: '100px' }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
          <p style={{ color: '#64748b', fontSize: '18px' }}>Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700, color: '#1e293b' }}>
            🛡️ Super Admin Dashboard
          </h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '14px' }}>
            Manage companies and access requests
          </p>
        </div>
        <button onClick={handleLogout} style={logoutButtonStyle}>
          Logout
        </button>
      </div>

      {/* Message */}
      {message && (
        <div style={{
          padding: '14px 20px',
          borderRadius: '10px',
          marginBottom: '20px',
          background: message.type === 'success' ? '#d1fae5' : '#fee2e2',
          color: message.type === 'success' ? '#059669' : '#dc2626'
        }}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('pending')}
          style={{ ...tabStyle, ...(activeTab === 'pending' ? activeTabStyle : {}) }}
        >
          Pending Requests ({pendingCompanies.length})
        </button>
        <button
          onClick={() => setActiveTab('companies')}
          style={{ ...tabStyle, ...(activeTab === 'companies' ? activeTabStyle : {}) }}
        >
          All Companies ({allCompanies.length})
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          style={{ ...tabStyle, ...(activeTab === 'audit' ? activeTabStyle : {}) }}
        >
          Audit Log
        </button>
      </div>

      {/* Content */}
      <div style={contentStyle}>
        {/* Pending Requests Tab */}
        {activeTab === 'pending' && (
          pendingCompanies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>✅</div>
              <p>No pending requests</p>
            </div>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Company</th>
                  <th style={thStyle}>Admin</th>
                  <th style={thStyle}>Category</th>
                  <th style={thStyle}>Budget/Day</th>
                  <th style={thStyle}>Trial Days</th>
                  <th style={thStyle}>Created</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingCompanies.map(company => (
                  <tr key={company.company_id}>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600 }}>{company.company_name}</div>
                      <div style={{ fontSize: '13px', color: '#64748b' }}>{company.billing_email}</div>
                    </td>
                    <td style={tdStyle}>
                      <div>{company.admin_name || '-'}</div>
                      <div style={{ fontSize: '13px', color: '#64748b' }}>{company.admin_email}</div>
                    </td>
                    <td style={tdStyle}>{company.account_category || '-'}</td>
                    <td style={tdStyle}>${company.daily_ai_budget}</td>
                    <td style={tdStyle}>{company.trial_days_total} days</td>
                    <td style={tdStyle}>{formatDate(company.created_at)}</td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => approveAccess(company.company_id)}
                          disabled={actionLoading === company.company_id}
                          style={approveButtonStyle}
                        >
                          ✓ Approve
                        </button>
                        <button
                          onClick={() => rejectAccess(company.company_id)}
                          disabled={actionLoading === company.company_id}
                          style={rejectButtonStyle}
                        >
                          ✗ Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {/* All Companies Tab */}
        {activeTab === 'companies' && (
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Company</th>
                <th style={thStyle}>Admin</th>
                <th style={thStyle}>Access</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Budget</th>
                <th style={thStyle}>Used Today</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {allCompanies.map(company => (
                <tr key={company.company_id}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600 }}>{company.company_name}</div>
                    <div style={{ fontSize: '13px', color: '#64748b' }}>{company.billing_email}</div>
                  </td>
                  <td style={tdStyle}>
                    <div>{company.admin_name || '-'}</div>
                    <div style={{ fontSize: '13px', color: '#64748b' }}>{company.admin_email}</div>
                  </td>
                  <td style={tdStyle}>
                    <span style={{
                      background: company.access_model === 'byok' ? '#dbeafe' : '#f3e8ff',
                      color: company.access_model === 'byok' ? '#1d4ed8' : '#7c3aed',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '13px',
                      fontWeight: 500
                    }}>
                      {company.access_model || 'none'}
                    </span>
                  </td>
                  <td style={tdStyle}>{getStatusBadge(company.access_status)}</td>
                  <td style={tdStyle}>
                    {company.access_model === 'byok' ? '∞' : `$${company.daily_ai_budget || 10}/day`}
                  </td>
                  <td style={tdStyle}>
                    {company.access_model === 'byok' ? '-' : `$${(company.ai_used_today || 0).toFixed(2)}`}
                  </td>
                  <td style={tdStyle}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {company.access_model !== 'byok' && (
                        <button
                          onClick={() => openEditLimits(company)}
                          style={editButtonStyle}
                        >
                          ✏️ Limits
                        </button>
                      )}
                      <button
                        onClick={() => toggleCompanyStatus(company)}
                        disabled={actionLoading === company.company_id}
                        style={company.access_status === 'active' ? disableButtonStyle : enableButtonStyle}
                      >
                        {company.access_status === 'active' ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Audit Log Tab */}
        {activeTab === 'audit' && (
          auditLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
              <p>No audit logs yet</p>
            </div>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Time</th>
                  <th style={thStyle}>Action</th>
                  <th style={thStyle}>Target Company</th>
                  <th style={thStyle}>Details</th>
                  <th style={thStyle}>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map(log => (
                  <tr key={log.id}>
                    <td style={tdStyle}>{formatDate(log.created_at)}</td>
                    <td style={tdStyle}>
                      <span style={{
                        background: '#f1f5f9',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: 500
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {log.target_company_id
  ? allCompanies.find(c => c.company_id === log.target_company_id)?.company_name || `Company #${log.target_company_id}`
  : '-'}
                    </td>
                    <td style={tdStyle}>
                      <code style={{ fontSize: '12px', color: '#64748b' }}>
                        {log.details ? JSON.stringify(log.details) : '-'}
                      </code>
                    </td>
                    <td style={tdStyle}>{log.ip_address || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>

      {/* Edit Limits Modal */}
      {editingCompany && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <h3 style={{ margin: '0 0 24px', fontSize: '20px', fontWeight: 600 }}>
              Edit Limits: {editingCompany.company_name}
            </h3>

            <div style={{ marginBottom: '20px' }}>
              <label style={labelStyle}>Daily AI Budget ($)</label>
              <input
                type="number"
                value={editBudget}
                onChange={(e) => setEditBudget(e.target.value)}
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Trial Days Total</label>
              <input
                type="number"
                value={editDays}
                onChange={(e) => setEditDays(e.target.value)}
                style={inputStyle}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button onClick={() => setEditingCompany(null)} style={cancelButtonStyle}>
                Cancel
              </button>
              <button onClick={saveLimits} style={saveButtonStyle}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Styles
const containerStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: '#f1f5f9',
  padding: '32px'
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '32px'
}

const logoutButtonStyle: React.CSSProperties = {
  padding: '10px 20px',
  background: '#1e293b',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const tabsStyle: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  marginBottom: '24px'
}

const tabStyle: React.CSSProperties = {
  padding: '12px 24px',
  background: 'white',
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  fontSize: '14px',
  fontWeight: 500,
  cursor: 'pointer',
  color: '#64748b'
}

const activeTabStyle: React.CSSProperties = {
  background: '#1e293b',
  color: 'white',
  border: '1px solid #1e293b'
}

const contentStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '12px',
  border: '1px solid #e2e8f0',
  overflow: 'hidden'
}

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse'
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '16px 20px',
  background: '#f8fafc',
  borderBottom: '1px solid #e2e8f0',
  fontSize: '13px',
  fontWeight: 600,
  color: '#64748b',
  textTransform: 'uppercase'
}

const tdStyle: React.CSSProperties = {
  padding: '16px 20px',
  borderBottom: '1px solid #f1f5f9',
  fontSize: '14px',
  color: '#1e293b'
}

const approveButtonStyle: React.CSSProperties = {
  padding: '8px 16px',
  background: '#059669',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer'
}

const rejectButtonStyle: React.CSSProperties = {
  padding: '8px 16px',
  background: '#dc2626',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer'
}

const editButtonStyle: React.CSSProperties = {
  padding: '8px 14px',
  background: '#f1f5f9',
  color: '#475569',
  border: '1px solid #e2e8f0',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer'
}

const disableButtonStyle: React.CSSProperties = {
  padding: '8px 14px',
  background: '#fef2f2',
  color: '#dc2626',
  border: '1px solid #fecaca',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer'
}

const enableButtonStyle: React.CSSProperties = {
  padding: '8px 14px',
  background: '#f0fdf4',
  color: '#059669',
  border: '1px solid #bbf7d0',
  borderRadius: '6px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer'
}

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000
}

const modalStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '16px',
  padding: '32px',
  width: '100%',
  maxWidth: '400px'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#374151'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 16px',
  border: '2px solid #e2e8f0',
  borderRadius: '8px',
  fontSize: '16px',
  boxSizing: 'border-box'
}

const cancelButtonStyle: React.CSSProperties = {
  padding: '12px 24px',
  background: '#f1f5f9',
  color: '#475569',
  border: 'none',
  borderRadius: '8px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const saveButtonStyle: React.CSSProperties = {
  padding: '12px 24px',
  background: '#0ea5e9',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}