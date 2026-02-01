'use client'
import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import config from '../../config'

const QuatheraLogoSmall = () => (
  <svg width="200" height="50" viewBox="150 200 700 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="circuitGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{ stopColor: '#00F5D4' }} />
        <stop offset="50%" style={{ stopColor: '#00BBF9' }} />
        <stop offset="100%" style={{ stopColor: '#9B5DE5' }} />
      </linearGradient>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <g transform="translate(500, 250)">
      <g transform="translate(-280, 0)">
        <circle
          cx="0"
          cy="0"
          r="40"
          fill="none"
          stroke="url(#circuitGradient)"
          strokeWidth="4"
          filter="url(#glow)"
        />
        <g
          stroke="url(#circuitGradient)"
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
          filter="url(#glow)"
        >
          <path d="M -28 -16 Q -34 0 -30 16 Q -24 34 0 38 Q 24 34 30 16 Q 34 0 28 -16 Q 20 -34 0 -36 Q -20 -34 -28 -16" />
          <path d="M 20 24 L 40 44 L 52 40" />
          <circle cx="52" cy="40" r="3" fill="url(#circuitGradient)" />
        </g>
        <circle cx="0" cy="0" r="6" fill="#0A0E17" stroke="url(#circuitGradient)" strokeWidth="1.5" />
      </g>

      <g transform="translate(-180, 0)">
        <text
          x="0"
          y="14"
          fontFamily="'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
          fontSize="64"
          fontWeight="300"
          fill="#FFFFFF"
          letterSpacing="4"
        >
          <tspan fill="url(#circuitGradient)" fontWeight="600">
            Q
          </tspan>
          uattera
        </text>
      </g>
    </g>
  </svg>
)

type VerifyStatus = 'verifying' | 'email_verified' | 'already_verified' | 'invalid' | 'expired' | 'error'

export default function VerifyEmail() {
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<VerifyStatus>('verifying')
  const hasCalledRef = useRef(false)

  useEffect(() => {
  if (hasCalledRef.current) return
  hasCalledRef.current = true

  const token = searchParams.get('token')

    if (!token) {
      setStatus('invalid')
      return
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${config.apiUrl}/api/auth/verify-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })

        const data = await response.json()

        if (data.status === 'email_verified' || data.status === 'already_verified') {
          window.location.href = 'https://localhost/login'
          return
        } else if (data.status === 'expired') {
          setStatus('expired')
        } else {
          setStatus('invalid')
        }
      } catch (err) {
        setStatus('error')
      }
    }

    verifyEmail()
  }, [searchParams])

  const getContent = () => {
    switch (status) {
      case 'verifying':
        return {
          emoji: '⏳',
          title: 'Verifying your email...',
          message: 'Please wait a moment.',
          showLogin: false,
        }
      case 'email_verified':
        return {
          emoji: '✅',
          title: 'Email verified!',
          message: 'Your account is now active. You can sign in.',
          showLogin: true,
        }
      case 'already_verified':
        return {
          emoji: '✅',
          title: 'Already verified',
          message: 'Your email was already verified. You can sign in.',
          showLogin: true,
        }
      case 'expired':
        return {
          emoji: '⏰',
          title: 'Link expired',
          message: 'This verification link has expired. Please request a new one by trying to sign in.',
          showLogin: true,
        }
      case 'invalid':
        return {
          emoji: '❌',
          title: 'Invalid link',
          message: 'This verification link is invalid or has already been used.',
          showLogin: true,
        }
      case 'error':
        return {
          emoji: '⚠️',
          title: 'Something went wrong',
          message: 'Unable to verify your email. Please try again later.',
          showLogin: true,
        }
    }
  }

  const content = getContent()

  return (
    <div style={shell}>
      {/* background layers */}
      <div style={bgBase} />
      <div style={bgGrid} />
      <div style={bgGlowRight} />
      <div style={bgGlowLeft} />

      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 480 }}>
        {/* top logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: 'none' }}>
            <QuatheraLogoSmall />
          </Link>
        </div>

        {/* Card */}
        <div style={card}>
          <div style={{ fontSize: 54, marginBottom: 16, textAlign: 'center' }}>{content.emoji}</div>
          <h1 style={{ fontSize: 24, fontWeight: 900, marginBottom: 12, color: '#fff', textAlign: 'center' }}>
            {content.title}
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.65)', margin: 0, lineHeight: 1.6, textAlign: 'center', fontSize: 15 }}>
            {content.message}
          </p>

          {content.showLogin && (
            <Link
              href="https://localhost/login"
              style={{
                display: 'block',
                marginTop: 28,
                padding: '14px 24px',
                background: 'linear-gradient(135deg, #00F5D4 0%, #00BBF9 100%)',
                color: '#0A0E17',
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 12,
                textDecoration: 'none',
                textAlign: 'center',
                boxShadow: '0 10px 30px rgba(0,245,212,0.16)',
              }}
            >
              Go to Login
            </Link>
          )}
        </div>

        {/* bottom link */}
        <p style={{ textAlign: 'center', marginTop: 24, color: 'rgba(255,255,255,0.6)', fontSize: 14 }}>
          Need help?{' '}
          <a href="mailto:support@quattera.ai" style={{ color: '#00F5D4', textDecoration: 'none', fontWeight: 700 }}>
            Contact support
          </a>
        </p>
      </div>
    </div>
  )
}

/* styles */
const shell: React.CSSProperties = {
  minHeight: '100vh',
  position: 'relative',
  display: 'grid',
  placeItems: 'center',
  fontFamily: "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
  padding: '36px 18px',
}

const bgBase: React.CSSProperties = { position: 'fixed', inset: 0, background: '#0A0E17' }

const bgGrid: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  backgroundImage:
    'linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px)',
  backgroundSize: '60px 60px',
  pointerEvents: 'none',
}

const bgGlowRight: React.CSSProperties = {
  position: 'fixed',
  top: '-20%',
  right: '-10%',
  width: 640,
  height: 640,
  background: 'radial-gradient(circle, rgba(0,187,249,0.15) 0%, transparent 70%)',
  borderRadius: '50%',
  pointerEvents: 'none',
}

const bgGlowLeft: React.CSSProperties = {
  position: 'fixed',
  bottom: '-30%',
  left: '-10%',
  width: 820,
  height: 820,
  background: 'radial-gradient(circle, rgba(155,93,229,0.12) 0%, transparent 70%)',
  borderRadius: '50%',
  pointerEvents: 'none',
}

const card: React.CSSProperties = {
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(255,255,255,0.03)',
  padding: 44,
  borderRadius: 18,
  textAlign: 'center',
}