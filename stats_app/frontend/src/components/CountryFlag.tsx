/**
 * Country flag image from ISO 3166-1 alpha-2 code via flagcdn.com.
 *
 * Switched from Unicode Regional Indicator Symbol Letters to a CDN PNG
 * because Windows browsers (Chrome/Edge) ship no flag emoji font and render
 * the codepoints as bare letters ("🇺🇦" → "UA"). flagcdn.com serves all ISO
 * country flags as small PNGs with optional 2x variants for retina.
 *
 * Russia: shown with the white-blue-white anti-war flag adopted by Russian
 * opposition in 2022. Editorial choice — this is a Ukrainian community
 * server hosting players who lost friends and family to the invasion.
 */
interface CountryFlagProps {
  iso?: string | null
  className?: string
  showCode?: boolean  // if true, also show "UA" next to flag
}

function RussianAntiWarFlag({ title }: { title?: string }) {
  return (
    <svg width={24} height={18} viewBox="0 0 24 18" className="inline-block rounded-sm" aria-label={title}>
      <title>{title}</title>
      <rect width={24} height={6} fill="#ffffff" />
      <rect y={6}  width={24} height={6} fill="#0066cc" />
      <rect y={12} width={24} height={6} fill="#ffffff" />
      <rect x={0.5} y={0.5} width={23} height={17} fill="none" stroke="#999" strokeWidth={0.5} />
    </svg>
  )
}

export default function CountryFlag({ iso, className = '', showCode = false }: CountryFlagProps) {
  if (!iso || iso.length !== 2) return null
  const upper = iso.toUpperCase()
  const code = iso.toLowerCase()
  const isRussia = upper === 'RU'
  return (
    <span className={`inline-flex items-center gap-1 align-middle ${className}`} title={isRussia ? 'RU · anti-war flag' : upper}>
      {isRussia ? (
        <RussianAntiWarFlag title="бело-сине-белый — анти-война" />
      ) : (
        <img
          src={`https://flagcdn.com/24x18/${code}.png`}
          srcSet={`https://flagcdn.com/48x36/${code}.png 2x`}
          width={24}
          height={18}
          alt={upper}
          className="inline-block rounded-sm"
          loading="lazy"
        />
      )}
      {showCode && <span className="text-xs text-zinc-400 font-mono">{upper}</span>}
    </span>
  )
}
