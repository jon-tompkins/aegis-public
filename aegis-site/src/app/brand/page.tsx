import Link from 'next/link'
import ShieldIcon from '../components/ShieldIcon'

export const metadata = {
  title: 'Aegis — Brand',
  description: 'Aegis brand guidelines: logo, colors, typography, tone, and usage.',
}

// ----- palette data (mirrors globals.css tokens) -----
const palette = [
  { token: '--accent', hex: '#00d4ff', role: 'Primary accent', onDark: true },
  { token: '--accent-2', hex: '#4a9eff', role: 'Secondary accent', onDark: true },
  { token: '--bg-deep', hex: '#050810', role: 'Deep background', onDark: true },
  { token: '--bg-dark', hex: '#0a0f1a', role: 'Section background', onDark: true },
  { token: '--bg-card', hex: '#0d1525', role: 'Card surface', onDark: true },
  { token: '--border', hex: '#1a2a4a', role: 'Borders / dividers', onDark: true },
  { token: '--text', hex: '#c8d4e8', role: 'Body text', onDark: true },
  { token: '--text-dim', hex: '#4a5a7a', role: 'Dimmed text', onDark: true },
  { token: '--success', hex: '#00cc88', role: 'Success / live', onDark: true },
  { token: '--warn', hex: '#ffd700', role: 'Warning', onDark: true },
  { token: '--danger', hex: '#ff4455', role: 'Error / block', onDark: true },
]

const typography = [
  {
    name: 'Space Grotesk',
    role: 'Display — logo wordmark, headings, buttons',
    weights: '400 / 500 / 600 / 700',
    source: 'Google Fonts',
    href: 'https://fonts.google.com/specimen/Space+Grotesk',
    sampleClass: "font-['Space_Grotesk'] font-bold text-3xl",
    sample: 'The chain that fights back',
  },
  {
    name: 'IBM Plex Sans',
    role: 'Body — paragraphs, UI copy',
    weights: '400 / 500 / 600',
    source: 'Google Fonts',
    href: 'https://fonts.google.com/specimen/IBM+Plex+Sans',
    sampleClass: 'text-base',
    sample: 'Aegis screens every transaction before it reaches the chain. Suspect transactions pause. Confirmed exploits are rejected on-chain.',
  },
  {
    name: 'JetBrains Mono',
    role: 'Code, tags, technical metadata',
    weights: '400 / 500 / 600',
    source: 'Google Fonts',
    href: 'https://fonts.google.com/specimen/JetBrains+Mono',
    sampleClass: "font-['JetBrains_Mono'] text-sm",
    sample: '0x5b7c…  ·  tx flagged: approve_to_eoa  ·  t1-v0.3',
  },
]

const voice = [
  {
    title: 'Plain, not marketing',
    body: 'Aegis does specific things. Describe those things. Don\'t pitch feelings. "Every transaction screened before it reaches the chain" is better than "revolutionary on-chain safety."',
  },
  {
    title: 'Concrete over abstract',
    body: 'Name the primitive, the spec, the rule. Link to the doc that defines it. Vague claims erode trust faster than honest limits.',
  },
  {
    title: 'Acknowledge limits',
    body: 'Aegis reduces exploit risk. It does not eliminate it. Say so every time the context warrants — it\'s the price of being trustworthy.',
  },
  {
    title: 'Builders first',
    body: 'The primary audience is technical: other protocol builders, validators, and autonomous agents. Write to them. Laypeople can follow if we\'re clear; they\'re pushed away by jargon, not by rigor.',
  },
]

const usage = {
  do: [
    'Use the mark on the deep navy (#050810) or any darker background.',
    'Maintain clear space around the mark equal to the height of the shield itself.',
    'Pair the mark with the "Aegis" wordmark in Space Grotesk.',
    'Use the primary cyan (#00d4ff) as the accent anchor in any layout featuring the brand.',
  ],
  dont: [
    'Don\'t recolor the mark outside the approved palette.',
    'Don\'t stretch, skew, or rotate the mark.',
    'Don\'t add drop shadows, gradients, or outer glows that weren\'t already in the official file.',
    'Don\'t compose the mark with third-party logos into a combined glyph.',
    'Don\'t place the mark on a low-contrast background where the cyan edges blur into it.',
    'Don\'t use the wordmark in a font other than Space Grotesk.',
  ],
}

// ----- sections -----

function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1a2a4a] bg-[#050810]/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <ShieldIcon className="w-7 h-7 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-bold text-lg text-white">Aegis</span>
          <span className="text-[#4a5a7a] text-sm ml-2">/ brand</span>
        </Link>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            ← Home
          </Link>
          <Link href="/docs/soul-hash" className="text-[#4a5a7a] hover:text-[#c8d4e8] transition-colors">
            Docs
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

function Hero() {
  return (
    <section className="pt-32 pb-16 px-6 sm:px-8 lg:px-12">
      <div className="max-w-4xl mx-auto">
        <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a] uppercase tracking-wider mb-4">
          v0.1 · pre-alpha
        </div>
        <h1 className="text-4xl md:text-5xl font-['Space_Grotesk'] font-bold text-white mb-4">
          Aegis brand
        </h1>
        <p className="text-lg text-[#c8d4e8] max-w-2xl">
          A reference for using the Aegis name, mark, palette, and voice consistently.
          The brand system is intentionally small — one mark, one accent, three fonts, four principles.
        </p>
      </div>
    </section>
  )
}

function Section({ id, eyebrow, title, children }: {
  id: string
  eyebrow: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="py-16 px-6 sm:px-8 lg:px-12 border-t border-[#1a2a4a]">
      <div className="max-w-4xl mx-auto">
        <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a] uppercase tracking-wider mb-2">
          {eyebrow}
        </div>
        <h2 className="text-2xl md:text-3xl font-['Space_Grotesk'] font-bold text-white mb-8">
          {title}
        </h2>
        {children}
      </div>
    </section>
  )
}

function NameSection() {
  return (
    <Section id="name" eyebrow="01" title="Name">
      <div className="space-y-4 text-[#c8d4e8]">
        <p>
          <strong className="text-white">Aegis</strong>{' '}
          <span className="font-['JetBrains_Mono'] text-sm text-[#4a5a7a]">/ˈiː.dʒɪs/ · EE-jis</span>
        </p>
        <p className="text-[#4a5a7a]">
          Always capitalised when the product is named. Lower-case elsewhere (<span className="font-['JetBrains_Mono'] text-sm">the aegis of</span>) keeps its English meaning and isn&apos;t a reference to the product.
        </p>
        <p className="text-[#4a5a7a]">
          Derived from Athena&apos;s shield in Greek myth — the name carries a defensive, guardian meaning. Use it. Do not over-explain the etymology in marketing copy.
        </p>
      </div>
    </Section>
  )
}

function LogoSection() {
  return (
    <Section id="logo" eyebrow="02" title="Logo">
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div className="p-10 rounded-xl bg-[#050810] border border-[#1a2a4a] flex flex-col items-center justify-center gap-6">
          <ShieldIcon className="w-20 h-20 text-[#00d4ff]" />
          <div className="font-['Space_Grotesk'] font-bold text-3xl text-white">Aegis</div>
        </div>
        <div className="p-10 rounded-xl bg-[#c8d4e8] border border-[#1a2a4a] flex flex-col items-center justify-center gap-6">
          <ShieldIcon className="w-20 h-20 text-[#050810]" />
          <div className="font-['Space_Grotesk'] font-bold text-3xl text-[#050810]">Aegis</div>
        </div>
      </div>
      <div className="text-sm text-[#4a5a7a] space-y-3">
        <p>
          The mark is a shield — the literal definition of the name. A mesh variant (validator nodes forming the shield silhouette) is the expanded form and is preferred for hero and download use; the solid glyph above is the working favicon.
        </p>
        <p>
          Official asset files (SVG + PNG, dark + light variants, mesh + solid) will live under{' '}
          <span className="font-['JetBrains_Mono'] text-[#c8d4e8]">/brand/files/</span>{' '}
          once vectorised. Until then, pull the mark directly from the site header or request the raster source from the maintainers.
        </p>
      </div>
    </Section>
  )
}

function ColorSection() {
  const swatch = (c: typeof palette[number]) => (
    <div
      key={c.hex}
      className="rounded-xl overflow-hidden border border-[#1a2a4a] bg-[#0d1525]"
    >
      <div
        className="h-24 w-full"
        style={{ background: c.hex }}
        aria-hidden
      />
      <div className="p-4">
        <div className="text-sm font-['Space_Grotesk'] font-semibold text-white">{c.role}</div>
        <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a] mt-1">{c.hex}</div>
        <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a]">{c.token}</div>
      </div>
    </div>
  )

  return (
    <Section id="color" eyebrow="03" title="Color">
      <p className="text-[#c8d4e8] mb-8 max-w-2xl">
        The palette is dark-first. Cyan is the single anchor accent. Use status colors (success / warn / danger) only to communicate state — never for decoration.
      </p>
      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4">
        {palette.map(swatch)}
      </div>
    </Section>
  )
}

function TypeSection() {
  return (
    <Section id="typography" eyebrow="04" title="Typography">
      <div className="space-y-8">
        {typography.map((t) => (
          <div
            key={t.name}
            className="p-6 rounded-xl bg-[#0d1525] border border-[#1a2a4a]"
          >
            <div className="flex items-baseline justify-between gap-4 mb-4 flex-wrap">
              <div>
                <div className="font-['Space_Grotesk'] font-semibold text-white text-lg">{t.name}</div>
                <div className="text-sm text-[#4a5a7a]">{t.role}</div>
              </div>
              <div className="text-xs font-['JetBrains_Mono'] text-[#4a5a7a]">
                {t.weights} ·{' '}
                <a href={t.href} target="_blank" rel="noopener noreferrer" className="hover:text-[#00d4ff] transition-colors">
                  {t.source} ↗
                </a>
              </div>
            </div>
            <div className={`text-white ${t.sampleClass}`}>{t.sample}</div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function VoiceSection() {
  return (
    <Section id="voice" eyebrow="05" title="Voice & tone">
      <div className="grid md:grid-cols-2 gap-4">
        {voice.map((v) => (
          <div
            key={v.title}
            className="p-6 rounded-xl bg-[#0d1525] border border-[#1a2a4a]"
          >
            <div className="font-['Space_Grotesk'] font-semibold text-[#00d4ff] mb-2">{v.title}</div>
            <p className="text-sm text-[#c8d4e8] leading-relaxed">{v.body}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}

function UsageSection() {
  return (
    <Section id="usage" eyebrow="06" title="Usage">
      <div className="grid md:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl bg-[#0d1525] border border-[#00cc88]/30">
          <div className="text-sm font-['JetBrains_Mono'] uppercase tracking-wider text-[#00cc88] mb-4">Do</div>
          <ul className="space-y-2 text-sm text-[#c8d4e8]">
            {usage.do.map((x) => (
              <li key={x} className="flex gap-2">
                <span className="text-[#00cc88] shrink-0">+</span>
                <span>{x}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="p-6 rounded-xl bg-[#0d1525] border border-[#ff4455]/30">
          <div className="text-sm font-['JetBrains_Mono'] uppercase tracking-wider text-[#ff4455] mb-4">Don&apos;t</div>
          <ul className="space-y-2 text-sm text-[#c8d4e8]">
            {usage.dont.map((x) => (
              <li key={x} className="flex gap-2">
                <span className="text-[#ff4455] shrink-0">−</span>
                <span>{x}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  )
}

function ContactSection() {
  return (
    <Section id="contact" eyebrow="07" title="Press & contact">
      <p className="text-[#c8d4e8] mb-4 max-w-2xl">
        Need a higher-resolution asset, a custom lockup, or a written quote for press? Open an issue on GitHub — the maintainers will respond in the thread.
      </p>
      <a
        href="https://github.com/jon-tompkins/aegis-public/issues/new"
        target="_blank"
        rel="noopener noreferrer"
        className="btn-primary"
      >
        Open an issue
      </a>
    </Section>
  )
}

function Footer() {
  return (
    <footer className="py-8 px-6 sm:px-8 lg:px-12 border-t border-[#1a2a4a]">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <ShieldIcon className="w-5 h-5 text-[#00d4ff]" />
          <span className="font-['Space_Grotesk'] font-semibold text-white">Aegis Chain</span>
        </div>
        <div className="text-[#4a5a7a] text-sm font-['JetBrains_Mono']">
          aegischain.xyz/brand
        </div>
        <div className="flex items-center gap-4 text-sm text-[#4a5a7a]">
          <Link href="/" className="hover:text-[#c8d4e8] transition-colors">Home</Link>
          <span>·</span>
          <Link href="/docs/soul-hash" className="hover:text-[#c8d4e8] transition-colors">Docs</Link>
          <span>·</span>
          <a href="https://github.com/jon-tompkins/aegis-public" target="_blank" rel="noopener noreferrer" className="hover:text-[#c8d4e8] transition-colors">GitHub</a>
        </div>
      </div>
    </footer>
  )
}

export default function BrandPage() {
  return (
    <main className="min-h-screen">
      <Nav />
      <Hero />
      <NameSection />
      <LogoSection />
      <ColorSection />
      <TypeSection />
      <VoiceSection />
      <UsageSection />
      <ContactSection />
      <Footer />
    </main>
  )
}
