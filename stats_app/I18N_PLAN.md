# HLL Stats — i18n implementation plan

Multi-language support for stats_app (port 7012, all-time stats UI),
matching the 14 languages already supported by rcongui_public at /live/.

## Languages (from `rcongui_public/src/i18n/config.ts`)

```
en24h, en, de, fr, es, zh-Hans, zh-Hant, ja, ko, pt, it, ru, uk, cs
```

## Technical setup (~2 hours, one-time)

1. Add deps to `stats_app/frontend/package.json`:
   - `react-i18next`
   - `i18next`
   - `i18next-browser-languagedetector`
   - `i18next-resources-to-backend` (lazy-loaded per-language JSON)
2. Create `stats_app/frontend/src/i18n/config.ts` mirroring rcongui_public's
   setup so language detection (localStorage key `i18nextLng`) is identical
   and switching language on /live/ persists to /7012/ (and vice versa).
3. Locale files: `stats_app/frontend/src/i18n/locales/{lang}/translation.json`
4. Wrap App in `I18nextProvider` in `main.tsx`.
5. Add `DropdownLanguageSelector` to `Layout.tsx` navbar (clone from
   rcongui_public).

## Content scope — tiered by editorial sensitivity

### Tier 1 — UI chrome (must translate) — ~80 keys

- Navigation: `Лідерборд`, `Рекорди ★`, `1 матч ⚡`, `Досягнення`, `Стилі`,
  `Порівняння`, `Hall of Shame`, `Карта`, `Live`, `Матчі`
- Table headers: `#`, `ГРАВЕЦЬ`, `KILLS`, `DEATHS`, `TK`, `K/D`, `KPM`,
  `ЧАС ГРИ`, `МАТЧІВ`, `LVL`
- Filter labels: `Період`, `Сторона / фракція`, `Режим`, `Карта`,
  `Клас зброї`, `Конкретна зброя`, `Мін. матчів`, `Пошук гравця`
- Buttons / CTAs: `Завантажити`, `Скинути`, `Порівняти`, `Додати в порівняння`
- Page titles: `Топ гравці`, `Стилі гри`, `Карта світу`, `Hall of Shame`
- Empty states: `Виберіть гравця`, `Немає даних`, `Завантаження…`
- Tabs on player detail: `Огляд`, `Зброя`, `Карти`, `Досягнення`, `Стилі`,
  `Останні матчі`, `Усі / З титулами`

### Tier 2 — Achievement names + descriptions — ~74 keys (37 × 2)

EDITORIAL DECISION NEEDED. Examples that are culture-specific:
- `Самурай` / `50+ убивств холодною зброєю`
- `Танковий бог` / `200+ kills as Tank + Anti-Tank`
- `ПТН ПНХ` (kick reason — cultural specificity, MUST stay Ukrainian)

Options:
  a. Translate all (loses Ukrainian flavor)
  b. Keep names Ukrainian, translate descriptions
  c. Keep all Ukrainian (mark as community brand)

### Tier 3 — Playstyle archetypes — ~60 keys (30 × 2)

Same editorial question. Examples:
- `Майстер жити` / `K/D >= 3.0, не вмирає`
- `Раб клану` / `Грає тільки з конкретним кланом`
- `Ритуал` / `30% матчів у пік-годину`

### Tier 4 — Match titles — ~30 keys

Examples: `Скажений`, `Безжальний`, `Спідран`, `Тренування`, `Кулеметник`.
Same editorial question.

### Tier 5 — Number / date formatting

Replace hardcoded `toLocaleString('uk-UA')` with `i18n.language`-driven
formatter. Mirror rcongui_public's `LocaleHandler` for dayjs.

## Recommended phasing

| Phase | Scope | Estimated time |
|------|------|--------------|
| 1 | Tier 1 chrome, 4 priority languages (`en`, `de`, `pl`, `ru`) | 3 h + translator review |
| 2 | Tier 1 chrome, all 14 languages | +2 h (AI first pass + native review) |
| 3 | Decide Tier 2-4 editorial policy, translate accordingly | Variable |

Priority languages chosen by world-map distribution (top non-UA after EN/DE
already covered: PL=467, RU=215). Together with EN, covers ~40% of
non-Ukrainian audience.

## File structure (proposed)

```
stats_app/frontend/src/
├── i18n/
│   ├── config.ts                  # i18next init, language list
│   ├── LocaleHandler.tsx          # dayjs locale sync
│   └── locales/
│       ├── en/translation.json
│       ├── de/translation.json
│       ├── pl/translation.json
│       └── ru/translation.json
└── main.tsx                       # I18nextProvider wrap
```

## Cross-app language sync

Both rcongui_public and stats_app read/write the same localStorage key
(`i18nextLng`) so switching language on /live/ persists to /7012/ and
vice versa. `i18next-browser-languagedetector` defaults to that key —
wins out of the box, no extra config.

## Open editorial questions to resolve before Tier 2-4

1. Are achievement / playstyle / match-title names part of the **community brand**
   (keep Ukrainian) or part of the **product UI** (translate)?
2. If keep Ukrainian — should the description still translate, with the
   original name shown as a "decoration"?
3. Is `ПТН ПНХ` (kick reason) translatable or strictly Ukrainian?

Until these answers are pinned, ship Phase 1 (Tier 1 chrome) and gather
feedback from non-Ukrainian players on whether further translation is
even desired.
