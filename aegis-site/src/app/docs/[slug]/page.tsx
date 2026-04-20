import fs from 'fs'
import path from 'path'
import { markdownToHtml } from '../../lib/markdown'
import { notFound } from 'next/navigation'

const SPECS_PATH = path.join(process.cwd(), 'src/app/docs/specs')

const docSlugs: Record<string, string> = {
  'roadmap': 'roadmap.md',
  'constitution': 'constitution.md',
  'soul-hash': 'soul-hash.md',
  'intent-mapping': 'intent-mapping.md',
  'training-pipeline': 'training-pipeline.md',
  'agent-comms': 'agent-comms.md',
  'guardian': 'guardian.md',
  'hack-taxonomy': 'hack-taxonomy.md',
  'byo-model': 'byo-model.md',
  'memory-strategy': 'memory-strategy.md',
  'off-chain-store': 'off-chain-store.md',
  'staking-systems': 'staking-systems.md',
  'economics': 'economics.md',
}

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  return Object.keys(docSlugs).map((slug) => ({ slug }))
}

export default async function DocPage({ params }: PageProps) {
  const { slug } = await params
  const filename = docSlugs[slug]

  if (!filename) {
    notFound()
  }

  const filePath = path.join(SPECS_PATH, filename)

  let content = ''
  try {
    content = fs.readFileSync(filePath, 'utf8')
  } catch {
    notFound()
  }

  const html = await markdownToHtml(content)

  return (
    <div className="docs-content">
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
