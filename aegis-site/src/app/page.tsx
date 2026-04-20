'use client'

import Link from 'next/link'
import ShieldIcon from './components/ShieldIcon'

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

// Navigation
function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1a2a4a] bg-[#050810]/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldIcon className="w-7 h-7 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-bold text-lg text-white">Aegis</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/docs/soul-hash" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            Docs
          </Link>
          <a
            href="https://github.com/jon-tompkins/aegis-public/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors"
          >
            Issues
          </a>
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
      <div className="relative z-10 max-w-4xl mx-auto px-6 sm:px-8 lg:px-12 text-center">
        <div className="animate-fade-up">
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-2 rounded-full border border-[#1a2a4a] bg-[#0d1525]">
            <span className="w-2 h-2 rounded-full bg-[#00cc88] animate-pulse" />
            <span className="text-sm font-['JetBrains_Mono'] text-[#4a5a7a]">Pre-alpha · specs only</span>
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-['Space_Grotesk'] font-bold text-white mb-6 animate-fade-up animate-fade-up-delay-1 glow-cyan-text">
          The chain that<br />
          <span className="text-[#00d4ff]">fights back</span>
        </h1>

        <p className="text-lg md:text-xl text-[#4a5a7a] max-w-2xl mx-auto mb-10 animate-fade-up animate-fade-up-delay-2">
          An Ethereum L2 where AI validators screen every transaction. Anomalies get paused. Exploits get stopped — before the pool drains.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up animate-fade-up-delay-3">
          <Link href="/docs/soul-hash" className="btn-primary">
            Read the specs
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
    <section className="py-24 px-6 sm:px-8 lg:px-12 bg-[#0a0f1a]">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-8">
          What it is
        </h2>
        <div className="space-y-6 text-[#4a5a7a] text-lg">
          <p>
            An Ethereum L2 where every transaction passes through a screening layer before it executes. AI validators, trained on years of exploit patterns, flag anomalies in milliseconds. Suspect transactions pause. The validator set votes. Confirmed exploits are rejected on-chain.
          </p>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-3 text-sm font-['JetBrains_Mono']">
          {['Tx submitted', 'Screened', 'Clear or escalate', 'Validator vote', 'On-chain result'].map((step, i) => (
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

// Core principles — 3 cards
function Principles() {
  const cards = [
    {
      tag: 'Agentic',
      title: 'Screening at chain speed',
      desc: 'Three tiers: deterministic rules on 100% of txs, statistical models on anomalies, LLM review on the hard cases.',
    },
    {
      tag: 'Verifiable',
      title: 'Soul-hash commitments',
      desc: 'Canonical behavioral profiles committed on-chain as a Merkle root. Different validators, same profile, same result.',
    },
    {
      tag: 'Aligned',
      title: 'Economic accountability',
      desc: 'Validators stake AEGIS and ETH; slash for negligence, earn for honest screening. Users pay gas in ETH — no token friction.',
    },
  ]

  return (
    <section className="py-24 px-6 sm:px-8 lg:px-12">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-12 text-center">
          Core principles
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {cards.map((card) => (
            <div
              key={card.title}
              className="p-6 rounded-xl bg-[#0d1525] border border-[#1a2a4a] card-hover"
            >
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

// Contribute — for builders and agents
function Contribute() {
  const specs = [
    { slug: 'soul-hash', label: 'Soul Hash' },
    { slug: 'intent-mapping', label: 'Intent Mapping' },
    { slug: 'economics', label: 'Economics' },
    { slug: 'agent-comms', label: 'Agent Comms' },
    { slug: 'staking-systems', label: 'Staking Systems' },
    { slug: 'memory-strategy', label: 'Memory Strategy' },
    { slug: 'hack-taxonomy', label: 'Hack Taxonomy' },
    { slug: 'byo-model', label: 'BYO Model' },
    { slug: 'guardian', label: 'Guardian' },
  ]

  return (
    <section className="py-24 px-6 sm:px-8 lg:px-12 bg-[#0a0f1a]">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-['Space_Grotesk'] font-bold text-white mb-4">
          Help build it
        </h2>
        <p className="text-[#4a5a7a] mb-10 max-w-2xl">
          Aegis is pre-alpha. The design lives in nine specs; most are drafts looking for a second set of eyes. Open issues carry the active work. Builders and autonomous agents both welcome.
        </p>

        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          <a
            href="https://github.com/jon-tompkins/aegis-public/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="p-5 rounded-xl bg-[#0d1525] border border-[#1a2a4a] card-hover block"
          >
            <div className="text-[#00d4ff] font-['Space_Grotesk'] font-semibold mb-1">Open issues</div>
            <div className="text-[#4a5a7a] text-sm">Active work, design questions, and unresolved calls.</div>
          </a>
          <a
            href="https://github.com/jon-tompkins/aegis-public"
            target="_blank"
            rel="noopener noreferrer"
            className="p-5 rounded-xl bg-[#0d1525] border border-[#1a2a4a] card-hover block"
          >
            <div className="text-[#00d4ff] font-['Space_Grotesk'] font-semibold mb-1">Repository</div>
            <div className="text-[#4a5a7a] text-sm">Specs, indexer skeleton, screening rule prototypes.</div>
          </a>
        </div>

        <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a] uppercase tracking-wider mb-3">
          Specs
        </div>
        <div className="flex flex-wrap gap-2">
          {specs.map((s) => (
            <Link
              key={s.slug}
              href={`/docs/${s.slug}`}
              className="px-3 py-1.5 rounded-md border border-[#1a2a4a] bg-[#0d1525] text-sm text-[#c8d4e8] hover:border-[#00d4ff] hover:text-[#00d4ff] transition-colors"
            >
              {s.label}
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}

// Footer
function Footer() {
  return (
    <footer className="py-8 px-6 sm:px-8 lg:px-12 border-t border-[#1a2a4a]">
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
          <Link href="/docs/soul-hash" className="hover:text-[#c8d4e8] transition-colors">
            Docs
          </Link>
          <span>·</span>
          <Link href="/brand" className="hover:text-[#c8d4e8] transition-colors">
            Brand
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
      <Principles />
      <Contribute />
      <Footer />
    </main>
  )
}
