export default function FeaturesPage() {
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ textAlign: 'center', marginBottom: '50px' }}>
        <h1 style={{ fontSize: '42px', marginBottom: '10px' }}>Features</h1>
        <p style={{ fontSize: '18px', color: '#666' }}>Powerful AI-driven testing for modern web applications</p>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* AI-Powered Discovery */}
        <div style={featureSection}>
          <div style={featureIcon}>🤖</div>
          <h2>AI-Powered Form Discovery</h2>
          <p>Claude AI automatically finds and analyzes all forms in your web application. No manual configuration needed.</p>
          <ul style={featureList}>
            <li>Automatic page crawling</li>
            <li>Intelligent form detection</li>
            <li>Field type recognition</li>
            <li>Validation rule extraction</li>
          </ul>
        </div>

        {/* Desktop Agent */}
        <div style={featureSection}>
          <div style={featureIcon}>💻</div>
          <h2>Desktop Agent</h2>
          <p>Runs securely on your team's computers. Your data never leaves your infrastructure.</p>
          <ul style={featureList}>
            <li>Windows, Mac, and Linux support</li>
            <li>Chrome, Firefox, Edge compatible</li>
            <li>Secure token-based authentication</li>
            <li>Real-time status updates</li>
          </ul>
        </div>

        {/* Cost Optimization */}
        <div style={featureSection}>
          <div style={featureIcon}>💰</div>
          <h2>Cost Optimization</h2>
          <p>Smart caching reduces API costs by up to 85% through intelligent change detection.</p>
          <ul style={featureList}>
            <li>DOM hash-based change detection</li>
            <li>Automatic budget management</li>
            <li>Usage tracking and alerts</li>
            <li>Monthly budget limits</li>
          </ul>
        </div>

        {/* Team Collaboration */}
        <div style={featureSection}>
          <div style={featureIcon}>👥</div>
          <h2>Team Collaboration</h2>
          <p>Shared workspace where all team members see the same projects and results.</p>
          <ul style={featureList}>
            <li>Unlimited team members</li>
            <li>Shared projects and networks</li>
            <li>Role-based access (Admin/User)</li>
            <li>Collaborative testing</li>
          </ul>
        </div>

        {/* Multi-Product Platform */}
        <div style={featureSection}>
          <div style={featureIcon}>🎯</div>
          <h2>Multi-Product Platform</h2>
          <p>Subscribe to one or multiple testing products based on your needs.</p>
          <ul style={featureList}>
            <li>Form Page Testing</li>
            <li>Shopping Site Testing</li>
            <li>Marketing Website Testing</li>
            <li>AI Website Advancement</li>
          </ul>
        </div>

        {/* Security & Privacy */}
        <div style={featureSection}>
          <div style={featureIcon}>🔒</div>
          <h2>Security & Privacy</h2>
          <p>Enterprise-grade security with complete data privacy.</p>
          <ul style={featureList}>
            <li>Agent runs on your infrastructure</li>
            <li>Encrypted credentials storage</li>
            <li>User-specific agent tokens</li>
            <li>Company data isolation</li>
          </ul>
        </div>

        {/* Scalable Architecture */}
        <div style={featureSection}>
          <div style={featureIcon}>📈</div>
          <h2>Scalable Architecture</h2>
          <p>Built to handle teams of any size, from startups to enterprises.</p>
          <ul style={featureList}>
            <li>Horizontal scaling ready</li>
            <li>Load balancer support</li>
            <li>Designed for 100,000+ users</li>
            <li>High availability setup</li>
          </ul>
        </div>

        {/* Easy Integration */}
        <div style={featureSection}>
          <div style={featureIcon}>⚡</div>
          <h2>Easy Integration</h2>
          <p>Get started in minutes with simple setup and intuitive interface.</p>
          <ul style={featureList}>
            <li>One-click agent download</li>
            <li>Automatic configuration</li>
            <li>No code required</li>
            <li>Comprehensive documentation</li>
          </ul>
        </div>
      </div>

      <div style={{ 
        textAlign: 'center', 
        marginTop: '60px',
        padding: '40px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        borderRadius: '10px'
      }}>
        <h2 style={{ fontSize: '32px', marginBottom: '20px' }}>Ready to Get Started?</h2>
        <p style={{ fontSize: '18px', marginBottom: '30px' }}>Start discovering forms in your web application today</p>
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

      <div style={{ marginTop: '40px', textAlign: 'center' }}>
        <a href="/" style={{ color: '#0070f3', textDecoration: 'none' }}>← Back to Home</a>
      </div>
    </div>
  )
}

const featureSection = {
  background: '#f9fafb',
  padding: '30px',
  borderRadius: '10px',
  marginBottom: '30px',
}

const featureIcon = {
  fontSize: '48px',
  marginBottom: '15px',
}

const featureList = {
  lineHeight: '2',
  color: '#666',
  marginTop: '15px',
}
