'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'

// Quathera Logo Component
const QuatheraLogo = ({ size = 50 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{ stopColor: '#00F5D4' }} />
        <stop offset="50%" style={{ stopColor: '#00BBF9' }} />
        <stop offset="100%" style={{ stopColor: '#9B5DE5' }} />
      </linearGradient>
      <filter id="logoGlow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    {/* Main Q Shape */}
    <circle
      cx="45"
      cy="45"
      r="28"
      fill="none"
      stroke="url(#logoGradient)"
      strokeWidth="6"
      filter="url(#logoGlow)"
    />

    {/* Inner Detail */}
    <circle cx="45" cy="45" r="12" fill="url(#logoGradient)" opacity="0.3" />

    {/* Tail */}
    <path
      d="M65 65 L78 78"
      stroke="url(#logoGradient)"
      strokeWidth="6"
      strokeLinecap="round"
      filter="url(#logoGlow)"
    />

    {/* AI Dot */}
    <circle cx="45" cy="45" r="4" fill="#00F5D4" filter="url(#logoGlow)" />
  </svg>
)

const StatItem = ({ value, label }: { value: string; label: string }) => (
  <div style={{ textAlign: 'center' }}>
    <div
      style={{
        fontSize: '48px',
        fontWeight: 700,
        background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        marginBottom: '8px',
      }}
    >
      {value}
    </div>
    <div
      style={{
        fontSize: '14px',
        color: 'rgba(255,255,255,0.6)',
        fontWeight: 500,
      }}
    >
      {label}
    </div>
  </div>
)

const FeatureCard = ({
  icon,
  title,
  description,
}: {
  icon: string
  title: string
  description: string
}) => (
  <div
    style={{
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '16px',
      padding: '32px',
      transition: 'all 0.3s ease',
    }}
  >
    <div style={{ fontSize: '32px', marginBottom: '20px' }}>{icon}</div>
    <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px', color: '#fff' }}>{title}</h3>
    <p style={{ fontSize: '16px', lineHeight: 1.6, color: 'rgba(255,255,255,0.7)' }}>{description}</p>
  </div>
)

export default function Home() {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
  }, [])

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0A0E17',
        color: '#fff',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        overflowX: 'hidden',
      }}
    >
      {/* Background Effects */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            'radial-gradient(circle at 20% 30%, rgba(0, 245, 212, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 70%, rgba(155, 93, 229, 0.1) 0%, transparent 50%)',
          pointerEvents: 'none',
        }}
      />

      {/* Navigation */}
      <nav
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 60px',
          background: 'rgba(10, 14, 23, 0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          zIndex: 1000,
        }}
      >
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
          <QuatheraLogo size={40} />
          <span
            style={{
              fontSize: '22px',
              fontWeight: 600,
              letterSpacing: '2px',
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            QUATTERA.ai
          </span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
          <Link href="/products" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>
            Products
          </Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>
            How It Works
          </Link>
          <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>
            Pricing
          </Link>
          <Link href="/docs" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>
            Docs
          </Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}>
            Login
          </Link>
          <Link
            href="/signup"
            style={{
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17',
              padding: '12px 24px',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '14px',
              textDecoration: 'none',
            }}
          >
            Request Early Access
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: '140px 60px 80px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(0, 245, 212, 0.1)',
            border: '1px solid rgba(0, 245, 212, 0.3)',
            borderRadius: '50px',
            padding: '8px 20px',
            marginBottom: '32px',
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
            transition: 'all 0.6s ease',
          }}
        >
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00F5D4' }} />
          <span style={{ color: '#00F5D4', fontSize: '14px', fontWeight: 500 }}>
            Private Beta · Limited early access
          </span>
        </div>

        {/* Headline */}
        <h1
          style={{
            fontSize: '72px',
            fontWeight: 700,
            lineHeight: 1.1,
            marginBottom: '24px',
            maxWidth: '900px',
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 0.6s ease 0.1s',
          }}
        >
          AI-Powered<br />
          <span
            style={{
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Web Mapping &amp; Visual Testing
          </span>
        </h1>

        {/* Subheadline */}
        <p
          style={{
            fontSize: '20px',
            color: 'rgba(255,255,255,0.7)',
            maxWidth: '760px',
            lineHeight: 1.7,
            marginBottom: '48px',
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 0.6s ease 0.2s',
          }}
        >
          Quattera automatically discovers and maps form-heavy workflows (including conditional paths) and helps you create
          guided visual scenarios for dynamic web apps. Choose your project type in the app after login.
        </p>

        {/* CTA Buttons */}
        <div
          style={{
            display: 'flex',
            gap: '16px',
            marginBottom: '80px',
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 0.6s ease 0.3s',
          }}
        >
          <Link
            href="/signup"
            style={{
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17',
              padding: '16px 32px',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '16px',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            Request Early Access <span>→</span>
          </Link>
          <Link
            href="/how-it-works"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.2)',
              color: '#fff',
              padding: '16px 32px',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '16px',
              textDecoration: 'none',
            }}
          >
            How it works
          </Link>
        </div>

        {/* Stats (non-claimy) */}
        <div
          style={{
            display: 'flex',
            gap: '80px',
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 0.6s ease 0.4s',
          }}
        >
          <StatItem value="Forms" label="Auto Mapping" />
          <StatItem value="Dynamic" label="Guided Scenarios" />
          <StatItem value="BYOK" label="Cost Control" />
          <StatItem value="Agent" label="Runs in your env" />
        </div>
      </section>

      {/* Problem Section */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '16px' }}>
              The Problem
            </h2>
            <h3 style={{ fontSize: '48px', fontWeight: 700, marginBottom: '24px', lineHeight: 1.2 }}>
              Test Automation is
              <br />
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Broken</span>
            </h3>
            <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.7)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.7 }}>
              Manual scripting doesn’t keep up with modern web apps. When pages evolve, locators break, flows drift, and teams lose confidence.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            <FeatureCard
              icon="⏱️"
              title="Slow to build"
              description="Traditional automation requires constant manual effort and doesn’t scale with UI complexity."
            />
            <FeatureCard
              icon="💥"
              title="Breaks on change"
              description="Small UI updates cause locator failures and brittle suites that demand frequent maintenance."
            />
            <FeatureCard
              icon="🧩"
              title="Hard to cover edge cases"
              description="Conditional fields, nested flows, and dynamic states make full coverage expensive and error-prone."
            />
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <h2 style={{ fontSize: '14px', color: '#00F5D4', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '16px' }}>
              The Solution
            </h2>
            <h3 style={{ fontSize: '48px', fontWeight: 700, marginBottom: '24px', lineHeight: 1.2 }}>
              Let AI Discover, Map
              <br />
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>&amp; Verify</span>
            </h3>
            <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.7)', maxWidth: '720px', margin: '0 auto', lineHeight: 1.7 }}>
              Quattera is built for two realities: enterprise apps full of forms and workflows, and dynamic consumer-style web apps.
              You choose your project type in the app after login.
            </p>
            {/* Progression (platform direction) */}
            <div
              style={{
                maxWidth: '900px',
                margin: '32px auto 56px',
                padding: '18px 18px',
                borderRadius: '14px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '14px',
                  flexWrap: 'wrap',
                }}
              >
                {[
                  { title: 'Discover & Map', badge: 'Available now (Beta)' },
                  { title: 'Generate Scenarios', badge: 'Expanding' },
                  { title: 'Execute & Validate', badge: 'Planned' },
                ].map((s, idx) => (
                  <div
                    key={s.title}
                    style={{
                      flex: '1 1 220px',
                      minWidth: 220,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 12,
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'rgba(0,0,0,0.15)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, color: '#fff', fontSize: 14 }}>{s.title}</div>
                      <div style={{ marginTop: 6, fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{s.badge}</div>
                    </div>

                    {/* Arrow between steps (not after last) */}
                    {idx !== 2 && (
                      <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 18, fontWeight: 700 }}>→</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            <FeatureCard
              icon="🧭"
              title="Automatic form mapping"
              description="Discover form pages, map hierarchy, and capture conditional/nested fields without writing scripts."
            />
            <FeatureCard
              icon="🛠️"
              title="Self-correcting discovery"
              description="If a path is missed, the system can recover and refine the map automatically."
            />
            <FeatureCard
              icon="👁️"
              title="Guided visual scenarios"
              description="Build small scenario steps for dynamic apps and validate outcomes visually, step by step."
            />
            <FeatureCard
              icon="🔒"
              title="Agent-based privacy"
              description="Run the agent in your environment to keep sensitive data where it belongs."
            />
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section style={{ padding: '120px 60px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <h3 style={{ fontSize: '44px', fontWeight: 700, marginBottom: '16px' }}>
            Join the Private Beta
          </h3>
          <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.7, marginBottom: '32px' }}>
            Get early access and help shape the product with direct feedback loops. Choose your workflow after login.
          </p>
          <Link
            href="/signup"
            style={{
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              color: '#0A0E17',
              padding: '16px 32px',
              borderRadius: '10px',
              fontWeight: 700,
              fontSize: '16px',
              textDecoration: 'none',
              display: 'inline-block',
            }}
          >
            Request Early Access →
          </Link>

          <div style={{ marginTop: '18px', fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>
            API mapping is available now. Mobile and deeper automation integrations are planned next.
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '40px 60px', borderTop: '1px solid rgba(255,255,255,0.08)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <QuatheraLogo size={30} />
            <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>© 2026 Quattera.ai</div>
          </div>
          <div style={{ display: 'flex', gap: '20px' }}>
            <Link href="/products" style={{ color: 'rgba(255,255,255,0.6)', textDecoration: 'none', fontSize: '14px' }}>
              Products
            </Link>
            <Link href="/pricing" style={{ color: 'rgba(255,255,255,0.6)', textDecoration: 'none', fontSize: '14px' }}>
              Pricing
            </Link>
            <Link href="/docs" style={{ color: 'rgba(255,255,255,0.6)', textDecoration: 'none', fontSize: '14px' }}>
              Docs
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}