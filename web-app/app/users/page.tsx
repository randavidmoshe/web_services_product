'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface User {
  id: number
  email: string
  name: string
  role: string
  company_id: number
  company_name: string | null
  totp_enabled: boolean
  created_at: string
  last_login_at: string | null
}

interface Company {
  id: number
  name: string
  billing_email: string
  created_at: string
  require_2fa: boolean
}

export default function UsersPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [userType, setUserType] = useState<string | null>(null)
  
  const [users, setUsers] = useState<User[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Add user modal
  const [showAddModal, setShowAddModal] = useState(false)
  const [newUserName, setNewUserName] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserPassword, setNewUserPassword] = useState('')
  const [newUserRole, setNewUserRole] = useState('user')
  const [addingUser, setAddingUser] = useState(false)
  
  // Edit user modal
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editUserName, setEditUserName] = useState('')
  const [editUserEmail, setEditUserEmail] = useState('')
  const [editUserRole, setEditUserRole] = useState('')
  const [savingUser, setSavingUser] = useState(false)
  
  // Delete confirmation
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [userToDelete, setUserToDelete] = useState<User | null>(null)
  const [deletingUser, setDeletingUser] = useState(false)
  
  // Reset 2FA confirmation
  const [showReset2FAModal, setShowReset2FAModal] = useState(false)
  const [userToReset2FA, setUserToReset2FA] = useState<User | null>(null)
  const [resetting2FA, setResetting2FA] = useState(false)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUserType = localStorage.getItem('userType')
    
    if (!storedToken) {
      router.push('/login')
      return
    }
    
    // Only admins and super_admin can access this page
    if (storedUserType !== 'admin' && storedUserType !== 'super_admin') {
      router.push('/dashboard')
      return
    }
    
    setToken(storedToken)
    setUserType(storedUserType)
  }, [router])

  useEffect(() => {
    if (token && userType) {
      if (userType === 'super_admin') {
        loadCompanies()
      }
      loadUsers()
    }
  }, [token, userType, selectedCompanyId])

  const loadCompanies = async () => {
    try {
      const response = await fetch('/api/users/companies', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setCompanies(data)
      }
    } catch (err) {
      console.error('Failed to load companies:', err)
    }
  }

  const loadUsers = async () => {
    setLoading(true)
    setError(null)
    
    try {
      let url = '/api/users'
      if (selectedCompanyId) {
        url += `?company_id=${selectedCompanyId}`
      }
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      } else if (response.status === 403) {
        router.push('/dashboard')
      } else {
        setError('Failed to load users')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddingUser(true)
    setError(null)
    
    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newUserName,
          email: newUserEmail,
          password: newUserPassword,
          role: newUserRole
        })
      })
      
      if (response.ok) {
        setMessage('User created successfully!')
        setShowAddModal(false)
        setNewUserName('')
        setNewUserEmail('')
        setNewUserPassword('')
        setNewUserRole('user')
        loadUsers()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to create user')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setAddingUser(false)
    }
  }

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    
    setSavingUser(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/users/${editingUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: editUserName,
          email: editUserEmail,
          role: editUserRole
        })
      })
      
      if (response.ok) {
        setMessage('User updated successfully!')
        setShowEditModal(false)
        setEditingUser(null)
        loadUsers()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to update user')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setSavingUser(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!userToDelete) return
    
    setDeletingUser(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/users/${userToDelete.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        setMessage('User deleted successfully!')
        setShowDeleteModal(false)
        setUserToDelete(null)
        loadUsers()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to delete user')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingUser(false)
    }
  }

  const handleReset2FA = async () => {
    if (!userToReset2FA) return
    
    setResetting2FA(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/users/${userToReset2FA.id}/reset-2fa`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        setMessage(`2FA reset for ${userToReset2FA.email}. They can now log in without 2FA.`)
        setShowReset2FAModal(false)
        setUserToReset2FA(null)
        loadUsers()
        setTimeout(() => setMessage(null), 5000)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to reset 2FA')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setResetting2FA(false)
    }
  }

  const openEditModal = (user: User) => {
    setEditingUser(user)
    setEditUserName(user.name)
    setEditUserEmail(user.email)
    setEditUserRole(user.role)
    setShowEditModal(true)
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (!token || !userType) {
    return null
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%)',
      padding: '32px',
      fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Back Button */}
        <button
          onClick={() => router.push('/dashboard')}
          style={{
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff',
            padding: '10px 20px',
            borderRadius: '10px',
            fontSize: '14px',
            cursor: 'pointer',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          ← Back to Dashboard
        </button>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '32px', fontWeight: 700, color: '#fff' }}>
              👥 Team Members
            </h1>
            <p style={{ margin: '8px 0 0', color: '#a0aec0', fontSize: '16px' }}>
              {userType === 'super_admin' ? 'Manage all users across companies' : 'Manage users in your company'}
            </p>
          </div>
          
          {userType !== 'super_admin' && (
            <button
              onClick={() => setShowAddModal(true)}
              style={{
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                color: '#fff',
                border: 'none',
                padding: '14px 28px',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 20px rgba(99, 102, 241, 0.4)'
              }}
            >
              ➕ Add User
            </button>
          )}
        </div>

        {/* Super Admin Company Filter */}
        {userType === 'super_admin' && companies.length > 0 && (
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '20px 24px',
            marginBottom: '24px',
            border: '1px solid rgba(255,255,255,0.1)'
          }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#a0aec0', fontSize: '14px', fontWeight: 500 }}>
              Filter by Company
            </label>
            <select
              value={selectedCompanyId || ''}
              onChange={(e) => setSelectedCompanyId(e.target.value ? Number(e.target.value) : null)}
              style={{
                width: '300px',
                padding: '12px 16px',
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '10px',
                color: '#fff',
                fontSize: '15px',
                cursor: 'pointer'
              }}
            >
              <option value="" style={{ background: '#1a1a2e' }}>All Companies</option>
              {companies.map(company => (
                <option key={company.id} value={company.id} style={{ background: '#1a1a2e' }}>{company.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Messages */}
        {message && (
          <div style={{
            background: 'rgba(34, 197, 94, 0.15)',
            border: '1px solid rgba(34, 197, 94, 0.4)',
            color: '#4ade80',
            padding: '16px 20px',
            borderRadius: '12px',
            marginBottom: '24px',
            fontSize: '15px'
          }}>
            ✅ {message}
          </div>
        )}

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            padding: '16px 20px',
            borderRadius: '12px',
            marginBottom: '24px',
            fontSize: '15px'
          }}>
            ❌ {error}
          </div>
        )}

        {/* Users Table */}
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '20px',
          border: '1px solid rgba(255,255,255,0.1)',
          overflow: 'hidden'
        }}>
          {loading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#a0aec0' }}>
              Loading users...
            </div>
          ) : users.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: '#a0aec0' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>👤</div>
              <p style={{ fontSize: '18px', marginBottom: '8px', color: '#fff' }}>No users found</p>
              {userType !== 'super_admin' && (
                <p style={{ fontSize: '14px' }}>Click "Add User" to create your first team member</p>
              )}
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.08)' }}>
                  <th style={thStyle}>Name</th>
                  <th style={thStyle}>Email</th>
                  <th style={thStyle}>Role</th>
                  {userType === 'super_admin' && <th style={thStyle}>Company</th>}
                  <th style={thStyle}>2FA</th>
                  <th style={thStyle}>Last Login</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, color: '#fff' }}>{user.name}</span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ color: '#a0aec0' }}>{user.email}</span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        display: 'inline-block',
                        padding: '6px 14px',
                        borderRadius: '20px',
                        fontSize: '13px',
                        fontWeight: 600,
                        background: user.role === 'admin' 
                          ? 'rgba(99, 102, 241, 0.25)' 
                          : 'rgba(255,255,255,0.1)',
                        color: user.role === 'admin' ? '#a5b4fc' : '#a0aec0'
                      }}>
                        {user.role === 'admin' ? '👑 Admin' : '👤 User'}
                      </span>
                    </td>
                    {userType === 'super_admin' && (
                      <td style={tdStyle}>
                        <span style={{ color: '#a0aec0' }}>{user.company_name || '-'}</span>
                      </td>
                    )}
                    <td style={tdStyle}>
                      {user.totp_enabled ? (
                        <span style={{ color: '#4ade80', fontWeight: 500 }}>🔐 Enabled</span>
                      ) : (
                        <span style={{ color: '#f87171', fontWeight: 500 }}>⚠️ Disabled</span>
                      )}
                    </td>
                    <td style={tdStyle}>
                      <span style={{ color: '#a0aec0', fontSize: '14px' }}>
                        {formatDate(user.last_login_at)}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => openEditModal(user)}
                          style={actionButtonStyle}
                          title="Edit user"
                        >
                          ✏️
                        </button>
                        {user.totp_enabled && (
                          <button
                            onClick={() => {
                              setUserToReset2FA(user)
                              setShowReset2FAModal(true)
                            }}
                            style={actionButtonStyle}
                            title="Reset 2FA"
                          >
                            🔓
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setUserToDelete(user)
                            setShowDeleteModal(true)
                          }}
                          style={{ ...actionButtonStyle, background: 'rgba(239, 68, 68, 0.2)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                          title="Delete user"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Add User Modal */}
        {showAddModal && (
          <div style={modalOverlayStyle}>
            <div style={modalContentStyle}>
              <h2 style={{ margin: '0 0 24px', fontSize: '24px', fontWeight: 700, color: '#fff' }}>
                ➕ Add New User
              </h2>
              
              <form onSubmit={handleAddUser}>
                <div style={{ marginBottom: '20px' }}>
                  <label style={labelStyle}>Full Name *</label>
                  <input
                    type="text"
                    value={newUserName}
                    onChange={(e) => setNewUserName(e.target.value)}
                    style={inputStyle}
                    placeholder="John Smith"
                    required
                  />
                </div>
                
                <div style={{ marginBottom: '20px' }}>
                  <label style={labelStyle}>Email Address *</label>
                  <input
                    type="email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    style={inputStyle}
                    placeholder="john@company.com"
                    required
                  />
                </div>
                
                <div style={{ marginBottom: '20px' }}>
                  <label style={labelStyle}>Password *</label>
                  <input
                    type="password"
                    value={newUserPassword}
                    onChange={(e) => setNewUserPassword(e.target.value)}
                    style={inputStyle}
                    placeholder="At least 6 characters"
                    minLength={6}
                    required
                  />
                </div>
                
                <div style={{ marginBottom: '28px' }}>
                  <label style={labelStyle}>Role *</label>
                  <select
                    value={newUserRole}
                    onChange={(e) => setNewUserRole(e.target.value)}
                    style={inputStyle}
                  >
                    <option value="user" style={{ background: '#1e293b' }}>User - Can run tests</option>
                    <option value="admin" style={{ background: '#1e293b' }}>Admin - Can manage users & settings</option>
                  </select>
                </div>
                
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    style={cancelButtonStyle}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={addingUser}
                    style={primaryButtonStyle}
                  >
                    {addingUser ? 'Creating...' : 'Create User'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {showEditModal && editingUser && (
          <div style={modalOverlayStyle}>
            <div style={modalContentStyle}>
              <h2 style={{ margin: '0 0 24px', fontSize: '24px', fontWeight: 700, color: '#fff' }}>
                ✏️ Edit User
              </h2>
              
              <form onSubmit={handleEditUser}>
                <div style={{ marginBottom: '20px' }}>
                  <label style={labelStyle}>Full Name *</label>
                  <input
                    type="text"
                    value={editUserName}
                    onChange={(e) => setEditUserName(e.target.value)}
                    style={inputStyle}
                    required
                  />
                </div>
                
                <div style={{ marginBottom: '20px' }}>
                  <label style={labelStyle}>Email Address *</label>
                  <input
                    type="email"
                    value={editUserEmail}
                    onChange={(e) => setEditUserEmail(e.target.value)}
                    style={inputStyle}
                    required
                  />
                </div>
                
                <div style={{ marginBottom: '28px' }}>
                  <label style={labelStyle}>Role *</label>
                  <select
                    value={editUserRole}
                    onChange={(e) => setEditUserRole(e.target.value)}
                    style={inputStyle}
                  >
                    <option value="user" style={{ background: '#1e293b' }}>User - Can run tests</option>
                    <option value="admin" style={{ background: '#1e293b' }}>Admin - Can manage users & settings</option>
                  </select>
                </div>
                
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false)
                      setEditingUser(null)
                    }}
                    style={cancelButtonStyle}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingUser}
                    style={primaryButtonStyle}
                  >
                    {savingUser ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && userToDelete && (
          <div style={modalOverlayStyle}>
            <div style={modalContentStyle}>
              <h2 style={{ margin: '0 0 16px', fontSize: '24px', fontWeight: 700, color: '#fff' }}>
                🗑️ Delete User
              </h2>
              <p style={{ color: '#a0aec0', marginBottom: '24px', lineHeight: 1.6 }}>
                Are you sure you want to delete <strong style={{ color: '#fff' }}>{userToDelete.name}</strong> ({userToDelete.email})?
                This action cannot be undone.
              </p>
              
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowDeleteModal(false)
                    setUserToDelete(null)
                  }}
                  style={cancelButtonStyle}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteUser}
                  disabled={deletingUser}
                  style={dangerButtonStyle}
                >
                  {deletingUser ? 'Deleting...' : 'Delete User'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Reset 2FA Confirmation Modal */}
        {showReset2FAModal && userToReset2FA && (
          <div style={modalOverlayStyle}>
            <div style={modalContentStyle}>
              <h2 style={{ margin: '0 0 16px', fontSize: '24px', fontWeight: 700, color: '#fff' }}>
                🔓 Reset Two-Factor Authentication
              </h2>
              <p style={{ color: '#a0aec0', marginBottom: '16px', lineHeight: 1.6 }}>
                Are you sure you want to reset 2FA for <strong style={{ color: '#fff' }}>{userToReset2FA.name}</strong> ({userToReset2FA.email})?
              </p>
              <div style={{
                background: 'rgba(251, 191, 36, 0.15)',
                border: '1px solid rgba(251, 191, 36, 0.4)',
                borderRadius: '12px',
                padding: '16px',
                marginBottom: '24px'
              }}>
                <p style={{ margin: 0, color: '#fbbf24', fontSize: '14px' }}>
                  ⚠️ The user will be able to log in without 2FA until they set it up again.
                </p>
              </div>
              
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowReset2FAModal(false)
                    setUserToReset2FA(null)
                  }}
                  style={cancelButtonStyle}
                >
                  Cancel
                </button>
                <button
                  onClick={handleReset2FA}
                  disabled={resetting2FA}
                  style={primaryButtonStyle}
                >
                  {resetting2FA ? 'Resetting...' : 'Reset 2FA'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Styles
const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '16px 20px',
  fontSize: '13px',
  fontWeight: 600,
  color: '#a0aec0',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
}

const tdStyle: React.CSSProperties = {
  padding: '16px 20px',
  fontSize: '15px'
}

const actionButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '8px',
  padding: '8px 12px',
  cursor: 'pointer',
  fontSize: '16px',
  transition: 'all 0.2s ease'
}

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.7)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '24px'
}

const modalContentStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #1e293b, #0f172a)',
  borderRadius: '24px',
  padding: '36px',
  width: '100%',
  maxWidth: '480px',
  boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
  border: '1px solid rgba(255,255,255,0.1)'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#e2e8f0'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px 18px',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '12px',
  fontSize: '16px',
  boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.1)',
  color: '#fff',
  outline: 'none'
}

const cancelButtonStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.1)',
  color: '#a0aec0',
  border: '1px solid rgba(255,255,255,0.2)',
  padding: '14px 28px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer'
}

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  border: 'none',
  padding: '14px 28px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.4)'
}

const dangerButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  color: '#fff',
  border: 'none',
  padding: '14px 28px',
  borderRadius: '12px',
  fontSize: '16px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 20px rgba(239, 68, 68, 0.4)'
}
