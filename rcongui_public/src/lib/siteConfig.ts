import type resources from '../types/resources'

type NavigationKeys = keyof (typeof resources)['navigation']

/**
 * Resolve the base URL of the sibling stats_app where /player/{id} and
 * /search live. Three modes:
 *   1. Override via VITE_STATS_APP_URL env var (build-time)
 *   2. Embedded build (BASE_URL !== '/'): we're already inside stats_app
 *      under /live/, so return '/' for same-origin relative links
 *   3. Standalone build (BASE_URL === '/'): we're on the public rcongui
 *      (port 7010) and stats_app sits on a sibling port. Build URL from
 *      the page's current host so it works on any IP/domain.
 *
 * Always returns a string ending in '/' so callers can do
 * `${statsAppBaseUrl()}player/${id}`.
 */
export function statsAppBaseUrl(): string {
  const override = import.meta.env.VITE_STATS_APP_URL
  if (override) return override.endsWith('/') ? override : override + '/'
  if (import.meta.env.BASE_URL !== '/') return '/'
  if (typeof window === 'undefined') return '/'
  return `${window.location.protocol}//${window.location.hostname}:7012/`
}

const siteConfig = {
  crconGitUrl: 'https://github.com/MarechJ/hll_rcon_tool',
  teamName: 'CRCON Team',
  navLinks: [
    {
      href: '/',
      labelKey: 'currentGame',
    },
    {
      href: '/games',
      labelKey: 'gameHistory',
    },
  ] as { href: string; labelKey: NavigationKeys; disabled?: boolean }[],
  // External links rendered alongside internal nav. Rendered via plain <a>
  // (target="_self"). `url` resolves at build time:
  //   • Standalone build (port 7010) → absolute URL set via VITE_STATS_APP_URL
  //     (typically http://<host>:7012/) so users jump to the sibling app.
  //   • Embedded build under /live/ inside stats_app → relative path '/' so
  //     users go back up to the host stats_app root.
  // Detection is purely build-time — see also vite.config.mts and Dockerfile.
  externalLinks: [
    {
      url: statsAppBaseUrl(),
      label: '📊 All-time stats',
    },
  ] as { url: string; label: string }[],
}

export default siteConfig
