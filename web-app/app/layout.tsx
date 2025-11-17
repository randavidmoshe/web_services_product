export const metadata = {
  title: 'Form Discoverer',
  description: 'AI-Powered Form Testing Platform',
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
