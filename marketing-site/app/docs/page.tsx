'use client'
import Link from 'next/link'

const QuatheraLogo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
        <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
        <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
      </linearGradient>
    </defs>
    <g transform="translate(50, 50)">
      <circle cx="0" cy="0" r="35" fill="none" stroke="url(#logoGrad)" strokeWidth="3"/>
      <g stroke="url(#logoGrad)" strokeWidth="2" fill="none" strokeLinecap="round">
        <path d="M -22 -12 Q -28 0 -24 12 Q -18 26 0 30 Q 18 26 24 12 Q 28 0 22 -12 Q 14 -28 0 -30 Q -14 -28 -22 -12"/>
        <path d="M 16 18 L 32 34 L 42 30"/>
        <circle cx="42" cy="30" r="3" fill="url(#logoGrad)"/>
      </g>
    </g>
  </svg>
)

const documents = [
  {
    icon: '👤',
    title: 'User Guide',
    description: 'Complete guide for using Quathera: installation, configuration, form discovery, test execution, and results analysis.',
    filename: 'Quathera-User-Guide.pdf',
    tag: 'Manual'
  },
  {
    icon: '👑',
    title: 'Admin Guide',
    description: 'Administrator guide for managing users, projects, AI budget, billing, security settings, and audit logs.',
    filename: 'Quathera-Admin-Guide.pdf',
    tag: 'Manual'
  },
  {
    icon: '🚀',
    title: 'Getting Started Guide',
    description: 'Quick start guide to set up Quathera, configure test sites, and run your first AI-powered tests.',
    filename: 'Quathera-Getting-Started-Guide.pdf',
    tag: 'Quick Start'
  },
  {
    icon: '🌐',
    title: 'Test Sites Guide',
    description: 'Configure test sites with user types, environments (QA/Staging/Production), and credential management.',
    filename: 'Quathera-Test-Sites-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '🔍',
    title: 'Form Discovery Guide',
    description: 'How AI automatically discovers every form in your application, handles SPAs, iframes, and edge cases.',
    filename: 'Quathera-Form-Discovery-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '🗺️',
    title: 'Form Mapping Guide',
    description: 'Deep dive into field analysis, junction paths, conditional logic, and parent-child relationships.',
    filename: 'Quathera-Form-Mapping-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '⚡',
    title: 'Test Scenarios Guide',
    description: 'How AI generates CRUD cycles, junction path coverage, negative tests, and multi-user workflows.',
    filename: 'Quathera-Test-Scenarios-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '▶️',
    title: 'Test Runner Guide',
    description: 'Running tests, monitoring execution, browser options, self-healing in action, and handling errors.',
    filename: 'Quathera-Test-Runner-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '📊',
    title: 'Reports & Analytics Guide',
    description: 'Test coverage matrix, bug reports, Jira integration, duplicate detection, and regression tracking.',
    filename: 'Quathera-Reports-Analytics-Guide.pdf',
    tag: 'Guide'
  },
  {
    icon: '🔐',
    title: 'Security Overview',
    description: 'Overview of our security architecture, encryption, compliance, and data protection practices.',
    filename: 'Quathera-Security-Overview.pdf',
    tag: 'Security'
  },
  {
    icon: '📋',
    title: 'Product Brief',
    description: 'Executive summary of Quathera capabilities, features, and benefits for decision makers.',
    filename: 'Quathera-Product-Brief.pdf',
    tag: 'Overview'
  },
  {
    icon: '💰',
    title: 'ROI Whitepaper',
    description: 'Analysis of test automation costs and how AI-powered testing delivers 10x ROI.',
    filename: 'Quathera-ROI-Whitepaper.pdf',
    tag: 'Business Case'
  }
]

export default function DocsPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#0A0E17', color: '#fff', fontFamily: "'SF Pro Display', 'Segoe UI', sans-serif" }}>
      {/* Background */}
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundImage: 'linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px)', backgroundSize: '60px 60px', pointerEvents: 'none' }} />

      {/* Nav */}
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 60px', background: 'rgba(10,14,23,0.85)', backdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(255,255,255,0.05)', position: 'relative', zIndex: 10 }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
          <QuatheraLogo />
          <span style={{ fontSize: '22px', fontWeight: 600, letterSpacing: '2px', background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>QUATHERA</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/products" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Products</Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>How It Works</Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Pricing</Link>
          <Link href="/docs" style={{ color: '#00F5D4', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>Docs</Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Login</Link>
          <Link href="/signup" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '12px 24px', borderRadius: '8px', fontWeight: 600, fontSize: '14px', textDecoration: 'none' }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '120px 60px 60px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <h1 style={{ fontSize: '56px', fontWeight: 700, marginBottom: '24px' }}>
          Documentation & <span style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Resources</span>
        </h1>
        <p style={{ fontSize: '20px', color: 'rgba(255,255,255,0.6)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.7 }}>
          Everything you need to get started with Quathera and understand our platform.
        </p>
      </section>

      {/* Documents Grid */}
      <section style={{ padding: '40px 60px 120px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px' }}>
          {documents.map((doc, i) => (
            <a 
              key={i} 
              href={`/docs/${doc.filename}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ 
                background: 'rgba(255,255,255,0.03)', 
                border: '1px solid rgba(255,255,255,0.08)', 
                borderRadius: '20px', 
                padding: '32px',
                textDecoration: 'none',
                color: 'inherit',
                transition: 'all 0.3s ease',
                display: 'block'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.borderColor = 'rgba(0,245,212,0.3)'
                e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div style={{ fontSize: '40px' }}>{doc.icon}</div>
                <span style={{ 
                  background: 'rgba(0,245,212,0.1)', 
                  color: '#00F5D4', 
                  padding: '4px 12px', 
                  borderRadius: '20px', 
                  fontSize: '12px',
                  fontWeight: 500
                }}>{doc.tag}</span>
              </div>
              <h3 style={{ fontSize: '22px', fontWeight: 600, marginBottom: '12px', color: '#fff' }}>{doc.title}</h3>
              <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, marginBottom: '20px' }}>{doc.description}</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#00F5D4', fontSize: '14px', fontWeight: 500 }}>
                <span>Download PDF</span>
                <span>↓</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Additional Resources */}
      <section style={{ padding: '80px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '20px' }}>Need More Help?</h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>
            Our team is here to help you get the most out of Quathera.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', flexWrap: 'wrap' }}>
            <a href="mailto:support@quathera.com" style={{ 
              background: 'rgba(255,255,255,0.05)', 
              border: '1px solid rgba(255,255,255,0.1)', 
              borderRadius: '12px', 
              padding: '20px 32px',
              textDecoration: 'none',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ fontSize: '24px' }}>📧</span>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '16px', fontWeight: 600 }}>Email Support</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)' }}>support@quathera.com</div>
              </div>
            </a>
            <Link href="/faq" style={{ 
              background: 'rgba(255,255,255,0.05)', 
              border: '1px solid rgba(255,255,255,0.1)', 
              borderRadius: '12px', 
              padding: '20px 32px',
              textDecoration: 'none',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ fontSize: '24px' }}>❓</span>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '16px', fontWeight: 600 }}>FAQ</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)' }}>Common questions answered</div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '100px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <h2 style={{ fontSize: '36px', fontWeight: 700, marginBottom: '20px' }}>Ready to Get Started?</h2>
        <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>Start your free 14-day trial today. No credit card required.</p>
        <Link href="/signup" style={{ display: 'inline-block', background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '18px 40px', borderRadius: '10px', fontWeight: 700, fontSize: '18px', textDecoration: 'none' }}>Start Free Trial →</Link>
      </section>

      {/* Footer */}
      <footer style={{ padding: '40px 60px', borderTop: '1px solid rgba(255,255,255,0.05)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <QuatheraLogo size={28} />
            <span style={{ fontSize: '16px', fontWeight: 600, color: 'rgba(255,255,255,0.8)' }}>QUATHERA</span>
          </div>
          <div style={{ display: 'flex', gap: '32px' }}>
            <Link href="/products" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Products</Link>
            <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Pricing</Link>
            <Link href="/docs" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Documentation</Link>
            <Link href="/faq" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>FAQ</Link>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px', margin: 0 }}>© 2025 Quathera. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
