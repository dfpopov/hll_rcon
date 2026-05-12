/**
 * Country flag image from ISO 3166-1 alpha-2 code via flagcdn.com.
 *
 * Switched from Unicode Regional Indicator Symbol Letters to a CDN PNG
 * because Windows browsers (Chrome/Edge) ship no flag emoji font and render
 * the codepoints as bare letters ("🇺🇦" → "UA"). flagcdn.com serves all ISO
 * country flags as small PNGs with optional 2x variants for retina.
 */
interface CountryFlagProps {
  iso?: string | null
  className?: string
  showCode?: boolean  // if true, also show "UA" next to flag
}

export default function CountryFlag({ iso, className = '', showCode = false }: CountryFlagProps) {
  if (!iso || iso.length !== 2) return null
  const code = iso.toLowerCase()
  return (
    <span className={`inline-flex items-center gap-1 align-middle ${className}`} title={iso}>
      <img
        src={`https://flagcdn.com/24x18/${code}.png`}
        srcSet={`https://flagcdn.com/48x36/${code}.png 2x`}
        width={24}
        height={18}
        alt={iso}
        className="inline-block rounded-sm"
        loading="lazy"
      />
      {showCode && <span className="text-xs text-zinc-400 font-mono">{iso}</span>}
    </span>
  )
}
