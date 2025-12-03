import './globals.css'

export const metadata = {
  title: 'Quathera - AI-Powered Form Testing',
  description: 'Automatically discover and test form pages in your web applications using AI-powered crawling',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
