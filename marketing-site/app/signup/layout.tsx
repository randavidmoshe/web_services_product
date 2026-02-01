export const metadata = {
  title: 'Sign up | Quattera.ai',
  description: 'Secure account creation for Quattera.ai (email verification + 2FA).',
}

export default function SignupLayout({ children }: { children: React.ReactNode }) {
  // IMPORTANT: nested route layouts must NOT include <html> / <body>.
  return <>{children}</>
}
