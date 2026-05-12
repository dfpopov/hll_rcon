interface AvatarProps {
  url?: string | null
  name: string
  size?: number  // pixels
}

/**
 * Steam avatar with graceful fallback to colored circle with first-letter initial.
 * If avatar_url is null/empty/load-fails, shows a deterministic color block.
 */
export default function Avatar({ url, name, size = 32 }: AvatarProps) {
  const initial = (name || '?').trim().charAt(0).toUpperCase() || '?'
  // Hash-based deterministic color for fallback
  const colors = [
    'bg-rose-700', 'bg-amber-700', 'bg-emerald-700', 'bg-sky-700',
    'bg-violet-700', 'bg-fuchsia-700', 'bg-teal-700', 'bg-orange-700',
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0
  const fallbackColor = colors[Math.abs(hash) % colors.length]

  if (url) {
    return (
      <img
        src={url}
        alt={name}
        width={size}
        height={size}
        className="rounded inline-block object-cover bg-zinc-800"
        loading="lazy"
        onError={(e) => {
          // Mark image as broken so a CSS-only fallback can render
          ;(e.currentTarget as HTMLImageElement).style.display = 'none'
        }}
      />
    )
  }
  return (
    <span
      className={`inline-flex items-center justify-center rounded text-xs font-bold text-white ${fallbackColor}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {initial}
    </span>
  )
}
