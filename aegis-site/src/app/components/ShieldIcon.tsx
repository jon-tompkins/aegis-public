/**
 * Renders the canonical Aegis mesh shield from /public/brand/aegis-mark.svg.
 *
 * The mark is pre-colored canonical cyan (#00D4FF) with a transparent
 * background. If a future non-cyan variant is needed, add a prop that swaps
 * to a different pre-rendered file (e.g. aegis-mark-white.svg); do not try
 * to recolor the mark via CSS (mask-image works but loses the fine mesh
 * detail on small sizes).
 */
export default function ShieldIcon({ className = '' }: { className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/brand/aegis-mark.svg"
      alt=""
      aria-hidden="true"
      className={className}
    />
  )
}
