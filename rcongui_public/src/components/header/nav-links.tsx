'use client'
import siteConfig from '@/lib/siteConfig'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router'
import { Button } from '../ui/button'

export function NavLinks() {
  const pathname = useLocation()
  const { t } = useTranslation('navigation')

  return (
    <>
      {siteConfig.navLinks.map((link) => {
        const isNotActive = pathname.pathname !== link.href
        return (
          <Button
            key={link.href}
            variant={'text'}
            className={cn(
              'text-sm font-medium transition-colors focus:ring-primary',
              isNotActive && 'text-muted-foreground',
              !link.disabled && 'hover:text-primary',
              link.disabled && 'text-muted-foreground/50',
            )}
            asChild
          >
            <Link key={link.href} to={link.href} aria-disabled={!!link.disabled}>
              {t(link.labelKey)}
            </Link>
          </Button>
        )
      })}
      {/* External links — plain <a>, render after internal nav. */}
      {siteConfig.externalLinks.map((link) => (
        <Button
          key={link.url}
          variant={'text'}
          className="text-sm font-medium transition-colors focus:ring-primary text-muted-foreground hover:text-primary"
          asChild
        >
          <a href={link.url}>{link.label}</a>
        </Button>
      ))}
    </>
  )
}
