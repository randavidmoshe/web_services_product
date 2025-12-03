import './globals.css'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Quathera - AI-Powered Web Testing Automation',
  description: 'Automatically discover and test form pages in your web applications using AI-powered crawling. Start your free trial today.',
  keywords: ['web testing', 'AI testing', 'form testing', 'automated testing', 'QA automation'],
  authors: [{ name: 'Quathera' }],
  openGraph: {
    title: 'Quathera - AI-Powered Web Testing Automation',
    description: 'Automatically discover and test form pages in your web applications using AI-powered crawling.',
    type: 'website',
    locale: 'en_US',
    siteName: 'Quathera',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Quathera - AI-Powered Web Testing Automation',
    description: 'Automatically discover and test form pages in your web applications using AI-powered crawling.',
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <meta name="theme-color" content="#00BBF9" />
      </head>
      <body>{children}</body>
    </html>
  )
}
