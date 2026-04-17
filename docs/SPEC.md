# Aegis Chain — Site Spec

**Spec Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** For review  

---

## Concept

Aegis is a security-first Ethereum L2 with AI agent validators. The site should feel like a **secure terminal from the future** — not a typical crypto landing page. Think: defense contractor meets cyberpunk. Precise, dark, confident. The shield metaphor is the visual anchor.

---

## Site Structure

### Landing Page (/)

**Sections:**
1. **Hero** — "The chain that fights back." One-line value prop. Animated shield/grid visual. CTA: "Read the Spec" + "View on GitHub"
2. **What is Aegis** — 3 sentences. L2 + AI validators + exploit pause. Simple diagram of tx flow.
3. **Why it matters** — 3 cards: (1) Agentic screening, (2) Soul hash verification, (3) Economic alignment. Brief, no jargon.
4. **How it works** — Numbered steps: tx submitted → Guardian screens → clear or escalate → validators vote → result on-chain.
5. **Stack** — OP Stack + AI agents + Ethereum security. Minimal, credible.
6. **Get involved** — Link to GitHub, specs, Telegram.

**Design:** Full-width sections, alternating dark/very-dark backgrounds. No large hero image — animated SVG grid/shield in CSS.

---

### Docs (/docs/)

**Structure:**
```
docs/
├── index.md                    → Redirects to /docs/chain-design
├── chain-design.md             → Architecture, tx flow, intervention
├── soul-hash.md               → Profile Merkle tree, OP Stack patch
├── intent-mapping.md           → ClickHouse + LMDB, screening API
├── agent-comms.md              → Manifold integration
├── guardian.md                → Guardian vs validator (ship later)
├── training-pipeline.md       → Clark's spec (linked)
├── hack-taxonomy.md            → Exploit patterns, Tier 1 rules
├── byo-model.md               → BYO-model interface
├── memory-strategy.md          → Tenet/teacups/MRI for Aegis
├── staking-systems.md          → EigenLayer, UMA, chain-native DeFi
├── economics.md                → Clark's spec (linked)
└── SPEC.md                    → This file
```

**Nav:** Left sidebar, collapsible sections grouped by category.

---

## Design System

### Colors
```css
--bg-deep:     #050810;   /* page background */
--bg-dark:     #0a0f1a;   /* section alternates */
--bg-card:     #0d1525;   /* cards, nav */
--border:      #1a2a4a;   /* subtle borders */
--accent:      #00d4ff;   /* cyan — primary accent */
--accent-dim:  #00d4ff22; /* accent glow */
--accent-2:    #4a9eff;   /* secondary blue */
--text:        #c8d4e8;   /* body text */
--text-dim:    #4a5a7a;   /* muted text */
--success:     #00cc88;   /* clear / safe */
--warn:        #ffd700;   /* escalate / watch */
--danger:      #ff4455;   /* reject / slash */
```

### Typography
- **Headings:** JetBrains Mono or Space Grotesk (monospace feel, futuristic)
- **Body:** IBM Plex Sans (readable, technical)
- **Code/terminal:** JetBrains Mono
- **Scale:** 48px hero → 32px h1 → 24px h2 → 18px h3 → 16px body

### Motion
- Entrance: fade-up, 400ms ease-out, staggered 80ms between elements
- Hover: subtle glow pulse on cards/buttons
- Hero: slow-pulsing shield SVG, grid lines animate on load
- Scroll: parallax-free, just intersection observer reveals

### Visual Assets
- Hero: CSS/SVG animated grid with shield silhouette
- Icons: Phosphor Icons (thin weight) or custom SVG
- No stock photos — all abstract/geometric
- Background: subtle dot grid pattern

---

## Technical Stack

**Framework:** Next.js (static export)  
**Hosting:** Vercel — push to `main` → auto-deploy  
**Domain:** aegischain.com (Jonto setting up)  
**Deployment:** Vercel GitHub integration — push to main → redeploys automatically  

**Why Next.js:**
- Markdown-native via `next-mdx-remote` or `next-docs-markdown`
- Specs already written in Markdown — minimal conversion
- Vercel static export = fast, cheap, simple
- Full control over design system
- API routes available if we need dynamic features later

---

## Implementation Plan

### Phase 1: Docs Site (build first)
1. Set up VitePress in `docs/` folder
2. Migrate existing specs as `.md` files
3. Configure sidebar nav
4. Deploy to GitHub Pages
5. Point aegischain.com at GitHub Pages

### Phase 2: Landing Page
1. Build home page with hero, sections, footer
2. Wire "Read the Spec" → /docs/chain-design
3. Wire "View on GitHub" → aegis-public repo
4. Deploy

### Phase 3: Living Docs
- Specs update on `main` → GitHub Pages auto-deploys
- New specs added to `docs/specs/` → auto-appear in nav
- Cron or GitHub Actions to keep docs in sync

---

## Open Questions

1. **Domain:** aegischain.com — grabbed yet? If not, need to know registrar.
2. **GitHub Pages enabled?** Need to confirm Pages is set up on the repo.
3. **Deployment approach:** GitHub Actions workflow or manual?
4. **Landing page copy:** What's the one-liner? "The chain that fights back" is a draft.
