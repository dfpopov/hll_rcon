import type resources from '../types/resources'

type NavigationKeys = keyof (typeof resources)['navigation']

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
      url:
        import.meta.env.VITE_STATS_APP_URL ||
        (import.meta.env.BASE_URL !== '/' ? '/' : 'http://95.111.230.75:7012/'),
      label: '📊 All-time stats',
    },
  ] as { url: string; label: string }[],
}

export default siteConfig
