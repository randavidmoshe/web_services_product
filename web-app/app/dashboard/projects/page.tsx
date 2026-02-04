'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface Project {
  id: number
  name: string
  description: string | null
  company_id: number
  product_id: number
  created_by_user_id: number
  created_at: string
  updated_at: string
  network_count: number
  form_page_count: number
}

export default function ProjectsPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  
  // Projects
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  
  // Add Project Modal
  const [showAddModal, setShowAddModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [addingProject, setAddingProject] = useState(false)
  
  // Delete Confirmation Modal
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  const [deletingProject, setDeletingProject] = useState(false)

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id')
    const storedUserRole = localStorage.getItem('userType')
    
    // Verify auth via API
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
        setUserRole(data.type)
        loadProjects()
      })
      .catch(() => {
        window.location.href = '/login'
      })
    

  }, [])

  const loadProjects = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/`,
        { credentials: 'include' }
      )
      
      if (response.ok) {
        const data = await response.json()
        setProjects(data)
      } else {
        setError('Failed to load projects')
      }
    } catch (err) {
      setError('Connection error. Is the server running?')
    } finally {
      setLoading(false)
    }
  }

  const handleAddProject = async () => {
    if (!newProjectName.trim()) {
      setError('Project name is required')
      return
    }
    
    setAddingProject(true)
    setError(null)
    
    try {
      const response = await fetch(
        '/api/projects/',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            name: newProjectName.trim(),
            description: newProjectDescription.trim() || null,
            product_id: 1
          })
        }
      )
      
      if (response.ok) {
        setMessage('Project created successfully!')
        setShowAddModal(false)
        setNewProjectName('')
        setNewProjectDescription('')
        loadProjects()
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to create project')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setAddingProject(false)
    }
  }

  const handleDeleteClick = (project: Project, e: React.MouseEvent) => {
    e.stopPropagation()
    setProjectToDelete(project)
    setShowDeleteModal(true)
  }

  const handleConfirmDelete = async () => {
    if (!projectToDelete) return
    
    setDeletingProject(true)
    setError(null)
    
    try {
      const response = await fetch(
        `/api/projects/${projectToDelete.id}`,
        {
          method: 'DELETE',
          credentials: 'include'
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setMessage(`Project deleted. ${data.deleted.networks_deleted} networks and ${data.deleted.form_pages_deleted} form pages removed.`)
        setShowDeleteModal(false)
        setProjectToDelete(null)
        loadProjects()
      } else {
        const errData = await response.json()
        setError(errData.detail || 'Failed to delete project')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setDeletingProject(false)
    }
  }

  const handleProjectClick = (projectId: number) => {
    router.push(`/dashboard/projects/${projectId}`)
  }

  if (loading) return <p>Loading...</p>

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>📁 Projects</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={() => setShowAddModal(true)}
            style={primaryButtonStyle}
          >
            + Add Project
          </button>
          <button 
            onClick={() => router.push('/dashboard')}
            style={secondaryButtonStyle}
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>

      {/* Error/Message Display */}
      {error && (
        <div style={errorBoxStyle}>
          ❌ {error}
          <button onClick={() => setError(null)} style={closeButtonStyle}>×</button>
        </div>
      )}
      {message && (
        <div style={successBoxStyle}>
          ✅ {message}
          <button onClick={() => setMessage(null)} style={closeButtonStyle}>×</button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Loading projects...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && projects.length === 0 && (
        <div style={emptyStateStyle}>
          <h3>No projects yet</h3>
          <p>Create your first project to start discovering form pages.</p>
          <button 
            onClick={() => setShowAddModal(true)}
            style={{ ...primaryButtonStyle, marginTop: '20px' }}
          >
            + Create Your First Project
          </button>
        </div>
      )}

      {/* Projects List */}
      {!loading && projects.length > 0 && (
        <div style={{ display: 'grid', gap: '16px' }}>
          {projects.map(project => (
            <div 
              key={project.id}
              style={projectCardStyle}
              onClick={() => handleProjectClick(project.id)}
            >
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: '0 0 8px 0' }}>{project.name}</h3>
                {project.description && (
                  <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
                    {project.description}
                  </p>
                )}
                <div style={{ display: 'flex', gap: '20px', fontSize: '14px', color: '#888' }}>
                  <span>🌐 {project.network_count} networks</span>
                  <span>📄 {project.form_page_count} form pages</span>
                  <span>📅 Created: {new Date(project.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button
                  onClick={(e) => handleDeleteClick(project, e)}
                  style={deleteButtonStyle}
                  title="Delete project"
                >
                  🗑️
                </button>
                <span style={{ color: '#ccc', fontSize: '20px' }}>→</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Project Modal */}
      {showAddModal && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0 }}>Create New Project</h2>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Project Name *</label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Enter project name"
                style={inputStyle}
                autoFocus
              />
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={labelStyle}>Description (optional)</label>
              <textarea
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
                placeholder="Enter project description"
                style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setNewProjectName('')
                  setNewProjectDescription('')
                }}
                style={secondaryButtonStyle}
                disabled={addingProject}
              >
                Cancel
              </button>
              <button
                onClick={handleAddProject}
                style={primaryButtonStyle}
                disabled={addingProject || !newProjectName.trim()}
              >
                {addingProject ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && projectToDelete && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle}>
            <h2 style={{ marginTop: 0, color: '#c62828' }}>⚠️ Delete Project?</h2>
            
            <p>Are you sure you want to delete <strong>{projectToDelete.name}</strong>?</p>
            
            <div style={warningBoxStyle}>
              <strong>This will permanently delete:</strong>
              <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                <li>{projectToDelete.network_count} network(s)</li>
                <li>{projectToDelete.form_page_count} form page(s)</li>
              </ul>
              <p style={{ margin: 0, fontWeight: 'bold' }}>This action cannot be undone!</p>
            </div>
            
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button
                onClick={() => {
                  setShowDeleteModal(false)
                  setProjectToDelete(null)
                }}
                style={secondaryButtonStyle}
                disabled={deletingProject}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                style={dangerButtonStyle}
                disabled={deletingProject}
              >
                {deletingProject ? 'Deleting...' : 'Delete Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Styles
const primaryButtonStyle: React.CSSProperties = {
  background: '#0070f3',
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const secondaryButtonStyle: React.CSSProperties = {
  background: '#f5f5f5',
  color: '#333',
  padding: '10px 20px',
  border: '1px solid #ddd',
  borderRadius: '6px',
  fontSize: '14px',
  cursor: 'pointer'
}

const dangerButtonStyle: React.CSSProperties = {
  background: '#c62828',
  color: 'white',
  padding: '10px 20px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
}

const deleteButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid #ddd',
  borderRadius: '4px',
  padding: '8px 12px',
  cursor: 'pointer',
  fontSize: '16px'
}

const closeButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '0 0 0 10px'
}

const errorBoxStyle: React.CSSProperties = {
  background: '#ffebee',
  color: '#c62828',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
}

const successBoxStyle: React.CSSProperties = {
  background: '#e8f5e9',
  color: '#2e7d32',
  padding: '12px 16px',
  borderRadius: '6px',
  marginBottom: '20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
}

const warningBoxStyle: React.CSSProperties = {
  background: '#fff3e0',
  color: '#e65100',
  padding: '16px',
  borderRadius: '6px',
  marginTop: '16px'
}

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '60px 20px',
  background: '#f9f9f9',
  borderRadius: '8px',
  border: '2px dashed #ddd'
}

const projectCardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: '8px',
  padding: '20px',
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  transition: 'box-shadow 0.2s, border-color 0.2s'
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

const modalContentStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '8px',
  padding: '24px',
  width: '100%',
  maxWidth: '500px',
  maxHeight: '90vh',
  overflow: 'auto'
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '6px',
  fontWeight: 500,
  color: '#333'
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  fontSize: '14px',
  boxSizing: 'border-box'
}
