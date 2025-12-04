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

const steps = [
  {
    num: '01',
    title: 'Sign Up & Create Project',
    description: 'Create your account in seconds. Then create a project for your web application. Invite team members to collaborate.',
    details: ['No credit card required', 'Unlimited team members on paid plans', 'All users in your company see shared projects']
  },
  {
    num: '02',
    title: 'Download & Install Agent',
    description: 'Download our lightweight desktop agent. Available for Windows, Mac, and Linux. Install it on your machine or a dedicated test server.',
    details: ['One-click installation', 'Runs securely on your infrastructure', 'Your credentials never leave your network']
  },
  {
    num: '03',
    title: 'Configure Test Sites',
    description: 'Set up test sites for each user type (Admin, Regular User, etc.) across your environments. AI discovers forms on QA, then runs tests on QA, Staging, or Production.',
    details: ['Multiple user types per project', 'QA / Staging / Production environments', 'Login pages with credentials or public pages', 'Secure local credential storage']
  },
  {
    num: '04',
    title: 'AI Discovers All Forms',
    description: 'Click one button. AI automatically crawls your entire QA environment, logs in as each user type, and discovers every form — no manual navigation needed.',
    details: ['Fully automatic crawling', 'Handles all user types automatically', 'Finds hidden and dynamic forms', 'Zero manual effort required']
  },
  {
    num: '05',
    title: 'AI Maps Every Field',
    description: 'AI automatically analyzes each discovered form. It maps all fields, detects conditional paths, compares against your spec, and flags discrepancies — all without your input.',
    details: ['Automatic deep analysis', 'Junction paths auto-detected', 'Spec drift caught automatically', 'No manual mapping needed']
  },
  {
    num: '06',
    title: 'AI Runs & Heals Tests',
    description: 'AI automatically executes tests, runs full Create → Verify → Edit → Verify cycles, catches visual issues, and self-heals broken locators — completely hands-free.',
    details: ['One-click test execution', 'Auto-heals broken locators', 'Visual issues caught automatically', 'Screenshots captured on failures']
  },
  {
    num: '07',
    title: 'AI Reports Everything',
    description: 'AI automatically generates detailed reports with bugs, actual vs expected diffs, test coverage matrix, and Jira tickets — ready for you to review.',
    details: ['Auto-generated bug reports', 'Coverage matrix updated automatically', 'Jira tickets created automatically', 'Just review the results']
  }
]

export default function HowItWorks() {
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
          <Link href="/how-it-works" style={{ color: '#00F5D4', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>How It Works</Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Pricing</Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Login</Link>
          <Link href="/signup" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '12px 24px', borderRadius: '8px', fontWeight: 600, fontSize: '14px', textDecoration: 'none' }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '120px 60px 80px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <h1 style={{ fontSize: '56px', fontWeight: 700, marginBottom: '24px' }}>
          From Zero to Testing <span style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>in Minutes</span>
        </h1>
        <p style={{ fontSize: '20px', color: 'rgba(255,255,255,0.6)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.7 }}>
          No scripting. No coding. Just point Quathera at your app and let AI do the work.
        </p>
      </section>

      {/* Steps */}
      <section style={{ padding: '40px 60px 120px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: '40px', marginBottom: '60px', alignItems: 'flex-start' }}>
              {/* Number */}
              <div style={{
                width: '80px', height: '80px', borderRadius: '20px',
                background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '28px', fontWeight: 700, color: '#0A0E17', flexShrink: 0
              }}>{step.num}</div>
              
              {/* Content */}
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '12px' }}>{step.title}</h3>
                <p style={{ fontSize: '17px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.7, marginBottom: '20px' }}>{step.description}</p>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {step.details.map((d, j) => (
                    <li key={j} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0', fontSize: '15px', color: 'rgba(255,255,255,0.5)' }}>
                      <span style={{ color: '#00F5D4', fontSize: '12px' }}>●</span> {d}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* What Happens After */}
      <section style={{ padding: '100px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '36px', fontWeight: 700, marginBottom: '20px' }}>What Happens When Tests Run?</h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '60px', maxWidth: '700px', margin: '0 auto 60px' }}>
            Our AI handles everything automatically - from test execution to bug reporting.
          </p>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px' }}>
            {[
              { icon: '✅', title: 'Tests Pass', desc: 'Results logged, metrics updated, ready for next run' },
              { icon: '🔄', title: 'Locator Breaks', desc: 'AI auto-detects and fixes the broken locator' },
              { icon: '🐛', title: 'Real Bug Found', desc: 'Auto-creates Jira ticket with full context' },
              { icon: '🔁', title: 'Regression Detected', desc: 'AI identifies if a closed bug has returned' },
              { icon: '⚠️', title: 'Network Error', desc: 'Captures server/frontend errors for debugging' },
              { icon: '📊', title: 'Analytics Updated', desc: 'Trends and quality metrics tracked over time' }
            ].map((item, i) => (
              <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '30px', textAlign: 'center' }}>
                <div style={{ fontSize: '36px', marginBottom: '16px' }}>{item.icon}</div>
                <h4 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>{item.title}</h4>
                <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', margin: 0, lineHeight: 1.5 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>See It In Action</h2>
        <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>Start your free trial and discover every form in your app today.</p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
          <Link href="/signup" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '18px 40px', borderRadius: '10px', fontWeight: 700, fontSize: '18px', textDecoration: 'none' }}>Start Free Trial →</Link>
          <Link href="/products" style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', padding: '18px 40px', borderRadius: '10px', fontWeight: 600, fontSize: '18px', textDecoration: 'none' }}>View Features</Link>
        </div>
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
