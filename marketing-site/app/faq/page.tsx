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

const faqs = [
  {
    category: 'Getting Started',
    questions: [
      {
        q: 'How long does it take to set up Quathera?',
        a: 'Most teams are up and running in under 30 minutes. Sign up, install the agent, add your test sites, and start discovery. The AI handles everything else automatically.'
      },
      {
        q: 'Do I need coding skills to use Quathera?',
        a: 'No coding required at all. Quathera uses AI to automatically discover forms, map fields, and generate tests. You just point it at your application and let it work.'
      },
      {
        q: 'What browsers does Quathera support?',
        a: 'Quathera supports Chrome, Firefox, Edge, and Electron applications. You can run tests in headed (visible) or headless mode.'
      },
      {
        q: 'Can I use Quathera with any web application?',
        a: 'Yes! Quathera works with any web application regardless of the technology stack - React, Angular, Vue, traditional HTML, SPAs, iframes, and shadow DOM are all supported.'
      }
    ]
  },
  {
    category: 'How It Works',
    questions: [
      {
        q: 'What is "form discovery"?',
        a: 'Form discovery is our AI-powered crawler that navigates your web application like a real user, finding every form page automatically - login screens, registration forms, data entry pages, multi-step wizards, and more.'
      },
      {
        q: 'What is "form mapping"?',
        a: 'After discovering a form, our AI performs deep analysis to understand every field, conditional paths (like dropdowns that show/hide other fields), validation rules, and relationships between forms.'
      },
      {
        q: 'What are "junction paths"?',
        a: 'Junction paths are conditional branches in forms. For example, if selecting "Credit Card" shows card number fields but "Bank Transfer" shows account fields, those are junction paths. Quathera tests all combinations automatically.'
      },
      {
        q: 'How does self-healing work?',
        a: 'When a UI change breaks a test locator (like a button ID changing), our AI detects the failure, analyzes the current page, finds the correct new locator, updates the test, and continues - all automatically.'
      }
    ]
  },
  {
    category: 'Test Sites & Environments',
    questions: [
      {
        q: 'What are test sites?',
        a: 'Test sites represent different entry points to your application. You might have one site for admin users and another for regular users, since each role sees different forms.'
      },
      {
        q: 'Can I test across QA, Staging, and Production?',
        a: 'Yes! Discovery happens in your QA environment, then you can run the same tests against Staging or Production. The form mappings work across environments with consistent UI.'
      },
      {
        q: 'How do I handle different user roles?',
        a: 'Create a test site for each user role (Admin, Manager, User, etc.) with appropriate credentials. Quathera will discover forms accessible to each role separately.'
      }
    ]
  },
  {
    category: 'CI/CD Integration',
    questions: [
      {
        q: 'Can I integrate Quathera with my CI/CD pipeline?',
        a: 'Absolutely! Download our CI/CD agent, add it to your Docker image, and run tests via command line. Works with GitHub Actions, Jenkins, GitLab CI, CircleCI, and any other pipeline.'
      },
      {
        q: 'How do I run tests from command line?',
        a: 'Use commands like: quathera-agent run --project "My App" --env staging --version "v1.2.3". Results sync automatically to your web dashboard.'
      },
      {
        q: 'Can I track test coverage across versions?',
        a: 'Yes! The Version Coverage Matrix shows test results across all your releases. Columns are versions, rows are tests, with green/orange/red indicators for pass status.'
      }
    ]
  },
  {
    category: 'Security & Privacy',
    questions: [
      {
        q: 'Where does the agent run?',
        a: 'The Quathera Agent runs entirely on your infrastructure - your local machine, a test server, or your CI/CD pipeline. Your credentials and test data never leave your network.'
      },
      {
        q: 'Is my data encrypted?',
        a: 'Yes. All data in transit uses TLS 1.3 encryption. Data at rest in our cloud (configurations, results) is encrypted with AES-256. Your actual test data stays local.'
      },
      {
        q: 'Do you support 2FA?',
        a: 'Yes, two-factor authentication is available for all accounts using standard TOTP apps like Google Authenticator, Authy, or 1Password.'
      },
      {
        q: 'Are you GDPR compliant?',
        a: 'Quathera is GDPR-ready with data minimization, right to access, right to deletion, and Data Processing Agreements available for enterprise customers.'
      }
    ]
  },
  {
    category: 'Pricing & Plans',
    questions: [
      {
        q: 'Is there a free trial?',
        a: 'Yes! We offer a 14-day free trial with full feature access. No credit card required. You can also use our BYOK (Bring Your Own Key) trial with your own Anthropic API key for unlimited AI usage.'
      },
      {
        q: 'What\'s included in each plan?',
        a: 'Starter ($300/mo) includes 5 projects, 3 team members, and $300 AI budget. Professional ($500/mo) includes unlimited projects, 10 team members, and $500 AI budget. Enterprise has custom pricing with dedicated support.'
      },
      {
        q: 'What is the AI budget?',
        a: 'The AI budget covers the cost of AI operations like form discovery, mapping, and test generation. Most teams stay well within their budget. The BYOK option lets you use your own API key.'
      }
    ]
  },
  {
    category: 'Troubleshooting',
    questions: [
      {
        q: 'Where can I see logs?',
        a: 'Logs are available in two places: the Agent shows real-time execution logs locally, and the Web App shows aggregated logs with filtering and search.'
      },
      {
        q: 'Can I see screenshots of failures?',
        a: 'Yes! Every test failure automatically captures a screenshot showing exactly what the page looked like at the moment of failure. Great for debugging.'
      },
      {
        q: 'What if discovery misses a form?',
        a: 'You can manually trigger discovery for specific pages or add navigation hints. Our AI learns from your application structure over time.'
      }
    ]
  }
]

export default function FAQ() {
  const [openItems, setOpenItems] = useState<{[key: string]: boolean}>({})

  const toggleItem = (key: string) => {
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }))
  }

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
          <Link href="/login" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontSize: '15px' }}>Login</Link>
          <Link href="/signup" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '12px 24px', borderRadius: '8px', fontWeight: 600, fontSize: '14px', textDecoration: 'none' }}>Start Free Trial</Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '100px 60px 60px', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <h1 style={{ fontSize: '56px', fontWeight: 700, marginBottom: '20px' }}>
          Frequently Asked <span style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Questions</span>
        </h1>
        <p style={{ fontSize: '20px', color: 'rgba(255,255,255,0.6)', maxWidth: '600px', margin: '0 auto' }}>
          Everything you need to know about Quathera
        </p>
      </section>

      {/* FAQ Content */}
      <section style={{ padding: '40px 60px 120px', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {faqs.map((category, ci) => (
            <div key={ci} style={{ marginBottom: '60px' }}>
              <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px', color: '#00F5D4' }}>{category.category}</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {category.questions.map((item, qi) => {
                  const key = `${ci}-${qi}`
                  const isOpen = openItems[key]
                  return (
                    <div key={qi} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', overflow: 'hidden' }}>
                      <button
                        onClick={() => toggleItem(key)}
                        style={{
                          width: '100%', padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left'
                        }}
                      >
                        <span style={{ fontSize: '17px', fontWeight: 600, color: '#fff' }}>{item.q}</span>
                        <span style={{ fontSize: '24px', color: '#00F5D4', transform: isOpen ? 'rotate(45deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>+</span>
                      </button>
                      {isOpen && (
                        <div style={{ padding: '0 24px 20px', color: 'rgba(255,255,255,0.7)', fontSize: '16px', lineHeight: 1.7 }}>
                          {item.a}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '80px 60px', position: 'relative', zIndex: 1, background: 'rgba(0,245,212,0.02)', textAlign: 'center' }}>
        <h2 style={{ fontSize: '36px', fontWeight: 700, marginBottom: '16px' }}>Still have questions?</h2>
        <p style={{ fontSize: '18px', color: 'rgba(255,255,255,0.6)', marginBottom: '32px' }}>Our team is here to help. Reach out anytime.</p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
          <a href="mailto:support@quathera.com" style={{ background: 'linear-gradient(135deg, #00F5D4, #00BBF9)', color: '#0A0E17', padding: '16px 32px', borderRadius: '10px', fontWeight: 600, fontSize: '16px', textDecoration: 'none' }}>Contact Support</a>
          <Link href="/signup" style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', padding: '16px 32px', borderRadius: '10px', fontWeight: 600, fontSize: '16px', textDecoration: 'none' }}>Start Free Trial</Link>
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
