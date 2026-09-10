// Venue → real map links for the six AWS re:Invent 2026 venues on the Las Vegas
// Strip. We link out to Google Maps (no API key, no SDK) so the map is genuinely
// useful: "open venue" drops a pin at the real place, and "directions" opens
// turn-by-turn between two venues. Names/aliases mirror the backend
// (reinvent_data.py) so live session venues resolve correctly.

export interface VenueInfo {
  name: string;
  /** Google Maps place query — the official property name + city. */
  mapQuery: string;
  /** Approx. Strip position, north (higher) to south, for a simple visual. */
  lat: number;
  lng: number;
}

const VENUES: Record<string, VenueInfo> = {
  'The Venetian': { name: 'The Venetian', mapQuery: 'The Venetian Resort Las Vegas', lat: 36.1213, lng: -115.1697 },
  'Wynn': { name: 'Wynn', mapQuery: 'Wynn Las Vegas', lat: 36.1264, lng: -115.1657 },
  'Encore': { name: 'Encore', mapQuery: 'Encore at Wynn Las Vegas', lat: 36.1293, lng: -115.1647 },
  'Caesars Forum': { name: 'Caesars Forum', mapQuery: 'Caesars Forum Las Vegas', lat: 36.1189, lng: -115.1699 },
  'Caesars Palace': { name: 'Caesars Palace', mapQuery: 'Caesars Palace Las Vegas', lat: 36.1162, lng: -115.1745 },
  'MGM Grand': { name: 'MGM Grand', mapQuery: 'MGM Grand Las Vegas', lat: 36.1023, lng: -115.1697 },
};

const ALIASES: Record<string, string> = {
  venetian: 'The Venetian',
  'the venetian': 'The Venetian',
  palazzo: 'The Venetian',
  wynn: 'Wynn',
  encore: 'Encore',
  'mgm grand': 'MGM Grand',
  mgm: 'MGM Grand',
  'caesars forum': 'Caesars Forum',
  'caesars palace': 'Caesars Palace',
  caesars: 'Caesars Forum',
};

/** Resolve a free-text venue name to a known venue (or undefined). */
export function resolveVenue(name?: string): VenueInfo | undefined {
  if (!name) return undefined;
  const key = name.trim();
  if (VENUES[key]) return VENUES[key];
  const alias = ALIASES[key.toLowerCase()];
  if (alias && VENUES[alias]) return VENUES[alias];
  // Loose contains-match as a last resort (e.g. "Venetian Level 3").
  const lower = key.toLowerCase();
  for (const [aliasKey, canonical] of Object.entries(ALIASES)) {
    if (lower.includes(aliasKey)) return VENUES[canonical];
  }
  return undefined;
}

/** Google Maps link that drops a pin on the venue (or the search text). */
export function venueMapLink(name?: string): string {
  const v = resolveVenue(name);
  const q = v ? v.mapQuery : `${name ?? 'AWS re:Invent'} Las Vegas`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
}

/** Google Maps walking-directions link between two venues. */
export function directionsLink(from?: string, to?: string): string {
  const f = resolveVenue(from);
  const t = resolveVenue(to);
  const origin = f ? f.mapQuery : (from ?? '');
  const dest = t ? t.mapQuery : (to ?? 'AWS re:Invent Las Vegas');
  const params = new URLSearchParams({
    api: '1',
    destination: dest,
    travelmode: 'walking',
  });
  if (origin) params.set('origin', origin);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export { VENUES };
