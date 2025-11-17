export default function AboutPage() {
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ textAlign: 'center', marginBottom: '50px' }}>
        <h1 style={{ fontSize: '42px', marginBottom: '10px' }}>About Form Discoverer</h1>
        <p style={{ fontSize: '18px', color: '#666' }}>AI-powered automated testing for modern web applications</p>
      </div>

      <div style={{ maxWidth: '800px', margin: '0 auto', lineHeight: '1.8' }}>
        <section style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Our Mission</h2>
          <p style={{ fontSize: '16px', color: '#444' }}>
            Form Discoverer was built to solve a critical problem: discovering and testing all the forms 
            in complex web applications is time-consuming and error-prone. We leverage cutting-edge AI 
            technology to automate this process, saving development teams countless hours while improving 
            test coverage.
          </p>
        </section>

        <section style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>How It Works</h2>
          <div style={{ background: '#f9fafb', padding: '25px', borderRadius: '10px' }}>
            <ol style={{ paddingLeft: '20px' }}>
              <li style={{ marginBottom: '15px' }}>
                <strong>Download the Agent:</strong> Install our lightweight desktop application on your computer
              </li>
              <li style={{ marginBottom: '15px' }}>
                <strong>Configure Your Target:</strong> Point the agent to your web application URL
              </li>
              <li style={{ marginBottom: '15px' }}>
                <strong>AI Discovery:</strong> Claude AI intelligently crawls your site and discovers all forms
              </li>
              <li style={{ marginBottom: '15px' }}>
                <strong>Detailed Analysis:</strong> Get comprehensive reports on fields, validations, and structure
              </li>
              <li>
                <strong>Continuous Testing:</strong> Keep your tests up-to-date as your application evolves
              </li>
            </ol>
          </div>
        </section>

        <section style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Why Form Discoverer?</h2>
          <div style={{ display: 'grid', gap: '20px' }}>
            <div style={benefitCard}>
              <h3 style={{ color: '#0070f3', marginBottom: '10px' }}>⚡ Save Time</h3>
              <p>Automate what used to take days of manual work into minutes of automated discovery</p>
            </div>
            <div style={benefitCard}>
              <h3 style={{ color: '#10b981', marginBottom: '10px' }}>🎯 Improve Coverage</h3>
              <p>Never miss a form again. AI ensures comprehensive coverage of your entire application</p>
            </div>
            <div style={benefitCard}>
              <h3 style={{ color: '#f59e0b', marginBottom: '10px' }}>🔒 Stay Secure</h3>
              <p>Agents run on your infrastructure. Your data never leaves your control</p>
            </div>
            <div style={benefitCard}>
              <h3 style={{ color: '#8b5cf6', marginBottom: '10px' }}>📊 Get Insights</h3>
              <p>AI-powered analysis provides actionable insights to improve your forms</p>
            </div>
          </div>
        </section>

        <section style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Technology</h2>
          <p style={{ fontSize: '16px', color: '#444', marginBottom: '15px' }}>
            Form Discoverer is built on modern, scalable technology:
          </p>
          <ul style={{ lineHeight: '2', color: '#666' }}>
            <li><strong>Claude AI:</strong> Anthropic's cutting-edge language model for intelligent analysis</li>
            <li><strong>Selenium WebDriver:</strong> Industry-standard browser automation</li>
            <li><strong>Cloud Architecture:</strong> Scalable infrastructure supporting thousands of users</li>
            <li><strong>Modern Web Stack:</strong> Next.js, FastAPI, PostgreSQL for reliability and performance</li>
          </ul>
        </section>

        <section style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Products</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <div style={productBadge}>
              <strong>Form Page Testing</strong>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>Discover & analyze forms</p>
            </div>
            <div style={productBadge}>
              <strong>Shopping Site Testing</strong>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>E-commerce flows</p>
            </div>
            <div style={productBadge}>
              <strong>Marketing Website Testing</strong>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>Landing pages</p>
            </div>
            <div style={productBadge}>
              <strong>AI Website Advancement</strong>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>Optimization insights</p>
            </div>
          </div>
        </section>

        <section style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '40px',
          borderRadius: '10px',
          textAlign: 'center'
        }}>
          <h2 style={{ fontSize: '28px', marginBottom: '15px' }}>Ready to Transform Your Testing?</h2>
          <p style={{ fontSize: '16px', marginBottom: '25px' }}>
            Join teams who are already saving time with AI-powered form discovery
          </p>
          <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <a href="/signup" style={{
              background: 'white',
              color: '#667eea',
              padding: '12px 24px',
              textDecoration: 'none',
              borderRadius: '6px',
              fontWeight: 'bold'
            }}>
              Start Free Trial
            </a>
            <a href="/pricing" style={{
              background: 'transparent',
              color: 'white',
              padding: '12px 24px',
              textDecoration: 'none',
              borderRadius: '6px',
              border: '2px solid white',
              fontWeight: 'bold'
            }}>
              View Pricing
            </a>
          </div>
        </section>
      </div>

      <div style={{ marginTop: '40px', textAlign: 'center' }}>
        <a href="/" style={{ color: '#0070f3', textDecoration: 'none' }}>← Back to Home</a>
      </div>
    </div>
  )
}

const benefitCard = {
  background: '#f9fafb',
  padding: '20px',
  borderRadius: '8px',
  border: '1px solid #e5e7eb',
}

const productBadge = {
  background: 'white',
  padding: '15px',
  borderRadius: '8px',
  border: '1px solid #e5e7eb',
  textAlign: 'center' as const,
}
