export default function PricingPage() {
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ textAlign: 'center', marginBottom: '50px' }}>
        <h1 style={{ fontSize: '42px', marginBottom: '10px' }}>Pricing</h1>
        <p style={{ fontSize: '18px', color: '#666' }}>Choose the right product for your testing needs</p>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: '30px',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        {/* Product 1 */}
        <div style={cardStyle}>
          <h2 style={{ color: '#0070f3' }}>Form Page Testing</h2>
          <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0' }}>
            $1,000<span style={{ fontSize: '18px', fontWeight: 'normal' }}>/month</span>
          </div>
          <p style={{ color: '#666', marginBottom: '20px' }}>Discover and analyze all forms in your web application</p>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li>AI-powered form discovery</li>
            <li>Automatic field detection</li>
            <li>Validation rule analysis</li>
            <li>$500 Claude API budget included</li>
            <li>Unlimited users</li>
          </ul>
          <button style={buttonStyle}>Get Started</button>
        </div>

        {/* Product 2 */}
        <div style={cardStyle}>
          <h2 style={{ color: '#10b981' }}>Shopping Site Testing</h2>
          <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0' }}>
            $1,500<span style={{ fontSize: '18px', fontWeight: 'normal' }}>/month</span>
          </div>
          <p style={{ color: '#666', marginBottom: '20px' }}>Complete e-commerce flow testing and analysis</p>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li>Cart & checkout testing</li>
            <li>Product search validation</li>
            <li>Payment form analysis</li>
            <li>$750 Claude API budget included</li>
            <li>Advanced reporting</li>
          </ul>
          <button style={buttonStyle}>Get Started</button>
        </div>

        {/* Product 3 */}
        <div style={cardStyle}>
          <h2 style={{ color: '#f59e0b' }}>Marketing Website Testing</h2>
          <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0' }}>
            $800<span style={{ fontSize: '18px', fontWeight: 'normal' }}>/month</span>
          </div>
          <p style={{ color: '#666', marginBottom: '20px' }}>Optimize your marketing pages and landing pages</p>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li>Landing page analysis</li>
            <li>Lead form testing</li>
            <li>SEO element validation</li>
            <li>$400 Claude API budget included</li>
            <li>Conversion optimization</li>
          </ul>
          <button style={buttonStyle}>Get Started</button>
        </div>

        {/* Product 4 */}
        <div style={cardStyle}>
          <h2 style={{ color: '#8b5cf6' }}>AI Website Advancement</h2>
          <div style={{ fontSize: '36px', fontWeight: 'bold', margin: '20px 0' }}>
            $2,000<span style={{ fontSize: '18px', fontWeight: 'normal' }}>/month</span>
          </div>
          <p style={{ color: '#666', marginBottom: '20px' }}>AI-powered recommendations to improve your website</p>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li>AI website analysis</li>
            <li>Improvement suggestions</li>
            <li>UX optimization insights</li>
            <li>$1,000 Claude API budget included</li>
            <li>Priority support</li>
          </ul>
          <button style={buttonStyle}>Get Started</button>
        </div>
      </div>

      <div style={{ 
        textAlign: 'center', 
        marginTop: '60px', 
        padding: '30px',
        background: '#f9fafb',
        borderRadius: '10px'
      }}>
        <h3 style={{ fontSize: '24px', marginBottom: '15px' }}>All Plans Include:</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '20px' }}>
          <div>✅ Desktop Agent</div>
          <div>✅ Unlimited Projects</div>
          <div>✅ Unlimited Tests</div>
          <div>✅ Team Collaboration</div>
          <div>✅ API Access</div>
          <div>✅ Email Support</div>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '40px' }}>
        <p style={{ fontSize: '16px', color: '#666' }}>
          Want to try before you buy? <a href="/signup" style={{ color: '#0070f3' }}>Start a free trial</a>
        </p>
        <p style={{ fontSize: '14px', color: '#999', marginTop: '10px' }}>
          Free trial includes 7 days with your own Claude API key
        </p>
      </div>

      <div style={{ marginTop: '40px', textAlign: 'center' }}>
        <a href="/" style={{ color: '#0070f3', textDecoration: 'none' }}>← Back to Home</a>
      </div>
    </div>
  )
}

const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '10px',
  padding: '30px',
  textAlign: 'center' as const,
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  transition: 'transform 0.2s',
}

const buttonStyle = {
  background: '#0070f3',
  color: 'white',
  padding: '12px 24px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '16px',
  cursor: 'pointer',
  marginTop: '20px',
  width: '100%',
}
