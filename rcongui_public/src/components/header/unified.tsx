/**
 * Unified header rendered at the top of every rcongui_public page when this
 * app is embedded inside stats_app at /live/*.
 *
 * Goal: when a user clicks `🟢 Зараз` or `📜 Матчі` in stats_app and lands
 * here, the page chrome (background, brand, nav items, colors) is visually
 * IDENTICAL to stats_app's Layout.tsx — so the two SPAs feel like a single
 * site even though cross-app navigation is a full page load.
 *
 * Strategy:
 *   • Mirror stats_app's navbar token-for-token (zinc-950 bg, amber-500
 *     brand, amber-400 active accent, zinc-300 inactive, gap-4 layout).
 *   • Identical item set & order. Sub-nav for live (Поточний матч /
 *     Історія матчів) is folded into the primary nav so everything fits
 *     in a single row.
 *   • Cross-app links use plain <a> because the destinations
 *     (/records/all-time etc.) are routes in stats_app, not rcongui_public.
 *   • Override the body background (rcongui_public's index.html sets a war
 *     scene image inline) and hide the rcongui_public footer so the visual
 *     break between the two apps disappears.
 *   • Active state from `window.location.pathname` so it stays correct
 *     across full page navigations.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

// ─── Inline language selector — mirrors stats_app/LanguageSelector exactly ─────────
//
// rcongui_public's own DropdownLanguageSelector offers 14 languages and lives
// in its own DOM tree; stats_app's offers 5 with a custom dropdown. Showing
// two different selectors broke the "single site" illusion. This component
// is a self-contained copy of stats_app's variant — same icon, same 5 langs,
// same styling — embedded straight into UnifiedHeader.
//
// Language sync still works through localStorage["i18nextLng"] which both
// SPAs read on init.
// Same set rcongui_public ships with, in the order it uses upstream.
// stats_app's LanguageSelector mirrors this list verbatim. Russian is
// kept as a visible choice but stats_app aliases ru → uk content.
const UNIFIED_LANGS = [
  { code: 'uk',      name: 'Українська' },
  { code: 'en',      name: 'English' },
  { code: 'de',      name: 'Deutsch' },
  { code: 'ru',      name: 'Русский' },
  { code: 'pl',      name: 'Polski' },
  { code: 'fr',      name: 'Français' },
  { code: 'es',      name: 'Español' },
  { code: 'it',      name: 'Italiano' },
  { code: 'pt',      name: 'Português' },
  { code: 'cs',      name: 'Čeština' },
  { code: 'zh-Hans', name: '简体中文' },
  { code: 'zh-Hant', name: '繁體中文' },
  { code: 'ja',      name: '日本語' },
  { code: 'ko',      name: '한국어' },
] as const

function InlineLanguageSelector() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const current = (i18n.resolvedLanguage || i18n.language || 'en').slice(0, 7)

  useEffect(() => {
    if (!open) return
    const click = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', click)
    document.addEventListener('keydown', key)
    return () => {
      document.removeEventListener('mousedown', click)
      document.removeEventListener('keydown', key)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="size-8 inline-flex items-center justify-center rounded text-zinc-400 hover:text-amber-400 hover:bg-zinc-800/60 transition-colors"
        title={t('language', { defaultValue: 'Language' })}
        aria-label="Language"
        aria-expanded={open}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="m5 8 6 6" />
          <path d="m4 14 6-6 2-3" />
          <path d="M2 5h12" />
          <path d="M7 2h1" />
          <path d="m22 22-5-10-5 10" />
          <path d="M14 18h6" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl z-50 min-w-[160px] py-1">
          {UNIFIED_LANGS.map((l) => {
            const active = current === l.code || current.startsWith(l.code + '-')
            return (
              <button
                key={l.code}
                onClick={() => { i18n.changeLanguage(l.code); setOpen(false) }}
                className={`w-full text-left px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'text-amber-400 bg-zinc-800/70 font-medium'
                    : 'text-zinc-200 hover:bg-zinc-800/60 hover:text-amber-300'
                }`}
              >
                {l.name}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

type NavItem = {
  href: string
  // i18n key looked up in NAV_LABELS; emoji is part of the label so it stays
  // identical to stats_app/Layout.tsx.
  labelKey: NavLabelKey
  titleKey?: NavLabelKey
  match: 'exact' | 'prefix' | 'liveCurrent' | 'liveGames'
}
type NavLabelKey =
  | 'liveCurrent' | 'liveCurrentTitle' | 'liveGames' | 'liveGamesTitle'
  | 'leaderboard' | 'recordsAllTime' | 'recordsAllTimeTitle'
  | 'recordsSingleGame' | 'recordsSingleGameTitle' | 'achievements'
  | 'playstyles' | 'compare' | 'hallOfShame' | 'hallOfShameTitle' | 'worldMap'
  | 'searchPlaceholder'

// Inline translations for the unified-header nav. Mirrors the `nav.*` keys
// in stats_app/frontend/src/i18n/locales/<lang>/translation.json so both
// apps render identical text in every language. Kept here as a literal map
// rather than going through rcongui_public's react-i18next instance because:
//   (a) rcongui_public's locale files don't have these specific keys
//   (b) duplicating the dictionary here is cheaper than touching 14 JSONs
//       in the upstream package + risking drift from the stats_app set
// 14 languages match the LanguageSelector (UNIFIED_LANGS above). `ru` shows
// Ukrainian per the editorial decision.
type NavLabels = Record<NavLabelKey, string>
const NAV_LABELS: Record<string, NavLabels> = {
  uk: {
    liveCurrent: '🟢 Зараз', liveCurrentTitle: 'Поточний матч',
    liveGames: '📜 Матчі', liveGamesTitle: 'Історія матчів',
    leaderboard: 'Лідерборд', recordsAllTime: '★ Весь час', recordsAllTimeTitle: 'Рекорди за весь час',
    recordsSingleGame: '⚡ 1 матч', recordsSingleGameTitle: 'Рекорди в одному матчі',
    achievements: 'Досягнення', playstyles: '🎭 Стилі', compare: 'Порівняння',
    hallOfShame: '💀 Сором', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Карта',
    searchPlaceholder: '🔍 Пошук гравця...',
  },
  en: {
    liveCurrent: '🟢 Live', liveCurrentTitle: 'Current match',
    liveGames: '📜 Games', liveGamesTitle: 'Match history',
    leaderboard: 'Leaderboard', recordsAllTime: '★ All-time', recordsAllTimeTitle: 'All-time records',
    recordsSingleGame: '⚡ Single game', recordsSingleGameTitle: 'Single-game records',
    achievements: 'Achievements', playstyles: '🎭 Styles', compare: 'Compare',
    hallOfShame: '💀 Shame', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 World map',
    searchPlaceholder: '🔍 Search player...',
  },
  de: {
    liveCurrent: '🟢 Live', liveCurrentTitle: 'Aktuelles Spiel',
    liveGames: '📜 Spiele', liveGamesTitle: 'Spielverlauf',
    leaderboard: 'Bestenliste', recordsAllTime: '★ Allzeit', recordsAllTimeTitle: 'Allzeit-Rekorde',
    recordsSingleGame: '⚡ Einzelspiel', recordsSingleGameTitle: 'Rekorde in einem Spiel',
    achievements: 'Erfolge', playstyles: '🎭 Stile', compare: 'Vergleich',
    hallOfShame: '💀 Schande', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Weltkarte',
    searchPlaceholder: '🔍 Spieler suchen...',
  },
  pl: {
    liveCurrent: '🟢 Teraz', liveCurrentTitle: 'Bieżący mecz',
    liveGames: '📜 Mecze', liveGamesTitle: 'Historia meczów',
    leaderboard: 'Ranking', recordsAllTime: '★ Cały czas', recordsAllTimeTitle: 'Rekordy z całego czasu',
    recordsSingleGame: '⚡ 1 mecz', recordsSingleGameTitle: 'Rekordy w jednym meczu',
    achievements: 'Osiągnięcia', playstyles: '🎭 Style', compare: 'Porównanie',
    hallOfShame: '💀 Wstyd', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Mapa',
    searchPlaceholder: '🔍 Szukaj gracza...',
  },
  fr: {
    liveCurrent: '🟢 En direct', liveCurrentTitle: 'Match en cours',
    liveGames: '📜 Matchs', liveGamesTitle: 'Historique des matchs',
    leaderboard: 'Classement', recordsAllTime: '★ Tous-temps', recordsAllTimeTitle: 'Records de tous les temps',
    recordsSingleGame: '⚡ 1 match', recordsSingleGameTitle: 'Records sur un match',
    achievements: 'Succès', playstyles: '🎭 Styles', compare: 'Comparer',
    hallOfShame: '💀 Honte', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Carte',
    searchPlaceholder: '🔍 Chercher un joueur...',
  },
  es: {
    liveCurrent: '🟢 En vivo', liveCurrentTitle: 'Partida actual',
    liveGames: '📜 Partidas', liveGamesTitle: 'Historial de partidas',
    leaderboard: 'Clasificación', recordsAllTime: '★ Histórico', recordsAllTimeTitle: 'Récords de todos los tiempos',
    recordsSingleGame: '⚡ 1 partida', recordsSingleGameTitle: 'Récords en una partida',
    achievements: 'Logros', playstyles: '🎭 Estilos', compare: 'Comparar',
    hallOfShame: '💀 Vergüenza', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Mapa',
    searchPlaceholder: '🔍 Buscar jugador...',
  },
  it: {
    liveCurrent: '🟢 Live', liveCurrentTitle: 'Partita corrente',
    liveGames: '📜 Partite', liveGamesTitle: 'Cronologia partite',
    leaderboard: 'Classifica', recordsAllTime: '★ All-time', recordsAllTimeTitle: 'Record di tutti i tempi',
    recordsSingleGame: '⚡ 1 match', recordsSingleGameTitle: 'Record in un match',
    achievements: 'Obiettivi', playstyles: '🎭 Stili', compare: 'Confronta',
    hallOfShame: '💀 Vergogna', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Mappa',
    searchPlaceholder: '🔍 Cerca giocatore...',
  },
  pt: {
    liveCurrent: '🟢 Ao vivo', liveCurrentTitle: 'Partida atual',
    liveGames: '📜 Partidas', liveGamesTitle: 'Histórico de partidas',
    leaderboard: 'Classificação', recordsAllTime: '★ Histórico', recordsAllTimeTitle: 'Recordes de todos os tempos',
    recordsSingleGame: '⚡ 1 partida', recordsSingleGameTitle: 'Recordes em uma partida',
    achievements: 'Conquistas', playstyles: '🎭 Estilos', compare: 'Comparar',
    hallOfShame: '💀 Vergonha', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Mapa',
    searchPlaceholder: '🔍 Buscar jogador...',
  },
  cs: {
    liveCurrent: '🟢 Nyní', liveCurrentTitle: 'Aktuální zápas',
    liveGames: '📜 Zápasy', liveGamesTitle: 'Historie zápasů',
    leaderboard: 'Žebříček', recordsAllTime: '★ Všechen čas', recordsAllTimeTitle: 'Rekordy všech dob',
    recordsSingleGame: '⚡ 1 zápas', recordsSingleGameTitle: 'Rekordy v jednom zápase',
    achievements: 'Úspěchy', playstyles: '🎭 Styly', compare: 'Porovnat',
    hallOfShame: '💀 Hanba', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 Mapa',
    searchPlaceholder: '🔍 Hledat hráče...',
  },
  'zh-Hans': {
    liveCurrent: '🟢 实时', liveCurrentTitle: '当前比赛',
    liveGames: '📜 比赛', liveGamesTitle: '比赛历史',
    leaderboard: '排行榜', recordsAllTime: '★ 全时段', recordsAllTimeTitle: '全时段记录',
    recordsSingleGame: '⚡ 单场', recordsSingleGameTitle: '单场记录',
    achievements: '成就', playstyles: '🎭 风格', compare: '对比',
    hallOfShame: '💀 耻辱', hallOfShameTitle: '耻辱殿堂', worldMap: '🌍 地图',
    searchPlaceholder: '🔍 搜索玩家...',
  },
  'zh-Hant': {
    liveCurrent: '🟢 即時', liveCurrentTitle: '目前比賽',
    liveGames: '📜 比賽', liveGamesTitle: '比賽歷史',
    leaderboard: '排行榜', recordsAllTime: '★ 全時段', recordsAllTimeTitle: '全時段紀錄',
    recordsSingleGame: '⚡ 單場', recordsSingleGameTitle: '單場紀錄',
    achievements: '成就', playstyles: '🎭 風格', compare: '對比',
    hallOfShame: '💀 恥辱', hallOfShameTitle: '恥辱殿堂', worldMap: '🌍 地圖',
    searchPlaceholder: '🔍 搜尋玩家...',
  },
  ja: {
    liveCurrent: '🟢 ライブ', liveCurrentTitle: '現在の試合',
    liveGames: '📜 試合', liveGamesTitle: '試合履歴',
    leaderboard: 'ランキング', recordsAllTime: '★ 全期間', recordsAllTimeTitle: '全期間の記録',
    recordsSingleGame: '⚡ 1試合', recordsSingleGameTitle: '1試合の記録',
    achievements: '実績', playstyles: '🎭 スタイル', compare: '比較',
    hallOfShame: '💀 恥', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 地図',
    searchPlaceholder: '🔍 プレイヤー検索...',
  },
  ko: {
    liveCurrent: '🟢 라이브', liveCurrentTitle: '현재 경기',
    liveGames: '📜 경기', liveGamesTitle: '경기 기록',
    leaderboard: '리더보드', recordsAllTime: '★ 전체 기간', recordsAllTimeTitle: '전체 기간 기록',
    recordsSingleGame: '⚡ 1경기', recordsSingleGameTitle: '1경기 기록',
    achievements: '업적', playstyles: '🎭 스타일', compare: '비교',
    hallOfShame: '💀 수치', hallOfShameTitle: 'Hall of Shame', worldMap: '🌍 지도',
    searchPlaceholder: '🔍 플레이어 검색...',
  },
}
// `ru` editorial alias → uk (matches stats_app's i18n/config.ts ru→uk redirect).
NAV_LABELS.ru = NAV_LABELS.uk

function labels(lng: string): NavLabels {
  return NAV_LABELS[lng] || NAV_LABELS[lng.split('-')[0]] || NAV_LABELS.en
}

// Identical order & href set to stats_app/Layout.tsx. Live items first.
const NAV: NavItem[] = [
  { href: '/live/',               labelKey: 'liveCurrent',       titleKey: 'liveCurrentTitle',       match: 'liveCurrent' },
  { href: '/live/games',          labelKey: 'liveGames',         titleKey: 'liveGamesTitle',         match: 'liveGames' },
  { href: '/leaderboard',         labelKey: 'leaderboard',                                            match: 'prefix' },
  { href: '/records/all-time',    labelKey: 'recordsAllTime',    titleKey: 'recordsAllTimeTitle',    match: 'prefix' },
  { href: '/records/single-game', labelKey: 'recordsSingleGame', titleKey: 'recordsSingleGameTitle', match: 'prefix' },
  { href: '/achievements',        labelKey: 'achievements',                                           match: 'prefix' },
  { href: '/playstyles',          labelKey: 'playstyles',                                             match: 'prefix' },
  { href: '/compare',             labelKey: 'compare',                                                match: 'prefix' },
  { href: '/hall-of-shame',       labelKey: 'hallOfShame',       titleKey: 'hallOfShameTitle',       match: 'prefix' },
  { href: '/server/countries',    labelKey: 'worldMap',                                               match: 'prefix' },
]

// ─── Inline player search — mirrors stats_app/NavSearch ─────────────────────
//
// stats_app exposes /api/players/autocomplete via its FastAPI backend; from
// the same origin (`7012/...`) we can call it directly. Clicking a result
// navigates to /player/{steam_id} which redirects out of /live/ onto the
// stats_app SPA at /player/<id>.
type Suggestion = { steam_id: string; name: string; avatar_url: string | null; matches: number }

function InlineSearch({ placeholder }: { placeholder: string }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = q.trim()
    if (t.length < 2) { setResults([]); return }
    let cancelled = false
    const id = setTimeout(() => {
      fetch(`/api/players/autocomplete?q=${encodeURIComponent(t)}&limit=8`)
        .then((r) => r.ok ? r.json() : [])
        .then((rs) => { if (!cancelled) setResults(Array.isArray(rs) ? rs : []) })
        .catch(() => { if (!cancelled) setResults([]) })
    }, 200)
    return () => { cancelled = true; clearTimeout(id) }
  }, [q])

  useEffect(() => {
    if (!open) return
    const click = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
      if (e.key === 'Enter' && results.length > 0 && ref.current?.contains(document.activeElement)) {
        window.location.href = `/player/${results[0].steam_id}`
      }
    }
    document.addEventListener('mousedown', click)
    document.addEventListener('keydown', key)
    return () => {
      document.removeEventListener('mousedown', click)
      document.removeEventListener('keydown', key)
    }
  }, [open, results])

  return (
    <div ref={ref} className="relative">
      <input
        type="text"
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        className="w-56 bg-zinc-800/80 text-zinc-100 px-3 py-1.5 rounded text-sm placeholder-zinc-500
                   focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:bg-zinc-800"
      />
      {open && results.length > 0 && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-zinc-900 border border-zinc-700 rounded-lg
                        shadow-2xl z-50 max-h-80 overflow-y-auto">
          {results.map((s) => (
            <a
              key={s.steam_id}
              href={`/player/${s.steam_id}`}
              className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-800 border-b border-zinc-800 last:border-0"
            >
              {s.avatar_url && (
                <img src={s.avatar_url} alt="" width={24} height={24} className="rounded shrink-0" loading="lazy" />
              )}
              <span className="flex-1 text-sm text-zinc-200 truncate">{s.name}</span>
              <span className="text-xs text-zinc-500 tabular-nums">{s.matches}m</span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

function navClass(active: boolean): string {
  return `text-sm hover:text-amber-400 transition-colors ${
    active ? 'text-amber-400 font-medium' : 'text-zinc-300'
  }`
}

function isActive(item: NavItem, pathname: string): boolean {
  switch (item.match) {
    case 'exact':
      return pathname === item.href
    case 'liveCurrent':
      // "🟢 Зараз" → /live/ — active only on /live or /live/ (current match page)
      return pathname === '/live' || pathname === '/live/'
    case 'liveGames':
      // "📜 Матчі" → /live/games — active on any /live/games/* deep link
      return pathname.startsWith('/live/games')
    case 'prefix':
    default:
      return pathname.startsWith(item.href)
  }
}

export function UnifiedHeader() {
  const { i18n } = useTranslation()
  const lng = i18n.resolvedLanguage || i18n.language || 'en'
  const L = labels(lng)
  const pathname =
    typeof window !== 'undefined' ? window.location.pathname : '/live/'

  // Override the war-scene body background that rcongui_public sets inline
  // in index.html so the embedded variant matches stats_app's dark theme.
  // Also force the `dark` class on <html> so rcongui_public's Tailwind
  // dark: variants apply — stats_app is dark-only, so we lock that here
  // and drop the theme toggle entirely.
  useLayoutEffect(() => {
    const prev = {
      bgImage: document.body.style.backgroundImage,
      bgColor: document.body.style.backgroundColor,
    }
    document.body.style.backgroundImage = 'none'
    document.body.style.backgroundColor = '#09090b' // zinc-950
    document.documentElement.classList.add('dark')
    return () => {
      document.body.style.backgroundImage = prev.bgImage
      document.body.style.backgroundColor = prev.bgColor
    }
  }, [])

  return (
    <header className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3 flex-wrap">
        {/* Brand → / which nginx redirects to /live/. */}
        <a href="/" className="text-amber-500 font-bold text-lg hover:text-amber-400 transition-colors">
          HLL Stats
        </a>
        {NAV.map((item) => (
          <a
            key={item.href}
            href={item.href}
            title={item.titleKey ? L[item.titleKey] : undefined}
            className={navClass(isActive(item, pathname))}
          >
            {L[item.labelKey]}
          </a>
        ))}
        <InlineSearch placeholder={L.searchPlaceholder} />
        <div className="ml-auto flex items-center">
          {/* Theme toggle removed — stats_app is dark-only and we lock dark
              mode here too to keep both apps visually consistent.
              Language selector inlined (14 langs, same as stats_app). */}
          <InlineLanguageSelector />
        </div>
      </div>
    </header>
  )
}
