'use client'
import { useState } from 'react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage('')
    
    try {
      const response = await fetch('http://localhost:8001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('token', data.token)
        localStorage.setItem('userType', data.type)
        localStorage.setItem('user_id', data.user_id)
        if (data.company_id) {
          localStorage.setItem('company_id', data.company_id)
        }
        setMessage('✅ Login successful!')
        setTimeout(() => window.location.href = '/dashboard', 1000)
      } else {
        setMessage('❌ Invalid credentials')
      }
    } catch (error) {
      setMessage('❌ Connection error')
    }
  }

  return (
    <div style={{ padding: '40px', maxWidth: '400px', margin: '100px auto' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>Login</h1>
      
      <form onSubmit={handleLogin}>
        <input
          type="email"
          placeholder="admin@acme.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            marginBottom: '15px',
            border: '1px solid #ddd',
            borderRadius: '5px',
            fontSize: '16px'
          }}
          required
        />
        
        <input
          type="password"
          placeholder="••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            marginBottom: '15px',
            border: '1px solid #ddd',
            borderRadius: '5px',
            fontSize: '16px'
          }}
          required
        />
        
        <button
          type="submit"
          style={{
            width: '100%',
            padding: '12px',
            background: '#0070f3',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            fontSize: '16px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          Login
        </button>
      </form>
      
      {message && (
        <div style={{
          marginTop: '20px',
          padding: '10px',
          textAlign: 'center',
          color: message.includes('✅') ? 'green' : 'red'
        }}>
          {message}
        </div>
      )}

      <div style={{ marginTop: '30px', fontSize: '14px', color: '#666' }}>
        <strong>Test Accounts:</strong>
        <div style={{ marginTop: '10px' }}>admin@formfinder.com / admin123</div>
        <div>admin@acme.com / admin123</div>
        <div>user@acme.com / user123</div>
      </div>
    </div>
  )
}
