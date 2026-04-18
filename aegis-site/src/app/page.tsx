'use client'

import Link from 'next/link'

// Animated shield grid SVG component
function ShieldGrid() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <svg
        className="absolute inset-0 w-full h-full shield-grid opacity-30"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="rgba(0, 212, 255, 0.15)"
              strokeWidth="0.5"
            />
          </pattern>
          <radialGradient id="shieldGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(0, 212, 255, 0.15)" />
            <stop offset="100%" stopColor="rgba(0, 212, 255, 0)" />
          </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <ellipse cx="50%" cy="45%" rx="25%" ry="30%" fill="url(#shieldGlow)" />
      </svg>
    </div>
  )
}

// Shield icon
function ShieldIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6l-8-4z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="rgba(0, 212, 255, 0.05)"
      />
      <path
        d="M9 12l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Navigation
function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1a2a4a] bg-[#050810]/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldIcon className="w-7 h-7 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-bold text-lg text-white">Aegis</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/docs/chain-design" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            Docs
          </Link>
          <Link href="/docs/hack-taxonomy" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            Research
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

// Hero section
function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      <ShieldGrid />
      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <div className="animate-fade-up">
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-2 rounded-full border border-[#1a2a4a] bg-[#0d1525]">
            <span className="w-2 h-2 rounded-full bg-[#00cc88] animate-pulse" />
            <span className="text-sm font-['JetBrains_Mono'] text-[#4a5a7a]">Ethereum L2 — AI Agent Validators</span>
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-['Space_Grotesk'] font-bold text-white mb-6 animate-fade-up animate-fade-up-delay-1 glow-cyan-text">
          The chain that<br />
          <span className="text-[#00d4ff]">fights back</span>
        </h1>

        <p className="text-lg md:text-xl text-[#4a5a7a] max-w-2xl mx-auto mb-10 animate-fade-up animate-fade-up-delay-2">
          Aegis is an Ethereum L2 where AI agents validate every transaction.
          Anomalies get paused. Exploits get stopped. Before they drain the pool.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up animate-fade-up-delay-3">
          <Link href="/docs/chain-design" className="btn-primary">
            Read the Spec
          </Link>
          <a
            href="https://github.com/jon-tompkins/aegis-public"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            View on GitHub
          </a>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-fade-up animate-fade-up-delay-5">
        <div className="w-6 h-10 rounded-full border border-[#1a2a4a] flex items-start justify-center p-2">
          <div className="w-1 h-2 rounded-full bg-[#00d4ff] animate-bounce" />
        </div>
      </div>
    </section>
  )
}

// What is Aegis
function WhatIsAegis() {
  return (
    <section className="py-24 px-6 bg-[#0a0f1a]">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-8">
          What is Aegis?
        </h2>
        <div className="space-y-6 text-[#4a5a7a] text-lg">
          <p>
            Aegis is an Ethereum Layer 2 built on the OP Stack. Every transaction — before it executes — passes through a screening layer run by AI agents. These agents have been trained on years of on-chain exploit patterns. They know what a drain looks like before it happens.
          </p>
          <p>
            If a transaction looks anomalous, the Guardian pauses it. The validator set votes. If it confirms malicious, the transaction is rejected and the contract is frozen. No drain. No exploit. Just a chain that fights back.
          </p>
        </div>

        {/* Simple flow diagram */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-3 text-sm font-['JetBrains_Mono']">
          {['Tx Submitted', 'Guardian Screens', 'Clear or Escalate', 'Validator Vote', 'On-Chain Result'].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className="px-4 py-2 rounded-lg bg-[#0d1525] border border-[#1a2a4a] text-[#c8d4e8]">
                {step}
              </div>
              {i < 4 && <span className="text-[#00d4ff]">→</span>}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Why it matters — 3 cards
function WhyItMatters() {
  const cards = [
    {
      icon: '⚡',
      tag: 'Agentic',
      title: 'AI Screening at Scale',
      desc: 'Every tx screened in milliseconds. Tier 1 heuristics run on 100% of transactions. Tier 2 statistical models catch anomalies. Tier 3 LLM explains the hard cases.',
    },
    {
      icon: '🔐',
      tag: 'Verifiable',
      title: 'Soul Hash Verification',
      desc: 'Canonical behavioral profiles committed on-chain as a Merkle root. Validators who run the same profiles produce the same results. Proof without disclosure.',
    },
    {
      icon: '💰',
      tag: 'Aligned',
      title: 'Economic Accountability',
      desc: 'Validators stake AEGIS and ETH. Slash for negligence. Earn for honest screening. Gas paid in ETH, not AEGIS. No speculative premium baked into every tx.',
    },
  ]

  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-12 text-center">
          Why it matters
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {cards.map((card) => (
            <div
              key={card.title}
              className="p-6 rounded-xl bg-[#0d1525] border border-[#1a2a4a] card-hover"
            >
              <span className="text-2xl mb-4 block">{card.icon}</span>
              <span className="tag tag-cyan mb-4 inline-block">{card.tag}</span>
              <h3 className="text-lg font-['Space_Grotesk'] font-semibold text-white mb-3">
                {card.title}
              </h3>
              <p className="text-[#4a5a7a] text-sm leading-relaxed">
                {card.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Stack section
function Stack() {
  return (
    <section className="py-24 px-6 bg-[#0a0f1a]">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-4">
          Built on what works
        </h2>
        <p className="text-[#4a5a7a] mb-12">
          No novel cryptography. No unproven consensus. Just battle-tested components wired together correctly.
        </p>
        <div className="grid grid-cols-3 gap-6 text-center">
          {[
            { name: 'OP Stack', desc: 'Ethereum L2' },
            { name: 'AI Agents', desc: 'Screening layer' },
            { name: 'Ethereum', desc: 'Security' },
          ].map((item) => (
            <div key={item.name} className="p-6 rounded-xl bg-[#0d1525] border border-[#1a2a4a]">
              <div className="text-[#00d4ff] font-['Space_Grotesk'] font-bold text-lg mb-1">
                {item.name}
              </div>
              <div className="text-[#4a5a7a] text-sm">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// CTA / Get involved
function CTA() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-2xl mx-auto text-center">
        <ShieldIcon className="w-12 h-12 text-[#00d4ff] mx-auto mb-6 glow-cyan" />
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-4">
          Start reading
        </h2>
        <p className="text-[#4a5a7a] mb-8">
          The full design is in the specs. Chain architecture, screening models, economics — all linked below.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/docs/chain-design" className="btn-primary">
            Chain Design
          </Link>
          <Link href="/docs/soul-hash" className="btn-secondary">
            Soul Hash Spec
          </Link>
        </div>
      </div>
    </section>
  )
}

// Footer
function Footer() {
  return (
    <footer className="py-8 px-6 border-t border-[#1a2a4a]">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <ShieldIcon className="w-5 h-5 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-semibold text-white">Aegis Chain</span>
        </div>
        <div className="text-[#4a5a7a] text-sm font-['JetBrains_Mono']">
          aegischain.xyz
        </div>
        <div className="flex items-center gap-4 text-sm text-[#4a5a7a]">
          <a href="https://github.com/jon-tompkins/aegis-public" target="_blank" rel="noopener noreferrer" className="hover:text-[#c8d4e8] transition-colors">
            GitHub
          </a>
          <span>·</span>
          <Link href="/docs/chain-design" className="hover:text-[#c8d4e8] transition-colors">
            Docs
          </Link>
        </div>
      </div>
    </footer>
  )
}

export default function Home() {
  return (
    <main className="min-h-screen dot-grid">
      <Nav />
      <Hero />
      <WhatIsAegis />
      <WhyItMatters />
      <Stack />
      <CTA />
      <Footer />
    </main>
  )
}
