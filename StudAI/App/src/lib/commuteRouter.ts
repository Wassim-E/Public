import type { CommuteResult } from "../types";

export type { CommuteResult };

// OSRM public instance — driving profile, no API key needed.
// Transit correction: Paris transit is ~85% of driving time (dense metro network).
const OSRM_BASE = "https://router.project-osrm.org/route/v1/driving";
const CACHE_KEY = "studai_commutes_v2";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

type CacheEntry = { minutes: number; modes: string[]; cachedAt: number };
type CacheStore = Record<string, CacheEntry>;

function entryKey(housingId: string, workPin: [number, number]): string {
  return `${housingId}@${workPin[0].toFixed(4)},${workPin[1].toFixed(4)}`;
}

function readStore(): CacheStore {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function writeStore(store: CacheStore): void {
  localStorage.setItem(CACHE_KEY, JSON.stringify(store));
}

export function getCachedCommute(
  housingId: string,
  workPin: [number, number]
): CommuteResult | null {
  const entry = readStore()[entryKey(housingId, workPin)];
  if (!entry || Date.now() - entry.cachedAt > CACHE_TTL_MS) return null;
  return { minutes: entry.minutes, modes: entry.modes };
}

export function setCachedCommute(
  housingId: string,
  workPin: [number, number],
  result: CommuteResult
): void {
  const store = readStore();
  store[entryKey(housingId, workPin)] = { ...result, cachedAt: Date.now() };
  const entries = Object.entries(store);
  if (entries.length > 2000) {
    entries.sort(([, a], [, b]) => a.cachedAt - b.cachedAt);
    for (const [k] of entries.slice(0, entries.length - 1600)) delete store[k];
  }
  writeStore(store);
}

export function countCached(workPin: [number, number], housingIds: string[]): number {
  const store = readStore();
  const now = Date.now();
  return housingIds.filter((id) => {
    const e = store[entryKey(id, workPin)];
    return e && now - e.cachedAt <= CACHE_TTL_MS;
  }).length;
}

export async function fetchOsrmCommute(
  housing: [number, number],
  work: [number, number]
): Promise<CommuteResult> {
  // OSRM expects lon,lat order
  const url = `${OSRM_BASE}/${housing[1]},${housing[0]};${work[1]},${work[0]}?overview=false`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`OSRM ${res.status}`);
  const data = await res.json();
  if (data.code !== "Ok" || !data.routes?.[0]) throw new Error("no_route");
  const drivingMinutes = data.routes[0].duration / 60;
  const minutes = Math.max(1, Math.round(drivingMinutes * 0.85));
  return { minutes, modes: ["transit est."] };
}
