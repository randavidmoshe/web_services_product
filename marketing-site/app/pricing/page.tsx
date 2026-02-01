'use client'
import { useState } from 'react'
import Link from 'next/link'

// Logo (keep your internal component name; branding is in text)
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

type AccessCardModel = {
  icon: string
  title: string
  subtitle: string
  badge: string
  description: string
  bullets: string[]
  cta?: { label: string; href: string; variant: 'primary' | 'secondary' }
}

function AccessCard({ model }: { model: AccessCardModel }) {
  const [isHovered, setIsHovered] = useState(false)

  const baseBorder = '1px solid rgba(255,255,255,0.06)'
  const hoverBorder = '1px solid rgba(0,245,212,0.35)'

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: isHovered
          ? 'linear-gradient(135deg, rgba(0,245,212,0.08), rgba(155,93,229,0.08))'
          : 'rgba(255,255,255,0.02)',
        border: isHovered ? hoverBorder : baseBorder,
        borderRadius: 18,
        padding: isHovered ? 34 : 32,
        transition: 'all 0.35s ease',
        transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 360,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14 }}>
        <div style={{ fontSize: 42 }}>{model.icon}</div>
        <div
          style={{
            fontSize: 12,
            fontWeight: 800,
            padding: '6px 10px',
            borderRadius: 999,
            border: '1px solid rgba(255,255,255,0.12)',
            background: 'rgba(0,0,0,0.22)',
            color: 'rgba(255,255,255,0.78)',
            whiteSpace: 'nowrap',
          }}
        >
          {model.badge}
        </div>
      </div>

      <h3
        style={{
          fontSize: 26,
          fontWeight: 800,
          margin: '14px 0 6px',
          background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        {model.title}
      </h3>

      <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.7)', marginBottom: 14 }}>{model.subtitle}</div>

      <div style={{ color: 'rgba(255,255,255,0.62)', lineHeight: 1.7, marginBottom: 18 }}>{model.description}</div>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, marginBottom: 22 }}>
        {model.bullets.map((b, i) => (
          <li
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '7px 0',
              color: 'rgba(255,255,255,0.78)',
              fontSize: 15,
            }}
          >
            <span style={{ color: '#00F5D4' }}>✓</span>
            {b}
          </li>
        ))}
      </ul>

      <div style={{ marginTop: 'auto' }}>
        {model.cta ? (
          <Link
            href={model.cta.href}
            style={{
              display: 'inline-block',
              textDecoration: 'none',
              padding: '14px 18px',
              borderRadius: 10,
              fontWeight: 900,
              fontSize: 15,
              color: model.cta.variant === 'primary' ? '#0A0E17' : '#fff',
              background:
                model.cta.variant === 'primary'
                  ? 'linear-gradient(135deg, #00F5D4, #00BBF9)'
                  : 'rgba(255,255,255,0.06)',
              border: model.cta.variant === 'primary' ? 'none' : '1px solid rgba(255,255,255,0.18)',
            }}
          >
            {model.cta.label} →
          </Link>
        ) : (
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.55)' }}>No action required</div>
        )}
      </div>
    </div>
  )
}

function SectionTitle({ eyebrow, title, desc }: { eyebrow: string; title: string; desc?: string }) {
  return (
    <div style={{ textAlign: 'center', marginBottom: 28 }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 14px',
          borderRadius: 999,
          background: 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.12)',
          fontSize: 13,
          fontWeight: 800,
          color: 'rgba(255,255,255,0.82)',
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: 999, background: '#34d399', display: 'inline-block' }} />
        {eyebrow}
      </div>

      <h2 style={{ fontSize: 40, fontWeight: 800, margin: '18px 0 10px' }}>{title}</h2>

      {desc ? (
        <p
          style={{
            fontSize: 18,
            color: 'rgba(255,255,255,0.62)',
            maxWidth: 860,
            margin: '0 auto',
            lineHeight: 1.7,
          }}
        >
          {desc}
        </p>
      ) : null}
    </div>
  )
}

export default function Pricing() {
  const accessModels: AccessCardModel[] = [
    {
      icon: '🟢',
      title: 'Early Access',
      subtitle: 'Funded by Quattera (manual approval)',
      badge: 'Limited capacity',
      description:
        'Designed for serious evaluation and feedback. To ensure quality and control AI usage, Early Access is approved manually and limited to a small number of active users.',
      bullets: [
        'Manual approval (limited active slots)',
        'Quattera funds capped AI usage',
        'Best for teams evaluating quickly',
        'Choose project type after login',
      ],
      cta: { label: 'Request Early Access', href: '/signup', variant: 'primary' },
    },
    {
      icon: '🔵',
      title: 'BYOK',
      subtitle: 'Bring Your Own AI Key (instant access)',
      badge: 'Instant access',
      description:
        'Use your own Anthropic/OpenAI API key to power mapping and scenario generation. This removes AI usage limits from Quattera and gives you full control over cost and scale.',
      bullets: [
        'Instant access after signup',
        'Use your own AI key (tokens billed to you)',
        'Choose models (e.g., Sonnet / Haiku)',
        'Great for power users & enterprises',
      ],
      cta: { label: 'Start with BYOK', href: '/signup', variant: 'secondary' },
    },
    {
      icon: '🟣',
      title: 'Execution layer',
      subtitle: 'Expanding capabilities',
      badge: 'Expanding',
      description:
        'Quattera is built to grow from understanding into automation. Execution features (runs, healing, locator correction, API execution) expand as coverage and reliability mature.',
      bullets: [
        'Scenario execution (end-to-end)',
        'Visual verification during runs',
        'Self-healing & locator correction',
        'API execution (positive/negative)',
      ],
      // no CTA on purpose
    },
  ]

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0A0E17',
        color: '#fff',
        fontFamily: "'SF Pro Display', 'Segoe UI', sans-serif",
      }}
    >
      {/* Background grid */}
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
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <QuatheraLogo />
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 2,
              background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            QUATTERA.ai
          </span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 40 }}>
          <Link href="/products" style={navLink}>
            Products
          </Link>
          <Link href="/how-it-works" style={navLink}>
            How It Works
          </Link>
          <Link href="/pricing" style={{ ...navLink, color: '#00F5D4', fontWeight: 700 }}>
            Pricing
          </Link>
          <Link href="/docs" style={navLink}>
            Docs
          </Link>
          <Link href="/login" style={navLink}>
            Login
          </Link>
          <Link
            href="/signup"
            style={{
              background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
              color: '#0A0E17',
              padding: '12px 20px',
              borderRadius: 10,
              fontWeight: 900,
              fontSize: 14,
              textDecoration: 'none',
            }}
          >
            Request Early Access
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '110px 60px 20px', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <SectionTitle
          eyebrow="Private Beta · Access models"
          title="Pricing"
          desc="No complicated tiers yet. Choose how you want to power Quattera’s AI — either via Early Access (funded, manually approved) or BYOK (instant)."
        />
      </section>

      {/* Access cards */}
      <section style={{ padding: '10px 60px 70px', position: 'relative', zIndex: 1 }}>
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 22,
          }}
        >
          {accessModels.map((m) => (
            <AccessCard key={m.title} model={m} />
          ))}
        </div>

        <div
          style={{
            maxWidth: 1200,
            margin: '18px auto 0',
            color: 'rgba(255,255,255,0.55)',
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          Tip: You’ll choose your project type (Form-heavy vs Dynamic) inside the app after login.
        </div>
      </section>

      {/* What happens after signup */}
      <section style={{ padding: '70px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)' }}>
        <div style={{ maxWidth: 980, margin: '0 auto' }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 10, textAlign: 'center' }}>
            What happens after signup?
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.62)', textAlign: 'center', marginBottom: 28, lineHeight: 1.7 }}>
            We keep onboarding secure and predictable. No hidden usage, no surprise costs.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: 16,
            }}
          >
            {[
              { n: '1', t: 'Create your account', d: 'Sign up with email and password.' },
              { n: '2', t: 'Verify email + set up 2FA', d: 'Confirm your email and complete 2FA for secure access.' },
              { n: '3', t: 'Choose project type', d: 'Pick Form-heavy or Dynamic project inside the app.' },
              { n: '4', t: 'Choose AI funding', d: 'Request Early Access (manual approval) or use BYOK (instant).' },
            ].map((s) => (
              <div
                key={s.n}
                style={{
                  border: '1px solid rgba(255,255,255,0.08)',
                  background: 'rgba(0,0,0,0.18)',
                  borderRadius: 16,
                  padding: 18,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: 999,
                      background: 'rgba(255,255,255,0.07)',
                      border: '1px solid rgba(255,255,255,0.12)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 900,
                    }}
                  >
                    {s.n}
                  </div>
                  <div style={{ fontWeight: 900 }}>{s.t}</div>
                </div>
                <div style={{ color: 'rgba(255,255,255,0.62)', lineHeight: 1.6 }}>{s.d}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 18, color: 'rgba(255,255,255,0.55)', fontSize: 13, lineHeight: 1.6 }}>
            Early Access requests are reviewed manually to keep evaluation quality high and to manage funded AI usage.
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section style={{ padding: '80px 60px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 980, margin: '0 auto' }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 18, textAlign: 'center' }}>FAQ</h2>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 14 }}>
            <Faq
              q="Why is Early Access manually approved?"
              a="Because funded AI usage has real cost. Manual approval keeps Early Access high-quality and prevents abuse, while giving serious evaluators a great experience."
            />
            <Faq
              q="What does BYOK mean?"
              a="Bring Your Own Key. You connect your Anthropic/OpenAI key so token usage is billed to you, and you can scale without Quattera-funded limits."
            />
            <Faq
              q="Do I need a credit card?"
              a="Not at this stage. Early Access is approved manually, and BYOK uses your own AI key. No credit card flow is required."
            />
            <Faq
              q="When do execution features become available?"
              a="Execution expands as reliability and coverage mature. You’ll see execution capabilities appear inside the app as they become ready—without hard dates on the marketing site."
            />
          </div>

          <div style={{ textAlign: 'center', marginTop: 28 }}>
            <Link
              href="/signup"
              style={{
                display: 'inline-block',
                background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
                color: '#0A0E17',
                padding: '16px 28px',
                borderRadius: 10,
                fontWeight: 900,
                fontSize: 16,
                textDecoration: 'none',
              }}
            >
              Request Early Access →
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '40px 60px', borderTop: '1px solid rgba(255,255,255,0.05)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <QuatheraLogo size={28} />
            <span style={{ fontSize: 16, fontWeight: 800, color: 'rgba(255,255,255,0.85)' }}>QUATTERA.ai</span>
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <Link href="/products" style={footerLink}>Products</Link>
            <Link href="/how-it-works" style={footerLink}>How It Works</Link>
            <Link href="/pricing" style={{ ...footerLink, color: '#00F5D4' }}>Pricing</Link>
            <Link href="/docs" style={footerLink}>Docs</Link>
            <Link href="/login" style={footerLink}>Login</Link>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14, margin: 0 }}>© 2026 Quattera.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

function Faq({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      style={{
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 16,
        background: open ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.02)',
        overflow: 'hidden',
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%',
          textAlign: 'left',
          padding: '16px 18px',
          background: 'transparent',
          border: 'none',
          color: '#fff',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <span style={{ fontWeight: 900 }}>{q}</span>
        <span style={{ color: 'rgba(255,255,255,0.6)', fontWeight: 900 }}>{open ? '–' : '+'}</span>
      </button>
      {open ? (
        <div style={{ padding: '0 18px 16px', color: 'rgba(255,255,255,0.62)', lineHeight: 1.7 }}>{a}</div>
      ) : null}
    </div>
  )
}

const navLink: React.CSSProperties = {
  color: 'rgba(255,255,255,0.72)',
  textDecoration: 'none',
  fontSize: 15,
}

const footerLink: React.CSSProperties = {
  color: 'rgba(255,255,255,0.6)',
  textDecoration: 'none',
  fontSize: 14,
}