/**
 * Tiny helpers for translating achievement / playstyle / match-title titles
 * and descriptions. The backend returns these in Ukrainian; i18n/locales/<lng>
 * carries the `meta.*` namespace with localized versions per id.
 *
 * Lookup chain:
 *   1. meta.<type>.<id>.<field> in the current language
 *   2. meta.<type>.<id>.<field> in fallbackLng (en)
 *   3. defaultValue — the backend-provided Ukrainian string (so unknown
 *      languages always render *something* sensible)
 *
 * Components import these hooks instead of inlining the t() call so the
 * key naming stays consistent and a missing-id never causes a "meta.x.y.z"
 * literal to leak into the UI.
 */
import { useTranslation } from 'react-i18next'

type MetaType = 'achievements' | 'playstyles' | 'matchTitles'

export function useMetaLabel() {
  const { t } = useTranslation()
  return {
    title(type: MetaType, id: string, fallback: string): string {
      return t(`meta.${type}.${id}.title`, { defaultValue: fallback })
    },
    description(type: MetaType, id: string, fallback: string): string {
      return t(`meta.${type}.${id}.description`, { defaultValue: fallback })
    },
  }
}
