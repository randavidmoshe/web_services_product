'use client'
import { useState } from 'react'
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

// Feature Card with hover expand effect
const FeatureCard = ({ feature }: { feature: { icon: string; title: string; subtitle: string; description: string; bullets: string[] } }) => {
  const [isHovered, setIsHovered] = useState(false)
  
  return (
    <div 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ 
        background: isHovered ? 'rgba(0,245,212,0.08)' : 'rgba(255,255,255,0.03)', 
        border: isHovered ? '1px solid rgba(0,245,212,0.4)' : '1px solid rgba(255,255,255,0.08)', 
        borderRadius: '20px', 
        padding: isHovered ? '50px' : '40px',
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        boxShadow: isHovered ? '0 20px 60px rgba(0,245,212,0.15)' : 'none',
        zIndex: isHovered ? 10 : 1,
        position: 'relative',
        cursor: 'pointer'
      }}
    >
      <div style={{ 
        fontSize: isHovered ? '56px' : '48px', 
        marginBottom: '20px',
        transition: 'all 0.4s ease'
      }}>{feature.icon}</div>
      <div style={{ 
        fontSize: '13px', 
        color: '#00F5D4', 
        textTransform: 'uppercase', 
        letterSpacing: '2px', 
        marginBottom: '8px' 
      }}>{feature.subtitle}</div>
      <h3 style={{ 
        fontSize: isHovered ? '32px' : '28px', 
        fontWeight: 700, 
        marginBottom: '16px',
        transition: 'all 0.4s ease'
      }}>{feature.title}</h3>
      <p style={{ 
        fontSize: isHovered ? '17px' : '16px', 
        color: 'rgba(255,255,255,0.6)', 
        lineHeight: 1.7, 
        marginBottom: '24px',
        transition: 'all 0.4s ease'
      }}>{feature.description}</p>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {feature.bullets.map((b, j) => (
          <li key={j} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px', 
            padding: isHovered ? '10px 0' : '8px 0', 
            fontSize: isHovered ? '16px' : '15px', 
            color: isHovered ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.7)',
            transition: 'all 0.4s ease'
          }}>
            <span style={{ color: '#00F5D4' }}>✓</span> {b}
          </li>
        ))}
      </ul>
    </div>
  )
}

const features = [
  {
    icon: '🔍',
    title: 'AI Form Discovery',
    subtitle: 'Find Every Form Automatically',
    description: 'Our AI-powered crawler navigates your entire web application, discovering every form page - login screens, registration, data entry, multi-step wizards.',
    bullets: ['Automatic login handling', 'Discovers hidden forms', 'Handles SPAs & iframes', 'Works with any framework']
  },
  {
    icon: '🗺️',
    title: 'Intelligent Form Mapping',
    subtitle: 'Deep Field Analysis',
    description: 'Each form is thoroughly analyzed. AI maps every field, understands conditional logic, detects validation rules, and identifies form relationships.',
    bullets: ['Maps all field types', 'Discovers junction paths', 'Parent-child relationships', 'Multi-user workflows']
  },
  {
    icon: '🌐',
    title: 'Multi-Environment Test Sites',
    subtitle: 'QA, Staging & Production',
    description: 'Configure test sites for different user types across multiple environments. AI discovers forms on QA, then run tests on any environment.',
    bullets: ['Multiple user types (Admin, Regular)', 'QA/Staging/Production support', 'Login or no-login pages', 'Credentials stored securely']
  },
  {
    icon: '⚡',
    title: 'Auto Test Generation',
    subtitle: 'Complete Test Scenarios',
    description: 'Automatically generates comprehensive test scenarios covering the full lifecycle: Create → Verify → Edit → Verify, plus negative tests for validation.',
    bullets: ['Full CRUD coverage', 'Negative test cases', 'Junction path variations', 'Multi-user privilege tests']
  },
  {
    icon: '🔄',
    title: 'Self-Healing Tests',
    subtitle: 'Tests That Fix Themselves',
    description: 'When UI changes break locators, AI automatically detects and fixes them. Your tests adapt to change instead of failing.',
    bullets: ['Auto-fix broken locators', 'Adapts to UI changes', 'Reduces maintenance 80%', 'Network error handling']
  },
  {
    icon: '👁️',
    title: 'Visual Verification',
    subtitle: 'Catch Visual Bugs Automatically',
    description: 'AI performs visual verification during discovery and test runs. Detect layout issues, styling problems, and visual regressions before users do.',
    bullets: ['Layout issue detection', 'Visual regression alerts', 'Screenshot comparisons', 'CSS anomaly detection']
  },
  {
    icon: '📋',
    title: 'Spec vs Discovery',
    subtitle: 'Catch Undocumented Changes',
    description: 'AI compares what your spec says against what it actually discovers. Identifies spec drift, missing documentation, and unexpected changes.',
    bullets: ['Spec drift detection', 'Missing field alerts', 'Undocumented changes', 'Automatic spec updates']
  },
  {
    icon: '📊',
    title: 'Test Coverage Matrix',
    subtitle: 'Track Quality Across Versions',
    description: 'Visual dashboard showing test pass/fail status by version. Color-coded cells (green/orange/red) give instant quality insights.',
    bullets: ['Version-by-version tracking', 'Color-coded results', 'Historical trends', 'Export reports']
  },
  {
    icon: '🐛',
    title: 'Smart Jira Integration',
    subtitle: 'Intelligent Bug Management',
    description: 'Automatically creates bugs in Jira when tests fail. AI detects duplicates before filing and identifies regressions when closed bugs reappear.',
    bullets: ['Auto bug creation', 'Duplicate detection', 'Regression identification', 'Screenshots attached']
  },
  {
    icon: '📝',
    title: 'Dual View Logs',
    subtitle: 'Agent & Web App Visibility',
    description: 'Complete test logs available on both Desktop Agent and Web App. See running scenarios, bugs found, healing actions, and network errors.',
    bullets: ['Agent-side logs', 'Web app logs', 'Actual vs expected diffs', 'Sniffer error capture']
  }
]

export default function Products() {
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
          <Link href="/products" style={{ color: '#00F5D4', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>Products</Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>How It Works</Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Pricing</Link>
          <Link href="/docs" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Docs</Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Login</Link>
          <Link href="/signup" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '12px 24px', borderRadius: '8px', fontWeight: 600, fontSize: '14px', textDecoration: 'none' }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '120px 60px 80px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <h1 style={{ fontSize: '56px', fontWeight: 700, marginBottom: '24px' }}>
          Complete AI-Powered <span style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Testing Platform</span>
        </h1>
        <p style={{ fontSize: '20px', color: 'rgba(255,255,255,0.6)', maxWidth: '700px', margin: '0 auto', lineHeight: 1.7 }}>
          From automatic form discovery to self-healing test execution - Quathera handles the complete testing lifecycle.
        </p>
      </section>

      {/* Features Grid */}
      <section style={{ padding: '40px 60px 120px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '40px' }}>
          {features.map((f, i) => (
            <FeatureCard key={i} feature={f} />
          ))}
        </div>
      </section>

      {/* Browser Support */}
      <section style={{ padding: '80px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '16px' }}>Multi-Browser Support</h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>Run tests across all major browsers with a single click</p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '60px' }}>
            {[{ name: 'Chrome', icon: '🌐' }, { name: 'Firefox', icon: '🦊' }, { name: 'Edge', icon: '🔷' }, { name: 'Electron', icon: '⚡' }].map((b, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '48px', marginBottom: '12px' }}>{b.icon}</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)' }}>{b.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>Ready to Get Started?</h2>
        <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>Start your free 14-day trial. No credit card required.</p>
        <Link href="/signup" style={{ display: 'inline-block', background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '18px 40px', borderRadius: '10px', fontWeight: 700, fontSize: '18px', textDecoration: 'none' }}>Start Free Trial →</Link>
      </section>

      {/* Footer */}
      <footer style={{ padding: '40px 60px', borderTop: '1px solid rgba(255,255,255,0.05)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <QuatheraLogo size={28} />
            <span style={{ fontSize: '16px', fontWeight: 600, color: 'rgba(255,255,255,0.8)' }}>QUATHERA</span>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px', margin: 0 }}>© 2025 Quathera. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
