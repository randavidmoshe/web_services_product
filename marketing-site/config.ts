// Configuration for marketing site
// In development: uses localhost
// In production: uses real domain

const config = {
  // API URL - where the backend runs
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001',
  
  // App URL - where the dashboard runs
  appUrl: process.env.NEXT_PUBLIC_APP_URL || 'https://localhost',
}

export default config
