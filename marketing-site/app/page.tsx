'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'

export default function Home() {
  const [scrolled, setScrolled] = useState(false)
  const [activeTestimonial, setActiveTestimonial] = useState(0)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeFaq, setActiveFaq] = useState<number | null>(null)
  const [showScrollTop, setShowScrollTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
      setShowScrollTop(window.scrollY > 500)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % 3)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const testimonials = [
    { name: 'Sarah Chen', role: 'QA Lead at TechFlow', text: 'Quathera reduced our form testing time by 80%. The AI discovery is incredibly accurate.', avatar: 'SC' },
    { name: 'Marcus Johnson', role: 'CTO at StartupXYZ', text: 'Finally, a testing tool that actually understands our complex forms. Game changer.', avatar: 'MJ' },
    { name: 'Emily Rodriguez', role: 'Dev Manager at ScaleUp', text: 'We found 47 form issues in the first week that manual testing missed completely.', avatar: 'ER' },
  ]

  const stats = [
    { value: '10x', label: 'Faster Testing' },
    { value: '95%', label: 'Form Detection' },
    { value: '500+', label: 'Companies' },
    { value: '24/7', label: 'AI Monitoring' },
  ]

  const faqs = [
    {
      question: 'How does Quathera discover forms automatically?',
      answer: 'Quathera uses advanced AI vision and smart crawling technology to navigate your web application just like a real user would. It identifies forms, buttons, and interactive elements, then maps out all the form pages in your application automatically.'
    },
    {
      question: 'Do I need to modify my code to use Quathera?',
      answer: 'No! Quathera works with any web application without requiring any code changes. Simply install our lightweight agent, point it to your application URL, and let the AI do the rest.'
    },
    {
      question: 'Is my data secure?',
      answer: 'Absolutely. Quathera runs locally on your infrastructure - your sensitive data never leaves your environment. All communication is encrypted with TLS 1.3, and we follow industry best practices for security.'
    },
    {
      question: 'What types of forms can Quathera test?',
      answer: 'Quathera can test virtually any web form - login forms, registration forms, checkout flows, multi-step wizards, dynamic forms, and more. Our AI adapts to different form structures and validation patterns.'
    },
    {
      question: 'Can I integrate Quathera with my CI/CD pipeline?',
      answer: 'Yes! Quathera provides seamless integration with popular CI/CD tools including GitHub Actions, GitLab CI, Jenkins, CircleCI, and more. Run automated form tests on every deployment.'
    },
    {
      question: 'What happens after my free trial ends?',
      answer: 'After your 14-day free trial, you can choose a plan that fits your needs. There\'s no automatic billing - you\'ll only be charged if you explicitly upgrade. Your test data and configurations are preserved.'
    },
  ]

  const integrations = [
    { name: 'GitHub', icon: '📦' },
    { name: 'GitLab', icon: '🦊' },
    { name: 'Jenkins', icon: '🔧' },
    { name: 'Slack', icon: '💬' },
    { name: 'Jira', icon: '📋' },
    { name: 'CircleCI', icon: '⚡' },
  ]

  const comparisonData = [
    { feature: 'Setup Time', manual: '2-4 weeks', quathera: '5 minutes' },
    { feature: 'Form Discovery', manual: 'Manual mapping', quathera: 'Automatic AI' },
    { feature: 'Test Maintenance', manual: 'High effort', quathera: 'Self-healing' },
    { feature: 'Coverage', manual: '~60%', quathera: '95%+' },
    { feature: 'Cost', manual: '$$$$ (QA team)', quathera: 'Fixed monthly' },
    { feature: 'Speed', manual: 'Hours/Days', quathera: 'Minutes' },
  ]

  return (
    <div className="page-wrapper">
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        html {
          scroll-behavior: smooth;
        }

        body {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          color: #0f172a;
          line-height: 1.6;
          overflow-x: hidden;
        }

        .page-wrapper {
          min-height: 100vh;
        }

        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }

        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 20px rgba(0, 187, 249, 0.3); }
          50% { box-shadow: 0 0 40px rgba(0, 187, 249, 0.6); }
        }

        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-100%); }
          to { opacity: 1; transform: translateX(0); }
        }

        .animate-fade-in {
          animation: fade-in-up 0.8s ease-out forwards;
        }

        .animate-delay-1 { animation-delay: 0.1s; opacity: 0; }
        .animate-delay-2 { animation-delay: 0.2s; opacity: 0; }
        .animate-delay-3 { animation-delay: 0.3s; opacity: 0; }
        .animate-delay-4 { animation-delay: 0.4s; opacity: 0; }

        .nav {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 60px;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 1000;
          transition: all 0.3s ease;
        }

        .nav-scrolled {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(20px);
          box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }

        .nav-transparent {
          background: transparent;
        }

        .nav-links {
          display: flex;
          align-items: center;
          gap: 40px;
        }

        .nav-link {
          color: #475569;
          font-weight: 500;
          text-decoration: none;
          position: relative;
          transition: color 0.3s ease;
        }

        .nav-link:hover {
          color: #00BBF9;
        }

        .nav-link::after {
          content: '';
          position: absolute;
          bottom: -4px;
          left: 0;
          width: 0;
          height: 2px;
          background: linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5);
          transition: width 0.3s ease;
        }

        .nav-link:hover::after {
          width: 100%;
        }

        .mobile-menu-btn {
          display: none;
          flex-direction: column;
          gap: 5px;
          background: none;
          border: none;
          cursor: pointer;
          padding: 10px;
        }

        .mobile-menu-btn span {
          display: block;
          width: 25px;
          height: 3px;
          background: #0f172a;
          border-radius: 3px;
          transition: all 0.3s ease;
        }

        .mobile-menu-btn.active span:nth-child(1) {
          transform: rotate(45deg) translate(5px, 5px);
        }

        .mobile-menu-btn.active span:nth-child(2) {
          opacity: 0;
        }

        .mobile-menu-btn.active span:nth-child(3) {
          transform: rotate(-45deg) translate(7px, -6px);
        }

        .mobile-menu {
          display: none;
          position: fixed;
          top: 70px;
          left: 0;
          right: 0;
          background: white;
          padding: 20px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.1);
          z-index: 999;
          animation: slideIn 0.3s ease;
        }

        .mobile-menu.open {
          display: block;
        }

        .mobile-menu a {
          display: block;
          padding: 15px 20px;
          color: #0f172a;
          text-decoration: none;
          font-weight: 500;
          border-bottom: 1px solid #f1f5f9;
        }

        .mobile-menu a:hover {
          background: #f8fafc;
          color: #00BBF9;
        }

        .btn-primary {
          background: linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%);
          background-size: 200% 200%;
          color: #0A0E17;
          padding: 12px 28px;
          border-radius: 12px;
          font-weight: 600;
          text-decoration: none;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(0, 187, 249, 0.3);
          border: none;
          cursor: pointer;
        }

        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 187, 249, 0.4);
        }

        .btn-secondary {
          background: #fff;
          color: #0A0E17;
          padding: 12px 28px;
          border-radius: 12px;
          font-weight: 600;
          border: 2px solid #e2e8f0;
          text-decoration: none;
          transition: all 0.3s ease;
          cursor: pointer;
        }

        .btn-secondary:hover {
          border-color: #00BBF9;
          box-shadow: 0 4px 15px rgba(0, 187, 249, 0.2);
        }

        .btn-large {
          padding: 18px 40px;
          font-size: 18px;
        }

        .hero {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
          background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 50%, #f5f3ff 100%);
        }

        .hero-bg-pattern {
          position: absolute;
          inset: 0;
          background-image: 
            radial-gradient(circle at 20% 50%, rgba(0, 187, 249, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(155, 93, 229, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 40% 80%, rgba(0, 245, 212, 0.08) 0%, transparent 50%);
        }

        .hero-grid {
          position: absolute;
          inset: 0;
          background-size: 60px 60px;
          background-image: 
            linear-gradient(to right, rgba(0, 0, 0, 0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
        }

        .hero-content {
          position: relative;
          z-index: 10;
          text-align: center;
          padding: 120px 60px 80px;
          max-width: 900px;
        }

        .hero-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(0, 187, 249, 0.1);
          border: 1px solid rgba(0, 187, 249, 0.3);
          padding: 8px 20px;
          border-radius: 50px;
          font-size: 14px;
          font-weight: 500;
          color: #0077b6;
          margin-bottom: 32px;
        }

        .hero-badge-dot {
          width: 8px;
          height: 8px;
          background: #00F5D4;
          border-radius: 50%;
          animation: pulse-glow 2s ease infinite;
        }

        .hero-title {
          font-size: 72px;
          font-weight: 800;
          line-height: 1.1;
          margin-bottom: 28px;
          letter-spacing: -2px;
        }

        .hero-title-gradient {
          background: linear-gradient(135deg, #00F5D4 0%, #00BBF9 40%, #9B5DE5 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-subtitle {
          font-size: 22px;
          color: #64748b;
          max-width: 650px;
          margin: 0 auto 48px;
          line-height: 1.7;
        }

        .hero-buttons {
          display: flex;
          gap: 20px;
          justify-content: center;
          margin-bottom: 60px;
        }

        .hero-stats {
          display: flex;
          justify-content: center;
          gap: 60px;
          padding-top: 40px;
          border-top: 1px solid rgba(0, 0, 0, 0.08);
        }

        .hero-stat {
          text-align: center;
        }

        .hero-stat-value {
          font-size: 36px;
          font-weight: 800;
          background: linear-gradient(135deg, #00BBF9, #9B5DE5);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-stat-label {
          font-size: 14px;
          color: #64748b;
          font-weight: 500;
        }

        .floating-element {
          position: absolute;
          border-radius: 16px;
          background: white;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
          padding: 16px 24px;
          animation: float 6s ease-in-out infinite;
          display: flex;
          align-items: center;
          gap: 12px;
          font-weight: 600;
          font-size: 14px;
        }

        .floating-element-1 { top: 25%; left: 8%; animation-delay: 0s; }
        .floating-element-2 { top: 35%; right: 8%; animation-delay: 2s; }
        .floating-element-3 { bottom: 25%; left: 12%; animation-delay: 4s; }

        .trusted-section {
          padding: 60px;
          background: #fff;
          border-bottom: 1px solid #f1f5f9;
        }

        .trusted-title {
          text-align: center;
          font-size: 14px;
          text-transform: uppercase;
          letter-spacing: 2px;
          color: #94a3b8;
          margin-bottom: 40px;
        }

        .trusted-logos {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 60px;
          flex-wrap: wrap;
        }

        .trusted-logo {
          font-size: 20px;
          font-weight: 700;
          color: #cbd5e1;
          transition: color 0.3s ease;
        }

        .trusted-logo:hover { color: #94a3b8; }

        .section {
          padding: 120px 60px;
        }

        .section-dark {
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          position: relative;
          overflow: hidden;
        }

        .section-dark::before {
          content: '';
          position: absolute;
          inset: 0;
          background-image: 
            radial-gradient(circle at 20% 50%, rgba(0, 187, 249, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(155, 93, 229, 0.1) 0%, transparent 50%);
        }

        .section-light {
          background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%);
        }

        .section-header {
          text-align: center;
          max-width: 700px;
          margin: 0 auto 80px;
          position: relative;
          z-index: 10;
        }

        .section-badge {
          display: inline-block;
          background: linear-gradient(135deg, rgba(0, 245, 212, 0.1), rgba(0, 187, 249, 0.1));
          color: #0077b6;
          padding: 8px 20px;
          border-radius: 50px;
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 20px;
        }

        .section-badge-dark {
          background: rgba(0, 187, 249, 0.2);
          color: #00F5D4;
        }

        .section-title {
          font-size: 48px;
          font-weight: 800;
          margin-bottom: 20px;
          letter-spacing: -1px;
        }

        .section-title-dark { color: #fff; }

        .section-subtitle {
          font-size: 18px;
          color: #64748b;
          line-height: 1.7;
        }

        .section-subtitle-dark { color: #94a3b8; }

        .demo-section {
          padding: 120px 60px;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          position: relative;
          overflow: hidden;
        }

        .demo-container {
          max-width: 1000px;
          margin: 0 auto;
          position: relative;
          z-index: 10;
        }

        .demo-video-wrapper {
          position: relative;
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 40px 100px rgba(0, 0, 0, 0.4);
          background: #1e293b;
          aspect-ratio: 16/9;
        }

        .demo-video-placeholder {
          position: absolute;
          inset: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        }

        .demo-play-btn {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00F5D4 0%, #00BBF9 50%, #9B5DE5 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.3s ease;
          border: none;
          margin-bottom: 20px;
        }

        .demo-play-btn:hover {
          transform: scale(1.1);
          box-shadow: 0 0 60px rgba(0, 187, 249, 0.5);
        }

        .demo-play-btn::after {
          content: '';
          border-style: solid;
          border-width: 15px 0 15px 25px;
          border-color: transparent transparent transparent #0f172a;
          margin-left: 5px;
        }

        .demo-text { color: #94a3b8; font-size: 18px; }

        .demo-browser-bar {
          height: 40px;
          background: #0f172a;
          display: flex;
          align-items: center;
          padding: 0 16px;
          gap: 8px;
        }

        .demo-browser-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }

        .products-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 32px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .product-card {
          position: relative;
          padding: 48px 36px;
          border-radius: 24px;
          background: #fff;
          border: 1px solid #e2e8f0;
          transition: all 0.4s ease;
          overflow: hidden;
        }

        .product-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5);
          transform: scaleX(0);
          transition: transform 0.4s ease;
        }

        .product-card:hover {
          transform: translateY(-8px);
          box-shadow: 0 25px 80px rgba(0, 0, 0, 0.12);
          border-color: transparent;
        }

        .product-card:hover::before { transform: scaleX(1); }

        .product-card-featured {
          border: 2px solid #00BBF9;
          background: linear-gradient(135deg, #f0f9ff 0%, #faf5ff 100%);
        }

        .product-card-featured::before { transform: scaleX(1); }

        .product-icon {
          width: 72px;
          height: 72px;
          border-radius: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 32px;
          margin-bottom: 28px;
          background: linear-gradient(135deg, #f0f9ff, #faf5ff);
        }

        .product-title { font-size: 24px; font-weight: 700; margin-bottom: 16px; }
        .product-description { color: #64748b; margin-bottom: 24px; line-height: 1.7; }
        .product-features { list-style: none; margin-bottom: 28px; }

        .product-feature {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 0;
          color: #475569;
          font-size: 15px;
        }

        .product-feature-check {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00F5D4, #00BBF9);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: white;
          flex-shrink: 0;
        }

        .product-link {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: #00BBF9;
          font-weight: 600;
          text-decoration: none;
          transition: gap 0.3s ease;
        }

        .product-link:hover { gap: 12px; }

        .coming-soon-badge {
          display: inline-block;
          background: #f1f5f9;
          color: #64748b;
          padding: 6px 16px;
          border-radius: 50px;
          font-size: 13px;
          font-weight: 600;
        }

        .comparison-section { padding: 120px 60px; background: #fff; }

        .comparison-table {
          max-width: 900px;
          margin: 0 auto;
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
        }

        .comparison-header {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          color: white;
          font-weight: 700;
        }

        .comparison-header > div { padding: 24px 32px; text-align: center; }
        .comparison-header > div:first-child { text-align: left; }

        .comparison-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          border-bottom: 1px solid #f1f5f9;
        }

        .comparison-row:last-child { border-bottom: none; }
        .comparison-row > div { padding: 20px 32px; display: flex; align-items: center; }
        .comparison-row > div:first-child { font-weight: 600; color: #0f172a; }
        .comparison-row > div:nth-child(2) { justify-content: center; color: #94a3b8; background: #fafafa; }
        .comparison-row > div:nth-child(3) { justify-content: center; color: #00BBF9; font-weight: 600; background: rgba(0, 187, 249, 0.05); }

        .steps-container {
          display: flex;
          justify-content: center;
          gap: 40px;
          max-width: 1100px;
          margin: 0 auto;
          position: relative;
          z-index: 10;
        }

        .step-card { flex: 1; text-align: center; }

        .step-number {
          width: 100px;
          height: 100px;
          border-radius: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 28px;
          font-size: 40px;
          font-weight: 800;
          color: #0f172a;
        }

        .step-number-1 { background: linear-gradient(135deg, #00F5D4, #00BBF9); }
        .step-number-2 { background: linear-gradient(135deg, #00BBF9, #9B5DE5); }
        .step-number-3 { background: linear-gradient(135deg, #9B5DE5, #7C3AED); }
        .step-number-4 { background: linear-gradient(135deg, #7C3AED, #EC4899); }

        .step-title { font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 12px; }
        .step-description { color: #94a3b8; font-size: 16px; line-height: 1.6; }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 40px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .feature-card {
          padding: 40px;
          border-radius: 20px;
          background: #fff;
          border: 1px solid #e2e8f0;
          transition: all 0.3s ease;
        }

        .feature-card:hover {
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
          transform: translateY(-4px);
        }

        .feature-icon {
          width: 56px;
          height: 56px;
          border-radius: 16px;
          background: linear-gradient(135deg, rgba(0, 245, 212, 0.1), rgba(0, 187, 249, 0.1));
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          margin-bottom: 24px;
        }

        .feature-title { font-size: 20px; font-weight: 700; margin-bottom: 12px; }
        .feature-description { color: #64748b; line-height: 1.7; }

        .integrations-section {
          padding: 100px 60px;
          background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%);
        }

        .integrations-grid {
          display: flex;
          justify-content: center;
          gap: 40px;
          flex-wrap: wrap;
          max-width: 900px;
          margin: 0 auto;
        }

        .integration-card {
          width: 140px;
          height: 140px;
          background: white;
          border-radius: 20px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
        }

        .integration-card:hover {
          transform: translateY(-8px);
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
        }

        .integration-icon { font-size: 40px; }
        .integration-name { font-weight: 600; color: #475569; font-size: 14px; }

        .security-section {
          padding: 80px 60px;
          background: #fff;
          border-top: 1px solid #f1f5f9;
          border-bottom: 1px solid #f1f5f9;
        }

        .security-container {
          max-width: 1000px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 60px;
        }

        .security-text h3 { font-size: 28px; font-weight: 700; margin-bottom: 12px; }
        .security-text p { color: #64748b; max-width: 500px; }

        .security-badges { display: flex; gap: 24px; }

        .security-badge {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 20px 30px;
          background: #f8fafc;
          border-radius: 16px;
          border: 1px solid #e2e8f0;
        }

        .security-badge-icon { font-size: 32px; }
        .security-badge-text { font-size: 12px; font-weight: 600; color: #475569; text-align: center; }

        .faq-section { padding: 120px 60px; background: #fff; }
        .faq-container { max-width: 800px; margin: 0 auto; }
        .faq-item { border-bottom: 1px solid #e2e8f0; }

        .faq-question {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px 0;
          background: none;
          border: none;
          text-align: left;
          font-size: 18px;
          font-weight: 600;
          color: #0f172a;
          cursor: pointer;
          transition: color 0.3s ease;
        }

        .faq-question:hover { color: #00BBF9; }

        .faq-icon {
          font-size: 24px;
          transition: transform 0.3s ease;
          color: #00BBF9;
        }

        .faq-icon.open { transform: rotate(45deg); }

        .faq-answer {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease, padding 0.3s ease;
        }

        .faq-answer.open { max-height: 300px; padding-bottom: 24px; }
        .faq-answer p { color: #64748b; line-height: 1.8; }

        .testimonials-container { max-width: 800px; margin: 0 auto; }

        .testimonial-card {
          background: #fff;
          border-radius: 24px;
          padding: 60px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
          text-align: center;
          position: relative;
        }

        .testimonial-quote {
          font-size: 24px;
          font-weight: 500;
          line-height: 1.6;
          color: #1e293b;
          margin-bottom: 40px;
          font-style: italic;
        }

        .testimonial-quote::before {
          content: '"';
          position: absolute;
          top: 30px;
          left: 50px;
          font-size: 100px;
          color: #00BBF9;
          opacity: 0.15;
          font-family: Georgia, serif;
        }

        .testimonial-author { display: flex; align-items: center; justify-content: center; gap: 16px; }

        .testimonial-avatar {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-weight: 700;
          font-size: 18px;
        }

        .testimonial-info { text-align: left; }
        .testimonial-name { font-weight: 700; font-size: 18px; }
        .testimonial-role { color: #64748b; font-size: 14px; }

        .testimonial-dots { display: flex; justify-content: center; gap: 12px; margin-top: 40px; }

        .testimonial-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #e2e8f0;
          cursor: pointer;
          transition: all 0.3s ease;
          border: none;
        }

        .testimonial-dot-active {
          background: linear-gradient(135deg, #00BBF9, #9B5DE5);
          transform: scale(1.2);
        }

        .cta-section {
          padding: 120px 60px;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          text-align: center;
          position: relative;
          overflow: hidden;
        }

        .cta-section::before {
          content: '';
          position: absolute;
          inset: 0;
          background-image: 
            radial-gradient(circle at 30% 30%, rgba(0, 245, 212, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 70% 70%, rgba(155, 93, 229, 0.15) 0%, transparent 50%);
        }

        .cta-content { position: relative; z-index: 10; max-width: 700px; margin: 0 auto; }
        .cta-title { font-size: 48px; font-weight: 800; color: #fff; margin-bottom: 20px; letter-spacing: -1px; }
        .cta-subtitle { font-size: 20px; color: #94a3b8; margin-bottom: 48px; }
        .cta-buttons { display: flex; gap: 20px; justify-content: center; }
        .cta-features { display: flex; justify-content: center; gap: 40px; margin-top: 48px; flex-wrap: wrap; }
        .cta-feature { display: flex; align-items: center; gap: 8px; color: #94a3b8; font-size: 14px; }
        .cta-feature-icon { color: #00F5D4; }

        .scroll-top-btn {
          position: fixed;
          bottom: 30px;
          right: 30px;
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00F5D4, #00BBF9, #9B5DE5);
          color: #0f172a;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          box-shadow: 0 4px 20px rgba(0, 187, 249, 0.3);
          transition: all 0.3s ease;
          z-index: 1000;
          opacity: 0;
          visibility: hidden;
        }

        .scroll-top-btn.visible { opacity: 1; visibility: visible; }
        .scroll-top-btn:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(0, 187, 249, 0.5); }

        .footer { padding: 80px 60px 40px; background: #050709; }

        .footer-grid {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 60px;
          max-width: 1200px;
          margin: 0 auto 60px;
        }

        .footer-brand { max-width: 300px; }
        .footer-logo { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 16px; }
        .footer-description { color: #64748b; line-height: 1.7; margin-bottom: 20px; }

        .footer-social-links { display: flex; gap: 16px; }

        .footer-social-link {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          background: #1e293b;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #94a3b8;
          text-decoration: none;
          transition: all 0.3s ease;
        }

        .footer-social-link:hover { background: linear-gradient(135deg, #00F5D4, #00BBF9); color: #0f172a; }

        .footer-column h4 {
          color: #fff;
          font-size: 14px;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 24px;
        }

        .footer-links { list-style: none; }
        .footer-links li { margin-bottom: 12px; }
        .footer-links a { color: #64748b; text-decoration: none; transition: color 0.3s ease; }
        .footer-links a:hover { color: #00BBF9; }

        .footer-bottom {
          border-top: 1px solid #1e293b;
          padding-top: 40px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          max-width: 1200px;
          margin: 0 auto;
        }

        .footer-copyright { color: #64748b; font-size: 14px; }
        .footer-legal-links { display: flex; gap: 30px; }
        .footer-legal-links a { color: #64748b; text-decoration: none; font-size: 14px; transition: color 0.3s ease; }
        .footer-legal-links a:hover { color: #00BBF9; }

        @media (max-width: 1024px) {
          .products-grid, .features-grid { grid-template-columns: 1fr; max-width: 500px; }
          .steps-container { flex-direction: column; gap: 40px; }
          .footer-grid { grid-template-columns: 1fr 1fr; }
          .comparison-header, .comparison-row { grid-template-columns: 1.5fr 1fr 1fr; }
          .security-container { flex-direction: column; text-align: center; }
          .security-text { text-align: center; }
          .security-text p { margin: 0 auto; }
        }

        @media (max-width: 768px) {
          .nav { padding: 16px 24px; }
          .nav-links { display: none; }
          .mobile-menu-btn { display: flex; }
          .hero-title { font-size: 42px; }
          .hero-content { padding: 100px 24px 60px; }
          .hero-buttons { flex-direction: column; align-items: center; }
          .hero-stats { flex-wrap: wrap; gap: 30px; }
          .section { padding: 80px 24px; }
          .section-title { font-size: 32px; }
          .floating-element { display: none; }
          .footer-grid { grid-template-columns: 1fr; }
          .footer-bottom { flex-direction: column; gap: 20px; text-align: center; }
          .footer-legal-links { flex-wrap: wrap; justify-content: center; }
          .cta-buttons { flex-direction: column; align-items: center; }
          .comparison-header, .comparison-row { font-size: 14px; }
          .comparison-header > div, .comparison-row > div { padding: 16px; }
          .security-badges { flex-direction: column; }
          .integrations-grid { gap: 20px; }
          .integration-card { width: 100px; height: 100px; }
          .cta-title { font-size: 32px; }
        }
      `}</style>

      {/* Navigation */}
      <nav className={`nav ${scrolled ? 'nav-scrolled' : 'nav-transparent'}`}>
        <Link href="/">
          <svg width="180" height="45" viewBox="0 0 180 45" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{stopColor:'#00F5D4'}}/>
                <stop offset="50%" style={{stopColor:'#00BBF9'}}/>
                <stop offset="100%" style={{stopColor:'#9B5DE5'}}/>
              </linearGradient>
            </defs>
            <circle cx="22" cy="22" r="18" fill="none" stroke="url(#logoGrad)" strokeWidth="3"/>
            <circle cx="22" cy="22" r="6" fill="url(#logoGrad)"/>
            <path d="M 30 30 L 40 38" stroke="url(#logoGrad)" strokeWidth="3" strokeLinecap="round"/>
            <text x="50" y="30" fontFamily="Inter, sans-serif" fontSize="24" fontWeight="700" fill="#0f172a">
              <tspan fill="url(#logoGrad)">Q</tspan>uathera
            </text>
          </svg>
        </Link>
        <div className="nav-links">
          <Link href="#products" className="nav-link">Products</Link>
          <Link href="#how-it-works" className="nav-link">How It Works</Link>
          <Link href="#faq" className="nav-link">FAQ</Link>
          <Link href="/pricing" className="nav-link">Pricing</Link>
          <Link href="/login" className="nav-link">Login</Link>
          <Link href="/signup" className="btn-primary">Start Free Trial</Link>
        </div>
        <button className={`mobile-menu-btn ${mobileMenuOpen ? 'active' : ''}`} onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          <span></span><span></span><span></span>
        </button>
      </nav>

      {/* Mobile Menu */}
      <div className={`mobile-menu ${mobileMenuOpen ? 'open' : ''}`}>
        <Link href="#products" onClick={() => setMobileMenuOpen(false)}>Products</Link>
        <Link href="#how-it-works" onClick={() => setMobileMenuOpen(false)}>How It Works</Link>
        <Link href="#faq" onClick={() => setMobileMenuOpen(false)}>FAQ</Link>
        <Link href="/pricing" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
        <Link href="/login" onClick={() => setMobileMenuOpen(false)}>Login</Link>
        <Link href="/signup" onClick={() => setMobileMenuOpen(false)}>Start Free Trial</Link>
      </div>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-bg-pattern"></div>
        <div className="hero-grid"></div>
        <div className="floating-element floating-element-1"><span>✓</span><span>Form Discovered</span></div>
        <div className="floating-element floating-element-2"><span>🤖</span><span>AI Testing Active</span></div>
        <div className="floating-element floating-element-3"><span>🛡️</span><span>100% Coverage</span></div>

        <div className="hero-content">
          <div className="hero-badge animate-fade-in">
            <span className="hero-badge-dot"></span>
            Now with AI Vision & Smart Crawling
          </div>
          <h1 className="hero-title animate-fade-in animate-delay-1">
            AI-Powered Web Testing<br /><span className="hero-title-gradient">Fully Automated</span>
          </h1>
          <p className="hero-subtitle animate-fade-in animate-delay-2">
            Discover and test every form in your web application automatically. Our AI handles the tedious work so you can focus on building amazing products.
          </p>
          <div className="hero-buttons animate-fade-in animate-delay-3">
            <Link href="/signup" className="btn-primary btn-large">Start Free Trial →</Link>
            <Link href="#demo" className="btn-secondary btn-large">Watch Demo</Link>
          </div>
          <div className="hero-stats animate-fade-in animate-delay-4">
            {stats.map((stat, i) => (
              <div key={i} className="hero-stat">
                <div className="hero-stat-value">{stat.value}</div>
                <div className="hero-stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trusted By */}
      <section className="trusted-section">
        <p className="trusted-title">Trusted by innovative teams worldwide</p>
        <div className="trusted-logos">
          <span className="trusted-logo">TechFlow</span>
          <span className="trusted-logo">ScaleUp</span>
          <span className="trusted-logo">DataCore</span>
          <span className="trusted-logo">CloudNine</span>
          <span className="trusted-logo">DevFirst</span>
        </div>
      </section>

      {/* Demo Video Section */}
      <section id="demo" className="demo-section">
        <div className="section-header">
          <span className="section-badge section-badge-dark">See It In Action</span>
          <h2 className="section-title section-title-dark">Watch Quathera Discover Forms</h2>
          <p className="section-subtitle section-subtitle-dark">See how our AI automatically crawls and discovers every form in your application</p>
        </div>
        <div className="demo-container">
          <div className="demo-video-wrapper">
            <div className="demo-browser-bar">
              <div className="demo-browser-dot" style={{background: '#ff5f57'}}></div>
              <div className="demo-browser-dot" style={{background: '#ffbd2e'}}></div>
              <div className="demo-browser-dot" style={{background: '#28ca41'}}></div>
            </div>
            <div className="demo-video-placeholder">
              <button className="demo-play-btn" aria-label="Play demo video"></button>
              <span className="demo-text">Click to play demo</span>
            </div>
          </div>
        </div>
      </section>

      {/* Products Section */}
      <section id="products" className="section">
        <div className="section-header">
          <span className="section-badge">Our Products</span>
          <h2 className="section-title">Everything You Need for Web Testing</h2>
          <p className="section-subtitle">Comprehensive testing solutions powered by cutting-edge AI technology</p>
        </div>
        <div className="products-grid">
          <div className="product-card product-card-featured">
            <div className="product-icon">📋</div>
            <h3 className="product-title">Form Pages Testing</h3>
            <p className="product-description">Automatically discover all form pages in your application. AI-powered crawling identifies forms, fields, and validation rules.</p>
            <ul className="product-features">
              <li className="product-feature"><span className="product-feature-check">✓</span>Auto-discovery of all forms</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Smart field detection</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Validation testing</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Edge case generation</li>
            </ul>
            <Link href="/pricing" className="product-link">Get Started →</Link>
          </div>
          <div className="product-card">
            <div className="product-icon">🛒</div>
            <h3 className="product-title">Shopping Site Testing</h3>
            <p className="product-description">End-to-end e-commerce testing. From product browsing to checkout flow, ensure your customers have a smooth experience.</p>
            <ul className="product-features">
              <li className="product-feature"><span className="product-feature-check">✓</span>Cart functionality</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Checkout flows</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Payment integration</li>
            </ul>
            <span className="coming-soon-badge">Coming Soon</span>
          </div>
          <div className="product-card">
            <div className="product-icon">📊</div>
            <h3 className="product-title">Marketing Website Testing</h3>
            <p className="product-description">Validate your marketing pages, landing pages, and content. Ensure links work and forms capture leads properly.</p>
            <ul className="product-features">
              <li className="product-feature"><span className="product-feature-check">✓</span>Link validation</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>Lead form testing</li>
              <li className="product-feature"><span className="product-feature-check">✓</span>SEO checks</li>
            </ul>
            <span className="coming-soon-badge">Coming Soon</span>
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="comparison-section">
        <div className="section-header">
          <span className="section-badge">Why Switch</span>
          <h2 className="section-title">Quathera vs Manual Testing</h2>
          <p className="section-subtitle">See how Quathera transforms your testing workflow</p>
        </div>
        <div className="comparison-table">
          <div className="comparison-header">
            <div>Feature</div>
            <div>Manual Testing</div>
            <div>Quathera</div>
          </div>
          {comparisonData.map((row, i) => (
            <div key={i} className="comparison-row">
              <div>{row.feature}</div>
              <div>{row.manual}</div>
              <div>{row.quathera}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="section section-dark">
        <div className="section-header">
          <span className="section-badge section-badge-dark">How It Works</span>
          <h2 className="section-title section-title-dark">Get Started in Minutes</h2>
          <p className="section-subtitle section-subtitle-dark">Simple setup, powerful results. No complex configuration needed.</p>
        </div>
        <div className="steps-container">
          <div className="step-card"><div className="step-number step-number-1">1</div><h3 className="step-title">Install Agent</h3><p className="step-description">Download and run our lightweight agent on your machine. One-click installation.</p></div>
          <div className="step-card"><div className="step-number step-number-2">2</div><h3 className="step-title">Add Your Site</h3><p className="step-description">Configure your web application URL and test credentials securely.</p></div>
          <div className="step-card"><div className="step-number step-number-3">3</div><h3 className="step-title">AI Discovers</h3><p className="step-description">Our AI crawls your site and discovers all form pages automatically.</p></div>
          <div className="step-card"><div className="step-number step-number-4">4</div><h3 className="step-title">Get Reports</h3><p className="step-description">Receive detailed reports with issues, screenshots, and fix suggestions.</p></div>
        </div>
      </section>

      {/* Features Section */}
      <section className="section section-light">
        <div className="section-header">
          <span className="section-badge">Why Quathera</span>
          <h2 className="section-title">Built for Modern Development Teams</h2>
          <p className="section-subtitle">Everything you need to ensure quality without slowing down development</p>
        </div>
        <div className="features-grid">
          <div className="feature-card"><div className="feature-icon">🧠</div><h3 className="feature-title">AI-Powered Discovery</h3><p className="feature-description">Our AI understands your application structure and finds every form, even dynamically generated ones.</p></div>
          <div className="feature-card"><div className="feature-icon">⚡</div><h3 className="feature-title">Lightning Fast</h3><p className="feature-description">Run thousands of test scenarios in minutes, not hours. Parallel execution for maximum speed.</p></div>
          <div className="feature-card"><div className="feature-icon">🔒</div><h3 className="feature-title">Secure by Design</h3><p className="feature-description">Your data never leaves your infrastructure. Agent runs locally with encrypted communication.</p></div>
          <div className="feature-card"><div className="feature-icon">📸</div><h3 className="feature-title">Visual Evidence</h3><p className="feature-description">Every test includes screenshots and video recordings for easy debugging.</p></div>
          <div className="feature-card"><div className="feature-icon">🔄</div><h3 className="feature-title">CI/CD Integration</h3><p className="feature-description">Seamlessly integrate with your existing pipeline. GitHub, GitLab, Jenkins supported.</p></div>
          <div className="feature-card"><div className="feature-icon">📈</div><h3 className="feature-title">Smart Analytics</h3><p className="feature-description">Track test coverage, find patterns in failures, and improve over time.</p></div>
        </div>
      </section>

      {/* Integrations Section */}
      <section className="integrations-section">
        <div className="section-header">
          <span className="section-badge">Integrations</span>
          <h2 className="section-title">Works With Your Tools</h2>
          <p className="section-subtitle">Seamlessly integrate with your existing development workflow</p>
        </div>
        <div className="integrations-grid">
          {integrations.map((integration, i) => (
            <div key={i} className="integration-card">
              <span className="integration-icon">{integration.icon}</span>
              <span className="integration-name">{integration.name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Security Section */}
      <section className="security-section">
        <div className="security-container">
          <div className="security-text">
            <h3>Enterprise-Grade Security</h3>
            <p>Your data stays on your infrastructure. We follow industry best practices to keep your tests and results secure.</p>
          </div>
          <div className="security-badges">
            <div className="security-badge"><span className="security-badge-icon">🔐</span><span className="security-badge-text">TLS 1.3<br/>Encryption</span></div>
            <div className="security-badge"><span className="security-badge-icon">🏠</span><span className="security-badge-text">On-Premise<br/>Agent</span></div>
            <div className="security-badge"><span className="security-badge-icon">✅</span><span className="security-badge-text">SOC 2<br/>Compliant</span></div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="section">
        <div className="section-header">
          <span className="section-badge">Testimonials</span>
          <h2 className="section-title">Loved by QA Teams</h2>
          <p className="section-subtitle">See what our customers have to say about Quathera</p>
        </div>
        <div className="testimonials-container">
          <div className="testimonial-card">
            <p className="testimonial-quote">{testimonials[activeTestimonial].text}</p>
            <div className="testimonial-author">
              <div className="testimonial-avatar">{testimonials[activeTestimonial].avatar}</div>
              <div className="testimonial-info">
                <div className="testimonial-name">{testimonials[activeTestimonial].name}</div>
                <div className="testimonial-role">{testimonials[activeTestimonial].role}</div>
              </div>
            </div>
          </div>
          <div className="testimonial-dots">
            {testimonials.map((_, i) => (<button key={i} className={`testimonial-dot ${i === activeTestimonial ? 'testimonial-dot-active' : ''}`} onClick={() => setActiveTestimonial(i)}/>))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="faq-section">
        <div className="section-header">
          <span className="section-badge">FAQ</span>
          <h2 className="section-title">Frequently Asked Questions</h2>
          <p className="section-subtitle">Everything you need to know about Quathera</p>
        </div>
        <div className="faq-container">
          {faqs.map((faq, i) => (
            <div key={i} className="faq-item">
              <button className="faq-question" onClick={() => setActiveFaq(activeFaq === i ? null : i)}>
                {faq.question}
                <span className={`faq-icon ${activeFaq === i ? 'open' : ''}`}>+</span>
              </button>
              <div className={`faq-answer ${activeFaq === i ? 'open' : ''}`}><p>{faq.answer}</p></div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Ready to Get Started?</h2>
          <p className="cta-subtitle">Start your 14-day free trial today. No credit card required.</p>
          <div className="cta-buttons">
            <Link href="/signup" className="btn-primary btn-large">Start Free Trial →</Link>
            <Link href="/pricing" className="btn-secondary btn-large">View Pricing</Link>
          </div>
          <div className="cta-features">
            <div className="cta-feature"><span className="cta-feature-icon">✓</span>14-day free trial</div>
            <div className="cta-feature"><span className="cta-feature-icon">✓</span>No credit card required</div>
            <div className="cta-feature"><span className="cta-feature-icon">✓</span>Cancel anytime</div>
            <div className="cta-feature"><span className="cta-feature-icon">✓</span>Full feature access</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="footer-logo">Quathera</div>
            <p className="footer-description">AI-powered web testing automation. Discover and test forms automatically, so you can focus on building great products.</p>
            <div className="footer-social-links">
              <a href="#" className="footer-social-link" aria-label="Twitter">𝕏</a>
              <a href="#" className="footer-social-link" aria-label="LinkedIn">in</a>
              <a href="#" className="footer-social-link" aria-label="GitHub">⌘</a>
            </div>
          </div>
          <div className="footer-column">
            <h4>Product</h4>
            <ul className="footer-links">
              <li><Link href="#products">Features</Link></li>
              <li><Link href="/pricing">Pricing</Link></li>
              <li><Link href="#how-it-works">How It Works</Link></li>
              <li><a href="#">Documentation</a></li>
              <li><a href="#">API Reference</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h4>Company</h4>
            <ul className="footer-links">
              <li><a href="#">About Us</a></li>
              <li><a href="#">Blog</a></li>
              <li><a href="#">Careers</a></li>
              <li><a href="#">Press Kit</a></li>
              <li><a href="#">Contact</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h4>Resources</h4>
            <ul className="footer-links">
              <li><a href="#">Help Center</a></li>
              <li><a href="#">Community</a></li>
              <li><a href="#">Webinars</a></li>
              <li><a href="#">Status Page</a></li>
              <li><Link href="#faq">FAQ</Link></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p className="footer-copyright">© 2025 Quathera. All rights reserved. | Patent Pending</p>
          <div className="footer-legal-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Cookie Policy</a>
            <a href="#">Security</a>
          </div>
        </div>
      </footer>

      {/* Scroll to Top Button */}
      <button className={`scroll-top-btn ${showScrollTop ? 'visible' : ''}`} onClick={scrollToTop} aria-label="Scroll to top">↑</button>
    </div>
  )
}
