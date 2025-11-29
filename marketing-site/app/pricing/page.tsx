'use client'
import Link from 'next/link'

export default function Pricing() {
  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Navigation */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 60px',
        background: '#fff',
        borderBottom: '1px solid #eee'
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '28px' }}>🔷</span>
          <span style={{ fontSize: '24px', fontWeight: 700, color: '#1a1a2e' }}>QUATHERA</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/pricing" style={{ color: '#2563eb', fontWeight: 600 }}>Pricing</Link>
          <Link href="/login" style={{ color: '#555', fontWeight: 500 }}>Login</Link>
          <Link href="/signup" style={{
            background: '#2563eb',
            color: '#fff',
            padding: '10px 24px',
            borderRadius: '8px',
            fontWeight: 600
          }}>
            Start Free Trial
          </Link>
        </div>
      </nav>

      {/* Pricing Header */}
      <section style={{
        padding: '80px 60px 40px',
        textAlign: 'center',
        background: '#f8fafc'
      }}>
        <h1 style={{
          fontSize: '48px',
          fontWeight: 800,
          color: '#1a1a2e',
          marginBottom: '16px'
        }}>
          Simple, Transparent Pricing
        </h1>
        <p style={{
          fontSize: '20px',
          color: '#64748b'
        }}>
          Start free, upgrade when you need more
        </p>
      </section>

      {/* Pricing Cards */}
      <section style={{
        padding: '60px',
        background: '#f8fafc'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '24px',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          {/* Free Trial */}
          <div style={{
            padding: '32px',
            borderRadius: '16px',
            background: '#fff',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Free Trial</h3>
            <div style={{ marginBottom: '20px' }}>
              <span style={{ fontSize: '40px', fontWeight: 800 }}>$0</span>
              <span style={{ color: '#64748b' }}>/14 days</span>
            </div>
            <ul style={{ listStyle: 'none', marginBottom: '24px' }}>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 14-day trial</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Limited AI usage</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 1 project</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Email support</li>
            </ul>
            <Link href="/signup?plan=trial" style={{
              display: 'block',
              textAlign: 'center',
              padding: '12px',
              borderRadius: '8px',
              border: '2px solid #2563eb',
              color: '#2563eb',
              fontWeight: 600
            }}>
              Start Free
            </Link>
          </div>

          {/* Free Trial BYOK */}
          <div style={{
            padding: '32px',
            borderRadius: '16px',
            background: '#fff',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Free Trial (BYOK)</h3>
            <div style={{ marginBottom: '20px' }}>
              <span style={{ fontSize: '40px', fontWeight: 800 }}>$0</span>
              <span style={{ color: '#64748b' }}>/14 days</span>
            </div>
            <ul style={{ listStyle: 'none', marginBottom: '24px' }}>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 14-day trial</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Your own API key</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Unlimited AI usage</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 1 project</li>
            </ul>
            <Link href="/signup?plan=trial_byok" style={{
              display: 'block',
              textAlign: 'center',
              padding: '12px',
              borderRadius: '8px',
              border: '2px solid #2563eb',
              color: '#2563eb',
              fontWeight: 600
            }}>
              Start with Your Key
            </Link>
          </div>

          {/* Starter */}
          <div style={{
            padding: '32px',
            borderRadius: '16px',
            background: '#fff',
            border: '2px solid #2563eb',
            position: 'relative'
          }}>
            <div style={{
              position: 'absolute',
              top: '-12px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: '#2563eb',
              color: '#fff',
              padding: '4px 16px',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 600
            }}>
              POPULAR
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Starter</h3>
            <div style={{ marginBottom: '20px' }}>
              <span style={{ fontSize: '40px', fontWeight: 800 }}>$300</span>
              <span style={{ color: '#64748b' }}>/month</span>
            </div>
            <ul style={{ listStyle: 'none', marginBottom: '24px' }}>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ $300 AI budget/month</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 5 projects</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 3 team members</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Priority support</li>
            </ul>
            <Link href="/signup?plan=starter" style={{
              display: 'block',
              textAlign: 'center',
              padding: '12px',
              borderRadius: '8px',
              background: '#2563eb',
              color: '#fff',
              fontWeight: 600
            }}>
              Get Started
            </Link>
          </div>

          {/* Professional */}
          <div style={{
            padding: '32px',
            borderRadius: '16px',
            background: '#fff',
            border: '1px solid #e2e8f0'
          }}>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Professional</h3>
            <div style={{ marginBottom: '20px' }}>
              <span style={{ fontSize: '40px', fontWeight: 800 }}>$500</span>
              <span style={{ color: '#64748b' }}>/month</span>
            </div>
            <ul style={{ listStyle: 'none', marginBottom: '24px' }}>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ $500 AI budget/month</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Unlimited projects</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ 10 team members</li>
              <li style={{ padding: '8px 0', color: '#475569' }}>✓ Dedicated support</li>
            </ul>
            <Link href="/signup?plan=professional" style={{
              display: 'block',
              textAlign: 'center',
              padding: '12px',
              borderRadius: '8px',
              border: '2px solid #2563eb',
              color: '#2563eb',
              fontWeight: 600
            }}>
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '40px 60px',
        background: '#0f0f1a',
        color: '#64748b',
        textAlign: 'center'
      }}>
        <p>© 2025 Quathera. All rights reserved.</p>
      </footer>
    </div>
  )
}
