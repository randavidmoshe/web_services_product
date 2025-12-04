'use client'
import Link from 'next/link'

// Quathera Logo Component
const QuatheraLogo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
        <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
        <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
      </linearGradient>
    </defs>
    <g transform="translate(50, 50)">
      <circle cx="0" cy="0" r="35" fill="none" stroke="url(#logoGradient)" strokeWidth="3"/>
      <g stroke="url(#logoGradient)" strokeWidth="2" fill="none" strokeLinecap="round">
        <path d="M -22 -12 Q -28 0 -24 12 Q -18 26 0 30 Q 18 26 24 12 Q 28 0 22 -12 Q 14 -28 0 -30 Q -14 -28 -22 -12"/>
        <path d="M 16 18 L 32 34 L 42 30"/>
        <circle cx="42" cy="30" r="3" fill="url(#logoGradient)"/>
      </g>
    </g>
  </svg>
)

const PricingCard = ({ 
  name, 
  price, 
  period, 
  features, 
  ctaText, 
  ctaLink, 
  popular = false 
}: { 
  name: string
  price: string
  period: string
  features: string[]
  ctaText: string
  ctaLink: string
  popular?: boolean
}) => (
  <div style={{
    padding: '40px',
    borderRadius: '20px',
    background: popular ? 'linear-gradient(135deg, rgba(0, 245, 212, 0.1), rgba(0, 187, 249, 0.1))' : 'rgba(255,255,255,0.03)',
    border: popular ? '2px solid rgba(0, 245, 212, 0.4)' : '1px solid rgba(255,255,255,0.08)',
    position: 'relative',
    transition: 'transform 0.3s, box-shadow 0.3s'
  }}>
    {popular && (
      <div style={{
        position: 'absolute',
        top: '-14px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'linear-gradient(135deg, #00F5D4, #00BBF9)',
        color: '#0A0E17',
        padding: '6px 20px',
        borderRadius: '20px',
        fontSize: '12px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '1px'
      }}>
        Most Popular
      </div>
    )}
    
    <h3 style={{ fontSize: '22px', fontWeight: 600, marginBottom: '16px', color: '#fff' }}>{name}</h3>
    
    <div style={{ marginBottom: '24px' }}>
      <span style={{ fontSize: '48px', fontWeight: 700, color: '#fff' }}>{price}</span>
      <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '16px' }}>{period}</span>
    </div>
    
    <ul style={{ listStyle: 'none', padding: 0, marginBottom: '32px' }}>
      {features.map((feature, idx) => (
        <li key={idx} style={{
          padding: '12px 0',
          color: 'rgba(255,255,255,0.7)',
          fontSize: '15px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ color: '#00F5D4' }}>✓</span>
          {feature}
        </li>
      ))}
    </ul>
    
    <Link href={ctaLink} style={{
      display: 'block',
      textAlign: 'center',
      padding: '16px',
      borderRadius: '10px',
      background: popular ? 'linear-gradient(135deg, #00F5D4, #00BBF9)' : 'rgba(255,255,255,0.1)',
      color: popular ? '#0A0E17' : '#fff',
      fontWeight: 600,
      fontSize: '15px',
      textDecoration: 'none',
      border: popular ? 'none' : '1px solid rgba(255,255,255,0.2)',
      transition: 'transform 0.2s'
    }}>
      {ctaText}
    </Link>
  </div>
)

export default function Pricing() {
  return (
    <div style={{ 
      minHeight: '100vh',
      background: '#0A0E17',
      color: '#fff',
      fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
    }}>
      {/* Background */}
      <div style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: `
          linear-gradient(rgba(0, 245, 212, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 245, 212, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
        pointerEvents: 'none'
      }} />

      {/* Navigation */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 60px',
        background: 'rgba(10, 14, 23, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        position: 'relative',
        zIndex: 10
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
          <QuatheraLogo />
          <span style={{ 
            fontSize: '22px', fontWeight: 600, letterSpacing: '2px',
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>QUATHERA</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/products" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Products</Link>
          <Link href="/how-it-works" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>How It Works</Link>
          <Link href="/pricing" style={{ color: '#00F5D4', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>Pricing</Link>
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Login</Link>
          <Link href="/signup" style={{
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
            color: '#0A0E17', padding: '12px 24px', borderRadius: '8px',
            fontWeight: 600, fontSize: '14px', textDecoration: 'none'
          }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Header */}
      <section style={{
        padding: '100px 60px 60px',
        textAlign: 'center',
        position: 'relative',
        zIndex: 1
      }}>
        <h1 style={{
          fontSize: '52px',
          fontWeight: 700,
          marginBottom: '20px'
        }}>
          Simple, Transparent Pricing
        </h1>
        <p style={{
          fontSize: '20px',
          color: 'rgba(255,255,255,0.6)',
          maxWidth: '600px',
          margin: '0 auto'
        }}>
          Start free for 14 days. No credit card required. Upgrade when you're ready.
        </p>
      </section>

      {/* Pricing Cards */}
      <section style={{
        padding: '40px 60px 120px',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '24px',
          maxWidth: '1400px',
          margin: '0 auto'
        }}>
          <PricingCard
            name="Free Trial"
            price="$0"
            period="/14 days"
            features={[
              '14-day full access',
              'Limited AI usage',
              '1 project',
              '1 team member',
              'Email support'
            ]}
            ctaText="Start Free"
            ctaLink="/signup?plan=trial"
          />
          
          <PricingCard
            name="Free Trial (BYOK)"
            price="$0"
            period="/14 days"
            features={[
              '14-day full access',
              'Your own API key',
              'Unlimited AI usage',
              '1 project',
              'Email support'
            ]}
            ctaText="Start with Your Key"
            ctaLink="/signup?plan=trial_byok"
          />
          
          <PricingCard
            name="Starter"
            price="$300"
            period="/month"
            features={[
              '$300 AI budget/month',
              '5 projects',
              '3 team members',
              'Priority support',
              'Jira integration'
            ]}
            ctaText="Get Started"
            ctaLink="/signup?plan=starter"
            popular={true}
          />
          
          <PricingCard
            name="Professional"
            price="$500"
            period="/month"
            features={[
              '$500 AI budget/month',
              'Unlimited projects',
              '10 team members',
              'Dedicated support',
              'Full integrations'
            ]}
            ctaText="Get Started"
            ctaLink="/signup?plan=professional"
          />
        </div>
      </section>

      {/* Enterprise CTA */}
      <section style={{
        padding: '80px 60px',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          maxWidth: '800px',
          margin: '0 auto',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '20px',
          padding: '60px',
          textAlign: 'center'
        }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '16px' }}>
            Need Enterprise Features?
          </h2>
          <p style={{
            fontSize: '18px',
            color: 'rgba(255,255,255,0.6)',
            marginBottom: '32px',
            lineHeight: 1.7
          }}>
            Custom pricing for larger teams, advanced security requirements, 
            dedicated infrastructure, and SLA guarantees.
          </p>
          <Link href="/contact" style={{
            display: 'inline-block',
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff',
            padding: '16px 32px',
            borderRadius: '10px',
            fontWeight: 600,
            fontSize: '16px',
            textDecoration: 'none'
          }}>
            Contact Sales
          </Link>
        </div>
      </section>

      {/* FAQ Preview */}
      <section style={{
        padding: '80px 60px',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '40px', textAlign: 'center' }}>
            Frequently Asked Questions
          </h2>
          
          {[
            { q: 'What happens after my free trial ends?', a: 'Your account remains active but testing is paused. Upgrade to continue, or export your test configurations. No data is deleted.' },
            { q: 'What is BYOK (Bring Your Own Key)?', a: 'BYOK lets you use your own Anthropic API key for AI operations. This gives you unlimited AI usage and direct control over your AI costs.' },
            { q: 'Can I change plans later?', a: 'Yes, you can upgrade or downgrade at any time. Changes take effect immediately, and billing is prorated.' },
            { q: 'Do you offer refunds?', a: 'Yes, we offer a 30-day money-back guarantee for all paid plans. No questions asked.' }
          ].map((faq, idx) => (
            <div key={idx} style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '12px',
              padding: '24px',
              marginBottom: '16px'
            }}>
              <h4 style={{ fontSize: '17px', fontWeight: 600, marginBottom: '12px', color: '#fff' }}>{faq.q}</h4>
              <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.6)', margin: 0, lineHeight: 1.6 }}>{faq.a}</p>
            </div>
          ))}
          
          <div style={{ textAlign: 'center', marginTop: '32px' }}>
            <Link href="/faq" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 600, fontSize: '15px' }}>
              View All FAQs →
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '40px 60px',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
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
