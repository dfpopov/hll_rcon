/**
 * Country flag emoji from ISO 3166-1 alpha-2 country code.
 * Uses Regional Indicator Symbol Letters — supported natively by modern
 * fonts; falls back to plain code text if not.
 */
interface CountryFlagProps {
  iso?: string | null
  className?: string
  showCode?: boolean  // if true, also show "UA" next to flag
}

function isoToFlag(iso: string): string {
  if (iso.length !== 2) return ''
  return iso
    .toUpperCase()
    .replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
}

export default function CountryFlag({ iso, className = '', showCode = false }: CountryFlagProps) {
  if (!iso || iso.length !== 2) return null
  return (
    <span className={className} title={iso}>
      <span className="text-base leading-none">{isoToFlag(iso)}</span>
      {showCode && <span className="ml-1 text-xs text-zinc-400 font-mono">{iso}</span>}
    </span>
  )
}
