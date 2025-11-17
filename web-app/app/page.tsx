export default function Home() {
  return (
    <div style={{ fontFamily: 'Arial, sans-serif' }}>
      {/* Navigation */}
      <nav style={{
        padding: '20px 40px',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#0070f3' }}>
          Form Discoverer
        </div>
        <div style={{ display: 'flex', gap: '25px', alignItems: 'center' }}>
          <a href="/features" style={navLink}>Features</a>
          <a href="/pricing" style={navLink}>Pricing</a>
          <a href="/about" style={navLink}>About</a>
          <a href="/login" style={{
            ...navLink,
            background: '#0070f3',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '5px'
          }}>Login</a>
        </div>
      </nav>

      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '80px 40px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}>
        <h1 style={{ fontSize: '52px', marginBottom: '20px', fontWeight: 'bold' }}>
          AI-Powered Form Discovery
        </h1>
        <p style={{ fontSize: '24px', marginBottom: '40px', opacity: 0.9 }}>
          Automatically discover, analyze, and test all forms in your web application
        </p>
        <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <a href="/signup" style={{
            background: 'white',
            color: '#667eea',
            padding: '15px 30px',
            textDecoration: 'none',
            borderRadius: '6px',
            fontSize: '18px',
            fontWeight: 'bold'
          }}>
            Start Free Trial
          </a>
          <a href="/features" style={{
            background: 'transparent',
            color: 'white',
            padding: '15px 30px',
            textDecoration: 'none',
            borderRadius: '6px',
            border: '2px solid white',
            fontSize: '18px',
            fontWeight: 'bold'
          }}>
            Learn More
          </a>
        </div>
      </div>

      {/* Features Highlight */}
      <div style={{ padding: '60px 40px', maxWidth: '1200px', margin: '0 auto' }}>
        <h2 style={{ textAlign: 'center', fontSize: '36px', marginBottom: '50px' }}>
          Why Form Discoverer?
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '40px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>🤖</div>
            <h3 style={{ fontSize: '20px', marginBottom: '10px' }}>AI-Powered</h3>
            <p style={{ color: '#666' }}>Claude AI automatically discovers and analyzes all forms</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>⚡</div>
            <h3 style={{ fontSize: '20px', marginBottom: '10px' }}>Save Time</h3>
            <p style={{ color: '#666' }}>Automate days of manual work into minutes</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>🔒</div>
            <h3 style={{ fontSize: '20px', marginBottom: '10px' }}>Secure</h3>
            <p style={{ color: '#666' }}>Agent runs on your desktop, data stays private</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>💰</div>
            <h3 style={{ fontSize: '20px', marginBottom: '10px' }}>Cost Optimized</h3>
            <p style={{ color: '#666' }}>Smart caching reduces API costs by 85%</p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div style={{ background: '#f9fafb', padding: '60px 40px' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <h2 style={{ textAlign: 'center', fontSize: '36px', marginBottom: '50px' }}>
            How It Works
          </h2>
          <div style={{ display: 'grid', gap: '30px' }}>
            <div style={stepCard}>
              <div style={stepNumber}>1</div>
              <h3>Download Agent</h3>
              <p>Install our lightweight desktop application</p>
            </div>
            <div style={stepCard}>
              <div style={stepNumber}>2</div>
              <h3>Configure Target</h3>
              <p>Point the agent to your web application</p>
            </div>
            <div style={stepCard}>
              <div style={stepNumber}>3</div>
              <h3>AI Discovery</h3>
              <p>Claude AI crawls and discovers all forms</p>
            </div>
            <div style={stepCard}>
              <div style={stepNumber}>4</div>
              <h3>View Results</h3>
              <p>Get detailed analysis and test recommendations</p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div style={{
        textAlign: 'center',
        padding: '80px 40px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}>
        <h2 style={{ fontSize: '36px', marginBottom: '20px' }}>Ready to Get Started?</h2>
        <p style={{ fontSize: '18px', marginBottom: '30px', opacity: 0.9 }}>
          Join teams who are already saving time with AI-powered form discovery
        </p>
        <a href="/signup" style={{
          background: 'white',
          color: '#667eea',
          padding: '15px 30px',
          textDecoration: 'none',
          borderRadius: '6px',
          fontSize: '18px',
          fontWeight: 'bold',
          display: 'inline-block'
        }}>
          Start Free Trial
        </a>
      </div>

      {/* Footer */}
      <div style={{
        padding: '40px',
        borderTop: '1px solid #e5e7eb',
        textAlign: 'center',
        color: '#666'
      }}>
        <div style={{ marginBottom: '20px' }}>
          <a href="/features" style={{ ...footerLink, marginRight: '20px' }}>Features</a>
          <a href="/pricing" style={{ ...footerLink, marginRight: '20px' }}>Pricing</a>
          <a href="/about" style={{ ...footerLink, marginRight: '20px' }}>About</a>
          <a href="/login" style={footerLink}>Login</a>
        </div>
        <p style={{ fontSize: '14px' }}>© 2025 Form Discoverer. All rights reserved.</p>
      </div>
    </div>
  )
}

const navLink = {
  textDecoration: 'none',
  color: '#333',
  fontSize: '16px',
}

const stepCard = {
  display: 'flex',
  alignItems: 'center',
  gap: '20px',
  background: 'white',
  padding: '25px',
  borderRadius: '10px',
  border: '1px solid #e5e7eb',
}

const stepNumber = {
  background: '#0070f3',
  color: 'white',
  width: '50px',
  height: '50px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '24px',
  fontWeight: 'bold',
  flexShrink: 0,
}

const footerLink = {
  textDecoration: 'none',
  color: '#666',
  fontSize: '14px',
}
