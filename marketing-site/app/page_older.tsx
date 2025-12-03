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
        padding: '16px 60px',
        background: '#ffffff',
        borderBottom: '1px solid #e2e8f0',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <svg width="300" height="70" viewBox="130 175 740 150" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="circuitGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
                <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
                <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
              </linearGradient>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            <g transform="translate(500, 250)">
              {/* Q Icon */}
              <g transform="translate(-280, 0)">
                <polygon points="0,-75 65,-37.5 65,37.5 0,75 -65,37.5 -65,-37.5" 
                         fill="none" stroke="#e2e8f0" strokeWidth="2"/>
                <circle cx="0" cy="0" r="52" fill="none" stroke="url(#circuitGradient)" strokeWidth="5" filter="url(#glow)"/>
                <g stroke="url(#circuitGradient)" strokeWidth="3" fill="none" strokeLinecap="round" filter="url(#glow)">
                  <path d="M -35 -20 Q -42 0 -38 20 Q -30 42 0 48 Q 30 42 38 20 Q 42 0 35 -20 Q 25 -42 0 -45 Q -25 -42 -35 -20"/>
                  <path d="M -20 -10 Q -25 5 -18 18 Q -5 28 12 22 Q 25 12 22 -5 Q 18 -22 0 -25 Q -15 -22 -20 -10" opacity="0.6"/>
                  <path d="M 25 30 L 50 55 L 65 50"/>
                  <circle cx="65" cy="50" r="4" fill="url(#circuitGradient)"/>
                </g>
                <g fill="url(#circuitGradient)" filter="url(#glow)">
                  <circle cx="-38" cy="-18" r="4"/>
                  <circle cx="-40" cy="18" r="4"/>
                  <circle cx="0" cy="48" r="4"/>
                  <circle cx="38" cy="18" r="4"/>
                  <circle cx="38" cy="-18" r="4"/>
                  <circle cx="0" cy="-45" r="4"/>
                  <circle cx="-30" cy="-35" r="3"/>
                  <circle cx="30" cy="-35" r="3"/>
                </g>
                <circle cx="0" cy="0" r="8" fill="#ffffff" stroke="url(#circuitGradient)" strokeWidth="2"/>
                <circle cx="0" cy="0" r="3" fill="url(#circuitGradient)" opacity="0.8"/>
              </g>
              
              {/* Quathera Text */}
              <g transform="translate(-180, 0)">
                <text x="0" y="18" 
                      fontFamily="'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif" 
                      fontSize="82" 
                      fontWeight="300" 
                      fill="#0A0E17" 
                      letterSpacing="6">
                  <tspan fill="url(#circuitGradient)" fontWeight="600">Q</tspan>uathera
                </text>
              </g>
            </g>
          </svg>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          <Link href="/pricing" style={{ color: '#475569', fontWeight: 500, textDecoration: 'none' }}>Pricing</Link>
          <Link href="/login" style={{ color: '#475569', fontWeight: 500, textDecoration: 'none' }}>Login</Link>
          <Link href="/signup" style={{
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            color: '#0A0E17',
            padding: '10px 24px',
            borderRadius: '8px',
            fontWeight: 600,
            textDecoration: 'none'
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
          <span style={{ 
            background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>Automated</span>
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
            background: 'linear-gradient(135deg, #00BBF9 0%, #9B5DE5 100%)',
            color: '#fff',
            padding: '16px 32px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '18px',
            textDecoration: 'none',
            boxShadow: '0 4px 15px rgba(0, 187, 249, 0.3)'
          }}>
            Start Free Trial
          </Link>
          <Link href="/pricing" style={{
            background: '#fff',
            color: '#0A0E17',
            padding: '16px 32px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '18px',
            border: '2px solid #0A0E17',
            textDecoration: 'none'
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
            border: '2px solid #00BBF9',
            background: 'linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%)'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>📋</div>
            <h3 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '12px' }}>Form Pages Testing</h3>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              Automatically discover all form pages in your application. AI-powered crawling identifies forms, fields, and validation rules.
            </p>
            <Link href="/pricing" style={{
              color: '#00BBF9',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              textDecoration: 'none'
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
              background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#0A0E17',
              fontWeight: 700
            }}>1</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>Install Agent</h3>
            <p style={{ color: '#64748b' }}>Download and run our lightweight agent on your machine</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
              width: '80px',
              height: '80px',
              background: 'linear-gradient(135deg, #00BBF9 0%, #9B5DE5 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#fff',
              fontWeight: 700
            }}>2</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>Add Your Site</h3>
            <p style={{ color: '#64748b' }}>Configure your web application URL and test credentials</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
              width: '80px',
              height: '80px',
              background: 'linear-gradient(135deg, #9B5DE5 0%, #7C3AED 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#fff',
              fontWeight: 700
            }}>3</div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px' }}>AI Discovers</h3>
            <p style={{ color: '#64748b' }}>Our AI crawls your site and discovers all form pages automatically</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section style={{
        padding: '80px 60px',
        background: 'linear-gradient(135deg, #0A0E17 0%, #1a2535 100%)',
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
          background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%)',
          color: '#0A0E17',
          padding: '16px 40px',
          borderRadius: '8px',
          fontWeight: 600,
          fontSize: '18px',
          display: 'inline-block',
          textDecoration: 'none',
          boxShadow: '0 4px 20px rgba(0, 187, 249, 0.3)'
        }}>
          Start Free Trial
        </Link>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '40px 60px',
        background: '#050709',
        color: '#64748b',
        textAlign: 'center'
      }}>
        <p>© 2025 Quathera. All rights reserved.</p>
      </footer>
    </div>
  )
}
