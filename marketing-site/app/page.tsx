'use client'
import Link from 'next/link'

export default function Home() {
  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Navigation */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 60px',
        background: '#fff',
        borderBottom: '1px solid #eee',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '28px' }}>🔷</span>
          <span style={{ fontSize: '24px', fontWeight: 700, color: '#1a1a2e' }}>QUATHERA</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/pricing" style={{ color: '#555', fontWeight: 500 }}>Pricing</Link>
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

      {/* Hero Section */}
      <section style={{
        padding: '100px 60px',
        background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
        textAlign: 'center'
      }}>
        <h1 style={{
          fontSize: '56px',
          fontWeight: 800,
          color: '#1a1a2e',
          marginBottom: '24px',
          lineHeight: 1.2
        }}>
          AI-Powered Web Testing<br />
          <span style={{ color: '#2563eb' }}>Automated</span>
        </h1>
        <p style={{
          fontSize: '20px',
          color: '#64748b',
          maxWidth: '600px',
          margin: '0 auto 40px'
        }}>
          Automatically discover and test form pages in your web applications. 
          Let AI handle the tedious work while you focus on building great products.
        </p>
        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <Link href="/signup" style={{
            background: '#2563eb',
            color: '#fff',
            padding: '16px 32px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '18px'
          }}>
            Start Free Trial
          </Link>
          <Link href="/pricing" style={{
            background: '#fff',
            color: '#2563eb',
            padding: '16px 32px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '18px',
            border: '2px solid #2563eb'
          }}>
            View Pricing
          </Link>
        </div>
      </section>

      {/* Products Section */}
      <section style={{ padding: '80px 60px', background: '#fff' }}>
        <h2 style={{
          fontSize: '40px',
          fontWeight: 700,
          textAlign: 'center',
          marginBottom: '60px',
          color: '#1a1a2e'
        }}>
          Our Products
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '32px',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          {/* Form Pages Testing */}
          <div style={{
            padding: '40px',
            borderRadius: '16px',
            border: '2px solid #2563eb',
            background: '#f8fafc'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>📋</div>
            <h3 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '12px' }}>Form Pages Testing</h3>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              Automatically discover all form pages in your application. AI-powered crawling identifies forms, fields, and validation rules.
            </p>
            <Link href="/pricing" style={{
              color: '#2563eb',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              Learn more →
            </Link>
          </div>

          {/* Shopping Site Testing */}
          <div style={{
            padding: '40px',
            borderRadius: '16px',
            border: '1px solid #e2e8f0',
            background: '#fff'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>🛒</div>
            <h3 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '12px' }}>Shopping Site Testing</h3>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              End-to-end e-commerce testing. From product browsing to checkout flow, ensure your customers have a smooth experience.
            </p>
            <span style={{ color: '#94a3b8', fontWeight: 500 }}>Coming Soon</span>
          </div>

          {/* Marketing Website Testing */}
          <div style={{
            padding: '40px',
            borderRadius: '16px',
            border: '1px solid #e2e8f0',
            background: '#fff'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>📊</div>
            <h3 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '12px' }}>Marketing Website Testing</h3>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              Validate your marketing pages, landing pages, and content. Ensure links work and forms capture leads properly.
            </p>
            <span style={{ color: '#94a3b8', fontWeight: 500 }}>Coming Soon</span>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section style={{ padding: '80px 60px', background: '#f8fafc' }}>
        <h2 style={{
          fontSize: '40px',
          fontWeight: 700,
          textAlign: 'center',
          marginBottom: '60px',
          color: '#1a1a2e'
        }}>
          How It Works
        </h2>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '60px',
          maxWidth: '1000px',
          margin: '0 auto'
        }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
              width: '80px',
              height: '80px',
              background: '#2563eb',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#fff'
            }}>1</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>Install Agent</h3>
            <p style={{ color: '#64748b' }}>Download and run our lightweight agent on your machine</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
              width: '80px',
              height: '80px',
              background: '#2563eb',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#fff'
            }}>2</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>Add Your Site</h3>
            <p style={{ color: '#64748b' }}>Configure your web application URL and test credentials</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
              width: '80px',
              height: '80px',
              background: '#2563eb',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#fff'
            }}>3</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>AI Discovers</h3>
            <p style={{ color: '#64748b' }}>Our AI crawls your site and discovers all form pages automatically</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section style={{
        padding: '80px 60px',
        background: '#1a1a2e',
        textAlign: 'center'
      }}>
        <h2 style={{
          fontSize: '40px',
          fontWeight: 700,
          color: '#fff',
          marginBottom: '20px'
        }}>
          Ready to Get Started?
        </h2>
        <p style={{
          fontSize: '18px',
          color: '#94a3b8',
          marginBottom: '40px'
        }}>
          Start your 14-day free trial. No credit card required.
        </p>
        <Link href="/signup" style={{
          background: '#2563eb',
          color: '#fff',
          padding: '16px 40px',
          borderRadius: '8px',
          fontWeight: 600,
          fontSize: '18px',
          display: 'inline-block'
        }}>
          Start Free Trial
        </Link>
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
