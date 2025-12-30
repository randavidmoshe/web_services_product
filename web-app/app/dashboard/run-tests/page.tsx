'use client'

export default function RunTestsPage() {
  return (
    <div style={{
      background: 'rgba(75, 85, 99, 0.5)',
      backdropFilter: 'blur(20px)',
      borderRadius: '28px',
      padding: '100px 80px',
      textAlign: 'center',
      border: '2px solid rgba(156, 163, 175, 0.35)',
      boxShadow: '0 0 50px rgba(156, 163, 175, 0.15), 0 20px 60px rgba(0,0,0,0.3), inset 0 0 30px rgba(255,255,255,0.03)'
    }}>
      <div style={{
        width: '110px',
        height: '110px',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.3))',
        borderRadius: '28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '48px',
        margin: '0 auto 28px',
        border: '2px solid rgba(99, 102, 241, 0.5)',
        boxShadow: '0 0 30px rgba(99, 102, 241, 0.4)'
      }}>▶️</div>
      <h2 style={{ margin: '0 0 16px', color: '#f3f4f6', fontSize: '32px', fontWeight: 700, letterSpacing: '-0.5px' }}>Run Tests</h2>
      <p style={{ color: '#9ca3af', margin: 0, fontSize: '18px', lineHeight: 1.6 }}>Coming soon - Execute your test scenarios and view results.</p>
    </div>
  )
}
