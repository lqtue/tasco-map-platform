// Fetch an official road length from Wikidata (property P2043 "length").
// CORS-safe from the browser via `origin=*`. Returns kilometres, or null when
// the entity has no length claim / the qid is missing / the request fails.

const WD_API = 'https://www.wikidata.org/w/api.php';

// Wikidata unit items we expect for a length: km and metre.
const UNIT_TO_KM: Record<string, number> = {
  Q828224: 1, // kilometre
  Q11573: 0.001, // metre
  Q253276: 1.609344, // mile
};

export async function fetchOfficialLengthKm(qid: string | undefined | null): Promise<number | null> {
  if (!qid || !/^Q\d+$/.test(qid)) return null;
  try {
    const url = `${WD_API}?action=wbgetentities&ids=${qid}&props=claims&format=json&origin=*`;
    const res = await fetch(url);
    const data = await res.json();
    const claims = data?.entities?.[qid]?.claims?.P2043;
    if (!claims || !claims.length) return null;
    const value = claims[0]?.mainsnak?.datavalue?.value;
    if (!value) return null;
    const amount = parseFloat(value.amount); // e.g. "+73.6"
    if (Number.isNaN(amount)) return null;
    const unitQid = String(value.unit || '').split('/').pop() || '';
    const factor = UNIT_TO_KM[unitQid] ?? 1; // unitless → assume km
    return amount * factor;
  } catch {
    return null;
  }
}
