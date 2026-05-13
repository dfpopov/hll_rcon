import { Outlet } from 'react-router'
import Footer from '../footer'
import { Header } from '../header'
import { UnifiedHeader } from '../header/unified'
import { Helmet } from 'react-helmet'
import { publicInfoQueryOptions } from '@/lib/queries/public-info'
import { useTranslation } from 'react-i18next'
import { useSuspenseQuery } from '@tanstack/react-query'

// When this app is embedded inside stats_app at /live/, render a navbar that
// matches stats_app exactly so the two SPAs feel like one site. Detection
// is purely build-time via Vite's BASE_URL (set to /live/ in stats_app's
// Dockerfile, default / for the standalone 7010 build).
const IS_EMBEDDED = import.meta.env.BASE_URL !== '/'

export default function Layout() {
  const { data: publicInfo } = useSuspenseQuery(publicInfoQueryOptions)
  const { t } = useTranslation('translation')

  return (
    <>
      <Helmet defaultTitle={t('title')} titleTemplate={`%s | ${publicInfo?.name?.name ?? t('title')}`} />
      <div className="relative flex flex-col min-h-screen">
        {IS_EMBEDDED ? <UnifiedHeader /> : <Header />}
        <main className="container px-1 pb-10 sm:px-4 relative flex flex-col grow bg-background gap-1">
          <Outlet />
        </main>
        <Footer />
      </div>
    </>
  )
}
