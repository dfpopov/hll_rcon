/**
 * HLL map_name → human-readable display string.
 *
 * Two flavors appear in the prod DB:
 * - lowercase substring style (carentan_warfare, kursk_offensive_ger)
 * - code prefix style (CAR_S_1944_Day_P_Skirmish, STA_L_1942_Warfare, etc.)
 *
 * formatMapName extracts location + game mode + flavor (Night, Day, Rain).
 * Unknown maps fall back to the raw string so we never hide data.
 */

// Code → location (display name).
const CODE_TO_LOCATION: Record<string, string> = {
  CAR: 'Carentan',
  HIL: 'Hill 400',
  PHL: 'Purple Heart Lane',
  REM: 'Remagen',
  SMDM: 'Sainte-Marie-du-Mont',
  STA: 'Stalingrad',
}

// lowercase substring → location.
const SUBSTRING_TO_LOCATION: Array<[string, string]> = [
  ['carentan',        'Carentan'],
  ['driel',           'Driel'],
  ['elsenbornridge',  'Elsenborn Ridge'],
  ['foy',             'Foy'],
  ['hill400',         'Hill 400'],
  ['hurtgenforest',   'Hürtgen Forest'],
  ['mortain',         'Mortain'],
  ['omahabeach',      'Omaha Beach'],
  ['stmariedumont',   'Sainte-Marie-du-Mont'],
  ['stmereeglise',    'Sainte-Mère-Église'],
  ['utahbeach',       'Utah Beach'],
  ['remagen',         'Remagen'],
  ['kharkov',         'Kharkov'],
  ['kursk',           'Kursk'],
  ['smolensk',        'Smolensk'],
  ['stalingrad',      'Stalingrad'],
  ['elalamein',       'El Alamein'],
  ['tobruk',          'Tobruk'],
]

function locationOf(raw: string): string | null {
  const lower = raw.toLowerCase()
  // Try code prefix first (CAR_S_1944_...) — split on underscore, look up.
  const head = raw.split('_')[0]
  if (head && CODE_TO_LOCATION[head]) return CODE_TO_LOCATION[head]
  // Otherwise scan for substring.
  for (const [pat, loc] of SUBSTRING_TO_LOCATION) {
    if (lower.includes(pat)) return loc
  }
  return null
}

function modeOf(raw: string): string {
  const lower = raw.toLowerCase()
  if (lower.includes('offensive')) {
    // suffix _us / _ger / _british / _cw / _rus tells us attacker side
    if (lower.includes('_us'))       return 'Offensive (US)'
    if (lower.includes('_ger'))      return 'Offensive (GER)'
    if (lower.includes('_british'))  return 'Offensive (GB)'
    if (lower.includes('_cw'))       return 'Offensive (CW)'
    if (lower.includes('_rus'))      return 'Offensive (RUS)'
    return 'Offensive'
  }
  if (lower.includes('skirmish')) return 'Skirmish'
  if (lower.includes('warfare'))  return 'Warfare'
  return ''
}

function flavorOf(raw: string): string {
  const lower = raw.toLowerCase()
  const tags: string[] = []
  if (lower.includes('night'))    tags.push('Ніч')
  if (lower.includes('dusk'))     tags.push('Сутінки')
  if (lower.includes('dawn'))     tags.push('Світанок')
  if (lower.includes('morning'))  tags.push('Ранок')
  if (lower.includes('day') && !lower.includes('dawn'))       tags.push('День')
  if (lower.includes('rain'))     tags.push('Дощ')
  if (lower.includes('overcast')) tags.push('Хмарно')
  return tags.length ? ` · ${tags.join(', ')}` : ''
}

/** Convert a raw HLL map_name to a human-readable string.
 *  e.g. "REM_L_1945_Warfare_Night" → "Remagen · Warfare · Ніч"
 *       "carentan_warfare"        → "Carentan · Warfare"
 *       "weird_unknown_string"    → "weird_unknown_string" (unchanged) */
export function formatMapName(raw: string): string {
  if (!raw) return ''
  const loc = locationOf(raw)
  if (!loc) return raw  // fall back, don't hide data
  const mode = modeOf(raw)
  const flavor = flavorOf(raw)
  return mode ? `${loc} · ${mode}${flavor}` : `${loc}${flavor}`
}
