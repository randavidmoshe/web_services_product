'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'

// Quathera Logo Component
const QuatheraLogo = ({ size = 50 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
        <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
        <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
      </linearGradient>
      <filter id="logoGlow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <g transform="translate(50, 50)">
      <circle cx="0" cy="0" r="35" fill="none" stroke="url(#logoGradient)" strokeWidth="3" filter="url(#logoGlow)"/>
      <g stroke="url(#logoGradient)" strokeWidth="2" fill="none" strokeLinecap="round" filter="url(#logoGlow)">
        <path d="M -22 -12 Q -28 0 -24 12 Q -18 26 0 30 Q 18 26 24 12 Q 28 0 22 -12 Q 14 -28 0 -30 Q -14 -28 -22 -12"/>
        <path d="M 16 18 L 32 34 L 42 30"/>
        <circle cx="42" cy="30" r="3" fill="url(#logoGradient)"/>
      </g>
      <g fill="url(#logoGradient)" filter="url(#logoGlow)">
        <circle cx="-24" cy="-10" r="3"/>
        <circle cx="-25" cy="10" r="3"/>
        <circle cx="0" cy="30" r="3"/>
        <circle cx="24" cy="10" r="3"/>
        <circle cx="24" cy="-10" r="3"/>
        <circle cx="0" cy="-30" r="3"/>
      </g>
      <circle cx="0" cy="0" r="5" fill="#0A0E17" stroke="url(#logoGradient)" strokeWidth="1.5"/>
      <circle cx="0" cy="0" r="2" fill="url(#logoGradient)"/>
    </g>
  </svg>
)

// Stat Component
const StatItem = ({ value, label }: { value: string; label: string }) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{
      fontSize: '48px',
      fontWeight: 700,
      background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      marginBottom: '8px'
    }}>{value}</div>
    <div style={{
      fontSize: '14px',
      color: 'rgba(255,255,255,0.6)',
      textTransform: 'uppercase',
      letterSpacing: '1px'
    }}>{label}</div>
  </div>
)

export default function HomePage() {
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    setIsVisible(true)
  }, [])

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#0A0E17',
      color: '#fff',
      fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
    }}>
      {/* Background Grid */}
      <div style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: `
          linear-gradient(rgba(0, 245, 212, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 245, 212, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
        pointerEvents: 'none',
        zIndex: 0
      }} />

      {/* Gradient Orbs */}
      <div style={{
        position: 'fixed', top: '-20%', right: '-10%',
        width: '600px', height: '600px',
        background: 'radial-gradient(circle, rgba(0, 187, 249, 0.15) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none', zIndex: 0
      }} />
      <div style={{
        position: 'fixed', bottom: '-30%', left: '-10%',
        width: '800px', height: '800px',
        background: 'radial-gradient(circle, rgba(155, 93, 229, 0.1) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none', zIndex: 0
      }} />

      {/* Navigation */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '20px 60px',
        background: 'rgba(10, 14, 23, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        zIndex: 1000
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
          <QuatheraLogo size={40} />
          <span style={{ 
            fontSize: '22px', fontWeight: 600, letterSpacing: '2px',
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>QUATHERA</span>
        </Link>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/products" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>Products</Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>How It Works</Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>Pricing</Link>
          <Link href="/docs" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>Docs</Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>Login</Link>
          <Link href="/signup" style={{
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
            color: '#0A0E17', padding: '12px 24px', borderRadius: '8px',
            fontWeight: 600, fontSize: '14px', textDecoration: 'none'
          }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center', textAlign: 'center',
        padding: '140px 60px 80px', position: 'relative', zIndex: 1
      }}>
        {/* Badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          background: 'rgba(0, 245, 212, 0.1)',
          border: '1px solid rgba(0, 245, 212, 0.3)',
          borderRadius: '50px', padding: '8px 20px', marginBottom: '32px',
          opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.6s ease'
        }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00F5D4' }} />
          <span style={{ color: '#00F5D4', fontSize: '14px', fontWeight: 500 }}>
            Now with AI Vision &amp; Smart Crawling
          </span>
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: '72px', fontWeight: 700, lineHeight: 1.1, marginBottom: '24px', maxWidth: '900px',
          opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
          transition: 'all 0.6s ease 0.1s'
        }}>
          AI-Powered<br />
          <span style={{
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>Test Automation</span>
        </h1>

        {/* Subheadline */}
        <p style={{
          fontSize: '20px', color: 'rgba(255,255,255,0.7)', maxWidth: '650px',
          lineHeight: 1.7, marginBottom: '48px',
          opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
          transition: 'all 0.6s ease 0.2s'
        }}>
          Quathera automatically discovers every form in your web application, 
          maps all fields and paths, generates complete test scenarios, and 
          runs self-healing tests. No scripting required.
        </p>

        {/* CTA Buttons */}
        <div style={{
          display: 'flex', gap: '16px', marginBottom: '80px',
          opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
          transition: 'all 0.6s ease 0.3s'
        }}>
          <Link href="/signup" style={{
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
            color: '#0A0E17', padding: '16px 32px', borderRadius: '8px',
            fontWeight: 600, fontSize: '16px', textDecoration: 'none',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}>
            Start Free Trial <span>→</span>
          </Link>
          <Link href="/how-it-works" style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff', padding: '16px 32px', borderRadius: '8px',
            fontWeight: 600, fontSize: '16px', textDecoration: 'none'
          }}>
            Watch Demo
          </Link>
        </div>

        {/* Stats */}
        <div style={{
          display: 'flex', gap: '80px',
          opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
          transition: 'all 0.6s ease 0.4s'
        }}>
          <StatItem value="10x" label="Faster Testing" />
          <StatItem value="95%" label="Form Detection" />
          <StatItem value="500+" label="Companies" />
          <StatItem value="24/7" label="AI Monitoring" />
        </div>
      </section>

      {/* Problem Section */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '3px', marginBottom: '16px' }}>The Problem</h2>
            <h3 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>Traditional Test Automation is Broken</h3>
            <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', maxWidth: '700px', margin: '0 auto', lineHeight: 1.7 }}>
              Companies hire armies of automation engineers who spend months writing brittle test scripts. When the UI changes, everything breaks.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
            {[
              { icon: '⏰', title: 'Months to Build', desc: 'Traditional automation takes 3-6 months to set up and requires constant maintenance' },
              { icon: '💸', title: 'Expensive Teams', desc: 'Hiring and retaining automation engineers costs $150K+ per engineer per year' },
              { icon: '🔧', title: 'Constant Breakage', desc: '80% of test failures are due to locator changes, not real bugs' }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'rgba(255, 82, 82, 0.1)',
                border: '1px solid rgba(255, 82, 82, 0.2)',
                borderRadius: '16px', padding: '32px', textAlign: 'center'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>{item.icon}</div>
                <h4 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>{item.title}</h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', lineHeight: 1.6 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, background: 'rgba(0, 245, 212, 0.02)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '3px', marginBottom: '16px' }}>The Solution</h2>
            <h3 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>AI That Does the Work For You</h3>
            <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', maxWidth: '700px', margin: '0 auto', lineHeight: 1.7 }}>
              Quathera replaces months of manual work with intelligent automation that discovers, maps, tests, and heals - automatically.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
            {[
              { icon: '🔍', title: 'AI Form Discovery', desc: 'Automatically crawls your web application and finds every form page - login forms, registration, data entry, multi-step wizards.' },
              { icon: '🗺️', title: 'Intelligent Form Mapping', desc: 'Deep analysis of each form: all fields, conditional paths, dropdown dependencies, multi-user workflows, and validation rules.' },
              { icon: '⚡', title: 'Auto Test Generation', desc: 'Generates complete test scenarios: Create → Verify → Edit → Verify cycles, plus negative tests. No scripting needed.' },
              { icon: '🔄', title: 'Self-Healing Tests', desc: 'When UI changes break locators, AI automatically detects and fixes them. Your tests adapt to change instead of breaking.' },
              { icon: '🌐', title: 'Multi-Environment Testing', desc: 'Configure test sites for different user types (Admin, Regular) across QA, Staging, and Production. AI discovers on QA, runs everywhere.' },
              { icon: '👁️', title: 'Visual Verification', desc: 'AI detects visual issues during discovery and test runs - layout problems, styling bugs, and visual regressions caught automatically.' },
              { icon: '📋', title: 'Spec vs Reality Detection', desc: 'Automatically identifies differences between your spec and what AI discovers. Catches undocumented changes and spec drift.' },
              { icon: '📊', title: 'Test Coverage Matrix', desc: 'Visual dashboard showing pass/fail by version. Track test health across releases with color-coded results.' },
              { icon: '🐛', title: 'Smart Jira Integration', desc: 'Auto-creates bugs in Jira with screenshots, detects duplicates, and identifies regressions when closed bugs reappear.' },
              { icon: '📝', title: 'Dual View Logs', desc: 'Complete logs on both Agent and Web App. See scenarios, bugs with actual vs expected, self-healing info, and network errors.' }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '16px', padding: '32px', transition: 'all 0.3s ease'
              }}>
                <div style={{ fontSize: '40px', marginBottom: '20px' }}>{item.icon}</div>
                <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px', color: '#fff' }}>{item.title}</h3>
                <p style={{ fontSize: '15px', lineHeight: 1.7, color: 'rgba(255,255,255,0.6)', margin: 0 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '3px', marginBottom: '16px' }}>How It Works</h2>
            <h3 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>From Zero to Testing in Minutes</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
            {[
              { num: '1', title: 'Create Your Project', desc: 'Sign up, create a project for your web application, and invite your team members.' },
              { num: '2', title: 'Install the Agent', desc: 'Download and install our lightweight agent on your machine or an isolated test server. Available for Windows, Mac, and Linux.' },
              { num: '3', title: 'Discover Form Pages', desc: 'Point the agent at your web app. Our AI automatically crawls and discovers every form page, handling logins and navigation.' },
              { num: '4', title: 'Map Your Forms', desc: 'For each discovered form, AI analyzes all fields, conditional paths, multi-user workflows, and generates the complete test specification.' },
              { num: '5', title: 'Run Self-Healing Tests', desc: 'Execute tests across Chrome, Firefox, Edge, or Electron. Tests automatically adapt when UI changes - no maintenance required.' }
            ].map((step, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
                <div style={{
                  width: '48px', height: '48px', borderRadius: '12px',
                  background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '20px', fontWeight: 700, color: '#0A0E17', flexShrink: 0
                }}>{step.num}</div>
                <div>
                  <h4 style={{ fontSize: '18px', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>{step.title}</h4>
                  <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, margin: 0 }}>{step.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div style={{ textAlign: 'center', marginTop: '60px' }}>
            <Link href="/signup" style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17', padding: '16px 32px', borderRadius: '8px',
              fontWeight: 600, fontSize: '16px', textDecoration: 'none'
            }}>
              Get Started Free <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, background: 'rgba(0, 245, 212, 0.02)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '3px', marginBottom: '16px' }}>Enterprise Security</h2>
            <h3 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>Your Data, Your Control</h3>
            <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', maxWidth: '700px', margin: '0 auto', lineHeight: 1.7 }}>
              The Quathera agent runs on your infrastructure. Your test data and credentials never leave your network.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
            {[
              { icon: '🔐', title: 'On-Premise Agent', desc: 'Agent runs locally - credentials stay on your machine' },
              { icon: '🔒', title: 'End-to-End Encryption', desc: 'TLS/SSL encryption for all data in transit' },
              { icon: '🛡️', title: 'Encrypted Storage', desc: 'All data encrypted at rest with AES-256' },
              { icon: '🔑', title: '2FA Authentication', desc: 'Two-factor authentication for all accounts' },
              { icon: '⏱️', title: 'Session Security', desc: 'Expiring tokens and automatic session timeout' },
              { icon: '🚫', title: 'Rate Limiting', desc: 'Protection against brute force attacks' },
              { icon: '📋', title: 'Audit Logs', desc: 'Complete audit trail of all user actions' },
              { icon: '🇪🇺', title: 'GDPR Ready', desc: 'Full compliance with data protection regulations' }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '12px', padding: '24px', textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>{item.icon}</div>
                <h4 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>{item.title}</h4>
                <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', margin: 0, lineHeight: 1.5 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Browser Support */}
      <section style={{ padding: '80px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '24px' }}>
          Supports All Major Browsers
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '48px', fontSize: '48px', opacity: 0.6 }}>
          <span title="Chrome">🌐</span>
          <span title="Firefox">🦊</span>
          <span title="Edge">🔷</span>
          <span title="Electron">⚡</span>
        </div>
      </section>

      {/* Final CTA */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <div style={{
          maxWidth: '800px', margin: '0 auto',
          background: 'linear-gradient(135deg, rgba(0, 245, 212, 0.1) 0%, rgba(155, 93, 229, 0.1) 100%)',
          border: '1px solid rgba(0, 245, 212, 0.2)',
          borderRadius: '24px', padding: '80px 60px'
        }}>
          <h2 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>Ready to Revolutionize Your Testing?</h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.7)', marginBottom: '40px', lineHeight: 1.7 }}>
            Join 500+ companies who have eliminated manual test automation. Start your free 14-day trial today.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
            <Link href="/signup" style={{
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17', padding: '16px 32px', borderRadius: '8px',
              fontWeight: 600, fontSize: '16px', textDecoration: 'none'
            }}>Start Free Trial →</Link>
            <Link href="/pricing" style={{
              background: 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.2)',
              color: '#fff', padding: '16px 32px', borderRadius: '8px',
              fontWeight: 600, fontSize: '16px', textDecoration: 'none'
            }}>View Pricing</Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '60px', borderTop: '1px solid rgba(255,255,255,0.05)',
        position: 'relative', zIndex: 1
      }}>
        <div style={{
          maxWidth: '1200px', margin: '0 auto',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <QuatheraLogo size={32} />
            <span style={{ fontSize: '18px', fontWeight: 600, color: 'rgba(255,255,255,0.8)' }}>QUATHERA</span>
          </div>
          <div style={{ display: 'flex', gap: '32px' }}>
            <Link href="/products" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Products</Link>
            <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Pricing</Link>
            <Link href="/docs" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Documentation</Link>
            <Link href="/security" style={{ color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: '14px' }}>Security</Link>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px', margin: 0 }}>© 2025 Quathera. All rights reserved. Patent Pending.</p>
        </div>
      </footer>
    </div>
  )
}
