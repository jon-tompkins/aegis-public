import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Aegis Chain — The Chain That Fights Back',
  description: 'Ethereum L2 with AI agent validators that screen every transaction for anomalous behavior and can pause or reject exploits at the chain level.',
  icons: {
    icon: [
      {
        url: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡</text></svg>",
        type: 'image/svg+xml',
      },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#050810] text-[#c8d4e8] antialiased">
        {children}
      </body>
    </html>
  )
}
