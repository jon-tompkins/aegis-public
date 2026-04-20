'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import ShieldIcon from '../components/ShieldIcon'

const navItems = [
  { href: '/docs/roadmap', label: 'Roadmap' },
  { href: '/docs/constitution', label: 'Constitution' },
  { href: '/docs/soul-hash', label: 'Soul Hash' },
  { href: '/docs/intent-mapping', label: 'Intent Mapping' },
  { href: '/docs/training-pipeline', label: 'Training Pipeline' },
  { href: '/docs/agent-comms', label: 'Agent Comms' },
  { href: '/docs/guardian', label: 'Guardian' },
  { href: '/docs/hack-taxonomy', label: 'Hack Taxonomy' },
  { href: '/docs/byo-model', label: 'BYO Model' },
  { href: '/docs/memory-strategy', label: 'Memory Strategy' },
  { href: '/docs/off-chain-store', label: 'Off-chain Store' },
  { href: '/docs/staking-systems', label: 'Staking Systems' },
  { href: '/docs/economics', label: 'Economics' },
]

function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1a2a4a] bg-[#050810]/90 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <ShieldIcon className="w-6 h-6 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-bold text-white">Aegis</span>
          <span className="text-[#4a5a7a] text-sm ml-2">/ docs</span>
        </Link>
        <div className="flex items-center gap-6 text-sm">
          <Link href="/" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            ← Home
          </Link>
          <a
            href="https://github.com/jon-tompkins/aegis-public"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors"
          >
            GitHub
          </a>
        </div>
      </div>
    </nav>
  )
}

function Sidebar({ current }: { current: string }) {
  return (
    <aside className="docs-sidebar w-64 shrink-0 hidden lg:block pr-8">
      <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a] uppercase tracking-wider mb-4">
        Specifications
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => {
          const active = current === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block text-sm py-1.5 px-3 rounded-md transition-colors ${
                active
                  ? 'text-[#00d4ff] bg-[#00d4ff]/08 font-medium'
                  : 'text-[#4a5a7a] hover:text-[#c8d4e8]'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-[#050810]">
      <Nav />
      <div className="pt-16">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-12 flex gap-12">
          <Sidebar current={pathname} />
          <article className="flex-1 min-w-0 max-w-3xl">
            {children}
          </article>
        </div>
      </div>
    </div>
  )
}
