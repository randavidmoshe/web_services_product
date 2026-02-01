'use client'
import { useState } from 'react'
import Link from 'next/link'

const QuatheraLogo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{ stopColor: '#00F5D4' }} />
        <stop offset="50%" style={{ stopColor: '#00BBF9' }} />
        <stop offset="100%" style={{ stopColor: '#9B5DE5' }} />
      </linearGradient>
    </defs>
    <g transform="translate(50, 50)">
      <circle cx="0" cy="0" r="35" fill="none" stroke="url(#logoGrad)" strokeWidth="3" />
      <g stroke="url(#logoGrad)" strokeWidth="2" fill="none" strokeLinecap="round">
        <path d="M-15 -10 Q0 -25 15 -10" />
        <path d="M-18 5 Q0 20 18 5" />
        <path d="M-8 -18 Q0 -10 8 -18" />
      </g>
      <circle cx="0" cy="0" r="6" fill="url(#logoGrad)" opacity="0.6" />
    </g>
  </svg>
)

const FeatureCard = ({ feature }: { feature: any }) => {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: isHovered
          ? 'linear-gradient(135deg, rgba(0,245,212,0.08), rgba(155,93,229,0.08))'
          : 'rgba(255,255,255,0.02)',
        border: isHovered ? '1px solid rgba(0,245,212,0.35)' : '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
        padding: isHovered ? '34px' : '32px',
        transition: 'all 0.35s ease',
        transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14 }}>
        <div style={{ fontSize: '42px', marginBottom: '16px' }}>{feature.icon}</div>
        {feature.stageBadge && (
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              padding: '6px 10px',
              borderRadius: 999,
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(0,0,0,0.22)',
              color: 'rgba(255,255,255,0.75)',
              whiteSpace: 'nowrap',
            }}
          >
            {feature.stageBadge}
          </div>
        )}
      </div>

      <h3
        style={{
          fontSize: '24px',
          fontWeight: 700,
          marginBottom: '6px',
          background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        {feature.title}
      </h3>

      <p style={{ fontSize: '16px', color: 'rgba(255,255,255,0.6)', marginBottom: '18px' }}>
        {feature.subtitle}
      </p>

      <p
        style={{
          fontSize: isHovered ? '17px' : '16px',
          color: 'rgba(255,255,255,0.6)',
          lineHeight: 1.7,
          marginBottom: '24px',
          transition: 'all 0.35s ease',
        }}
      >
        {feature.description}
      </p>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {feature.bullets.map((b: string, j: number) => (
          <li
            key={j}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: isHovered ? '10px 0' : '8px 0',
              fontSize: isHovered ? '16px' : '15px',
              color: isHovered ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.7)',
              transition: 'all 0.35s ease',
            }}
          >
            <span style={{ color: '#00F5D4' }}>✓</span> {b}
          </li>
        ))}
      </ul>
    </div>
  )
}

const progression = [
  { title: 'Discover & Map', badge: 'Available now (Beta)' },
  { title: 'Generate Scenarios', badge: 'Expanding' },
  { title: 'Execute & Validate', badge: 'Expanding' },
]

const features = [
  // Discover & Map (Available now)
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '🔍',
    title: 'AI Form Discovery',
    subtitle: 'Find Every Form Automatically',
    description:
      'AI navigates your application to discover form pages and workflow entry points — including multi-step flows and gated areas.',
    bullets: ['Automatic discovery', 'Handles SPAs & iframes', 'Works with any framework', 'Supports login flows'],
  },
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '🗺️',
    title: 'Intelligent Form Mapping',
    subtitle: 'Hierarchy + Conditional Paths',
    description:
      'Maps fields, relationships, parent/child hierarchy, and conditional options that reveal new inputs — building a blueprint of the workflow.',
    bullets: ['Field & rule understanding', 'Parent/child mapping', 'Conditional/nested paths', 'Workflow structure export'],
  },
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '🌐',
    title: 'Multi-Environment Setup',
    subtitle: 'QA, Staging & Production',
    description:
      'Configure environments and user types so teams can map and validate behavior where it matters.',
    bullets: ['Multiple user types', 'QA/Staging/Prod support', 'Login or no-login pages', 'Credentials handled securely'],
  },
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '🧾',
    title: 'Structured Output',
    subtitle: 'POM / Objects & Paths',
    description:
      'Export structured artifacts from mapping to accelerate automation work and product alignment.',
    bullets: ['POM export', 'Reusable objects', 'Scenario-ready paths', 'Shareable outputs'],
  },
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '📋',
    title: 'Spec Alignment',
    subtitle: 'Spec vs Reality',
    description:
      'Compare discovered/mapped flows to a provided spec to surface drift, missing requirements, and unexpected behavior.',
    bullets: ['Spec drift detection', 'Missing field alerts', 'Unexpected flow flags', 'Useful for PMs too'],
  },
  {
    stage: 'discover',
    stageBadge: 'Available now (Beta)',
    icon: '🎨',
    title: 'Figma Alignment',
    subtitle: 'Design vs Reality',
    description:
      'Upload design artifacts (e.g., Figma) and compare them to real UI states captured during mapping to help product teams spot gaps faster.',
    bullets: ['PM-friendly workflow', 'Visual evidence from mapping', 'Spot gaps & drift', 'Shareable findings'],
  },

  // Generate Scenarios (Expanding)
  {
    stage: 'scenarios',
    stageBadge: 'Expanding',
    icon: '⚡',
    title: 'Scenario Generation',
    subtitle: 'From Blueprint to Scenarios',
    description:
  'Generate concrete, runnable test scenarios from mapped flows and specifications—designed to scale into full execution.',
    bullets: [
      'End-to-end scenarios',
      'Positive & negative coverage',
      'API positive & negative tests',
      'Multiple paths per workflow',
      'User-defined custom scenarios',
    ],
  },


  {
    stage: 'scenarios',
    stageBadge: 'Expanding',
    icon: '📝',
    title: 'Observability Layer',
    subtitle: 'Agent + Web App Visibility',
    description:
      'Agent captures key signals during mapping and guided validation (including network activity) to help teams debug faster.',
    bullets: ['Agent-side visibility', 'Web app logs', 'Network capture (early)', 'Server-side error hints'],
  },

  // Execute & Validate (Planned)
  {
    stage: 'execute',
    stageBadge: 'Expanding',
    icon: '👁️',
    title: 'Visual Verification',
    subtitle: 'Validate Outcomes Visually',
    description:
      'During execution, validate outcomes visually step-by-step (ideal for highly interactive and stateful UIs).',
    bullets: ['Execution-time verification', 'Step-by-step visual checks', 'Dynamic UI flows', 'Designed to scale'],
  },
  {
    stage: 'execute',
    stageBadge: 'Planned',
    icon: '▶️',
    title: 'Test Execution',
    subtitle: 'Run Scenarios End-to-End',
    description:
      'Execute generated scenarios against your application and validate outcomes using the mapping blueprint and visual verification.',
    bullets: [
      'Run per user request',
      'Uses mapped blueprint',
      'Pairs with visual verification',
      'Planned capability',
    ],
  },

  {
    stage: 'execute',
    stageBadge: 'Planned',
    icon: '🔄',
    title: 'Self-Healing Execution',
    subtitle: 'Execution-Grade Resilience',
    description:
      'Execution features build on top of the mapping blueprint — enabling resilient runs that adapt as the UI changes.',
    bullets: ['Built on mapping blueprint', 'Resilient execution layer', 'Designed to reduce brittle suites', 'Planned capability'],
  },
  {
    stage: 'execute',
    stageBadge: 'Planned',
    icon: '🧷',
    title: 'Locator Correction',
    subtitle: 'Stability During Runs',
    description:
      'Locator fixes belong to test execution: as scenarios run, the system can correct selectors and keep automation stable.',
    bullets: ['During execution', 'Correct selectors automatically', 'Reduce manual maintenance', 'Planned capability'],
  },
  {
    stage: 'execute',
    stageBadge: 'Planned',
    icon: '🐛',
    title: 'Issue & Workflow Integrations',
    subtitle: 'Jira and Beyond',
    description:
      'Integrations and workflow automation are planned as execution capabilities mature.',
    bullets: ['Jira workflows', 'Attachments & context', 'Duplicate awareness', 'Planned capability'],
  },
]

function StageHeader({ title, badge }: { title: string; badge: string }) {
  return (
    <div
      style={{
        maxWidth: '1200px',
        margin: '0 auto 18px',
        display: 'flex',
        alignItems: 'baseline',
        justifyContent: 'space-between',
        gap: 16,
      }}
    >
      <h2 style={{ fontSize: '22px', fontWeight: 800, margin: 0 }}>{title}</h2>
      <span
        style={{
          fontSize: 12,
          fontWeight: 800,
          padding: '6px 10px',
          borderRadius: 999,
          border: '1px solid rgba(255,255,255,0.12)',
          background: 'rgba(255,255,255,0.06)',
          color: 'rgba(255,255,255,0.75)',
          whiteSpace: 'nowrap',
        }}
      >
        {badge}
      </span>
    </div>
  )
}

function ProgressionBlock() {
  return (
    <div
      style={{
        maxWidth: '920px',
        margin: '26px auto 26px',
        padding: '18px',
        borderRadius: '14px',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
      }}
    >
      <div style={{ display: 'flex', gap: 14, justifyContent: 'space-between', flexWrap: 'wrap' }}>
        {progression.map((step, index) => (
          <div
            key={step.title}
            style={{
              flex: '1 1 240px',
              minWidth: 240,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              padding: '12px 14px',
              borderRadius: '12px',
              background: 'rgba(0,0,0,0.18)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <div>
              <div style={{ fontWeight: 800, color: '#fff', fontSize: 14 }}>{step.title}</div>
              <div style={{ marginTop: 6, fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{step.badge}</div>
            </div>
            {index !== 2 && <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 18, fontWeight: 900 }}>→</div>}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12, fontSize: 13, color: 'rgba(255,255,255,0.68)', lineHeight: 1.5 }}>
        Mapping builds the blueprint (pages, hierarchy, paths). Scenarios define what to test. Execution runs and validates those scenarios end-to-end.
      </div>
    </div>
  )
}

function StageBand({
  title,
  badge,
  description,
  bandStyle,
  children,
}: {
  title: string
  badge: string
  description: string
  bandStyle?: React.CSSProperties
  children: React.ReactNode
}) {
  return (
    <section
      style={{
        padding: '46px 60px',
        position: 'relative',
        zIndex: 1,
        ...bandStyle,
      }}
    >
      <StageHeader title={title} badge={badge} />
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto 18px',
          color: 'rgba(255,255,255,0.62)',
          fontSize: 15,
          lineHeight: 1.6,
        }}
      >
        {description}
      </div>
      {children}
    </section>
  )
}

export default function Products() {
  const discover = features.filter((f) => f.stage === 'discover')
  const scenarios = features.filter((f) => f.stage === 'scenarios')
  const execute = features.filter((f) => f.stage === 'execute')

  return (
    <div style={{ minHeight: '100vh', background: '#0A0E17', color: '#fff', fontFamily: "'SF Pro Display', 'Segoe UI', sans-serif" }}>
      {/* Background */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage:
            'linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          pointerEvents: 'none',
        }}
      />

      {/* Nav */}
      <nav
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 60px',
          background: 'rgba(10,14,23,0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          position: 'relative',
          zIndex: 10,
        }}
      >
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
          <QuatheraLogo />
          <span
            style={{
              fontSize: '22px',
              fontWeight: 600,
              letterSpacing: '2px',
              background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            QUATTERA.ai
          </span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/products" style={{ color: '#00F5D4', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>
            Products
          </Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>
            How It Works
          </Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>
            Pricing
          </Link>
          <Link href="/docs" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>
            Docs
          </Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>
            Login
          </Link>
          <Link
            href="/signup"
            style={{
              background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
              color: '#0A0E17',
              padding: '12px 24px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '14px',
              textDecoration: 'none',
            }}
          >
            Request Early Access
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '110px 60px 50px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px 14px',
            borderRadius: '999px',
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.12)',
            marginBottom: '22px',
            fontSize: '14px',
            fontWeight: 700,
            letterSpacing: '0.2px',
            color: 'rgba(255,255,255,0.85)',
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: 999, background: '#34d399', display: 'inline-block' }} />
          Private Beta · Limited early access
        </div>

        <h1 style={{ fontSize: '56px', fontWeight: 700, marginBottom: '18px' }}>
          AI-Powered <span style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Web Mapping</span> for Testing
        </h1>

        <p style={{ fontSize: '20px', color: 'rgba(255,255,255,0.62)', maxWidth: '820px', margin: '0 auto', lineHeight: 1.7 }}>
          Quattera is built for two realities: enterprise apps full of forms and workflows, and dynamic consumer-style web apps.
          Choose your project type in the app after login.
        </p>

        <ProgressionBlock />

        <div style={{ display: 'flex', justifyContent: 'center', gap: 14, flexWrap: 'wrap', marginTop: 10 }}>
          <Link
            href="/signup"
            style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
              color: '#0A0E17',
              padding: '14px 28px',
              borderRadius: '10px',
              fontWeight: 800,
              fontSize: '16px',
              textDecoration: 'none',
            }}
          >
            Request Early Access →
          </Link>
          <Link
            href="/how-it-works"
            style={{
              display: 'inline-block',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.18)',
              color: '#fff',
              padding: '14px 28px',
              borderRadius: '10px',
              fontWeight: 800,
              fontSize: '16px',
              textDecoration: 'none',
            }}
          >
            How it works
          </Link>
        </div>
      </section>

      {/* Two markets (simple, no confusion) */}
      <section style={{ padding: '0 60px 40px', position: 'relative', zIndex: 1 }}>
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 18,
          }}
        >
          <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, padding: 20, background: 'rgba(255,255,255,0.02)' }}>
            <div style={{ fontSize: 34, marginBottom: 10 }}>🏢</div>
            <div style={{ fontWeight: 900, marginBottom: 6 }}>Form-heavy enterprise apps</div>
            <div style={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
              Automatic discovery and deep mapping of form workflows (hierarchy, conditional fields, paths).
            </div>
          </div>
          <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, padding: 20, background: 'rgba(255,255,255,0.02)' }}>
            <div style={{ fontSize: 34, marginBottom: 10 }}>🎬</div>
            <div style={{ fontWeight: 900, marginBottom: 6 }}>Dynamic web apps</div>
            <div style={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
              Guided scenarios with visual verification for highly interactive, stateful UIs.
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid (banded by stage) */}
    <StageBand
      title="Discover & Map"
      badge="Available now (Beta)"
      description="Automatically discover and map form-heavy workflows into a structured blueprint: pages, hierarchy, fields, and paths."
      bandStyle={{
        background: 'rgba(255,255,255,0.015)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '40px',
        }}
      >
        {discover.map((f, i) => (
          <FeatureCard key={`d-${i}`} feature={f} />
        ))}
      </div>
    </StageBand>

    <StageBand
      title="Generate Scenarios"
      badge="Expanding"
      description="Turn the blueprint into concrete test scenarios—covering end-to-end flows, positive and negative cases, API interactions, and user-defined paths."
      bandStyle={{
        background: 'rgba(0,0,0,0.12)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '40px',
        }}
      >
        {scenarios.map((f, i) => (
          <FeatureCard key={`s-${i}`} feature={f} />
        ))}
      </div>
    </StageBand>

    <StageBand
      title="Execute & Validate"
      badge="Expanding"
      description="Run scenarios and validate outcomes. This layer includes visual verification today and expands into execution reliability features."
      bandStyle={{
        background: 'rgba(255,255,255,0.01)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '40px',
        }}
      >
        {execute.map((f, i) => (
          <FeatureCard key={`e-${i}`} feature={f} />
        ))}
      </div>
    </StageBand>

      {/* Browser Support (tone-safe) */}
      <section style={{ padding: '100px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '16px' }}>Multi-Browser Support</h2>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px' }}>
            Run mapping and guided verification across major browsers
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '60px', flexWrap: 'wrap' }}>
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
      <section style={{ padding: '110px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 700, marginBottom: '20px' }}>Request Early Access</h2>
        <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '40px', maxWidth: 760, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.7 }}>
          Join the private beta and help shape the platform with direct feedback loops.
        </p>
        <Link
          href="/signup"
          style={{
            display: 'inline-block',
            background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
            color: '#0A0E17',
            padding: '18px 40px',
            borderRadius: '10px',
            fontWeight: 900,
            fontSize: '18px',
            textDecoration: 'none',
          }}
        >
          Request Early Access →
        </Link>
      </section>

      {/* Footer */}
      <footer style={{ padding: '40px 60px', borderTop: '1px solid rgba(255,255,255,0.05)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <QuatheraLogo size={28} />
            <span style={{ fontSize: '16px', fontWeight: 700, color: 'rgba(255,255,255,0.85)' }}>QUATTERA.ai</span>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '14px', margin: 0 }}>© 2026 Quattera.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}