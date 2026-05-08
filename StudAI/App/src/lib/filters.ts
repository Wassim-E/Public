import type { Housing, HousingCategory, TileStyle, TransitRoute, Station } from "../types";
import { haversineKm } from "./isochrone";

const WALK_SPEED_KMH = 5;

export type FilterState = {
  // housing filters
  maxRent: number | null;
  categories: HousingCategory[];
  minSurface: number | null;
  maxSurface: number | null;

  // workplace + commute
  workPin: [number, number] | null;
  workLabel: string | null;
  maxCommuteMinutes: number | null;
  avgTransitSpeedKmh: number;

  // transit overlay (additive: only routes in this list are drawn)
  transitShownRouteIds: string[];
  showStations: boolean;

  // amenities filter (all required amenities must be present)
  requiredAmenities: string[];

  // map style
  tileStyle: TileStyle;
};

export const initialFilterState: FilterState = {
  maxRent: null,
  categories: ["crous", "private"],
  minSurface: null,
  maxSurface: null,
  workPin: null,
  workLabel: null,
  maxCommuteMinutes: null,
  avgTransitSpeedKmh: 25,
  transitShownRouteIds: [],
  showStations: true,
  requiredAmenities: [],
  tileStyle: "mono-light",
};

export function applyFilters(
  housing: Housing[],
  state: FilterState,
  stations: Station[] = []
): Housing[] {
  // Precompute nearest station to workplace once per filter call
  let nearestWorkStation: Station | null = null;
  let nearestWorkDist = Infinity;
  if (state.workPin && state.maxCommuteMinutes != null && stations.length > 0) {
    for (const s of stations) {
      const d = haversineKm(state.workPin, [s.lat, s.lng]);
      if (d < nearestWorkDist) {
        nearestWorkDist = d;
        nearestWorkStation = s;
      }
    }
  }

  return housing.filter((h) => {
    if (h.category && !state.categories.includes(h.category)) return false;
    if (state.maxRent != null && h.rent != null && h.rent > state.maxRent) return false;
    if (state.minSurface != null && h.surface != null && h.surface < state.minSurface) return false;
    if (state.maxSurface != null && h.surface != null && h.surface > state.maxSurface) return false;
    if (state.requiredAmenities.length > 0) {
      const has = new Set(h.amenities ?? []);
      if (!state.requiredAmenities.every((a) => has.has(a))) return false;
    }
    if (state.workPin && state.maxCommuteMinutes != null) {
      const minutes = estimateCommuteMinutes(
        [h.lat, h.lng],
        state.workPin,
        stations,
        nearestWorkStation,
        nearestWorkDist,
        state.avgTransitSpeedKmh
      );
      if (minutes > state.maxCommuteMinutes) return false;
    }
    return true;
  });
}

// Estimate commute time via: walk to nearest station → transit → walk from nearest work station
function estimateCommuteMinutes(
  from: [number, number],
  to: [number, number],
  stations: Station[],
  nearestToWork: Station | null,
  nearestToWorkDist: number,
  avgTransitSpeedKmh: number
): number {
  if (!nearestToWork || stations.length === 0) {
    return (haversineKm(from, to) / avgTransitSpeedKmh) * 60;
  }

  let nearestFromStation = stations[0];
  let minFromDist = haversineKm(from, [stations[0].lat, stations[0].lng]);
  for (const s of stations) {
    const d = haversineKm(from, [s.lat, s.lng]);
    if (d < minFromDist) {
      minFromDist = d;
      nearestFromStation = s;
    }
  }

  const walkToStation = (minFromDist / WALK_SPEED_KMH) * 60;
  const transit =
    (haversineKm(
      [nearestFromStation.lat, nearestFromStation.lng],
      [nearestToWork.lat, nearestToWork.lng]
    ) /
      avgTransitSpeedKmh) *
    60;
  const walkFromStation = (nearestToWorkDist / WALK_SPEED_KMH) * 60;

  return walkToStation + transit + walkFromStation;
}

export function visibleRoutes(routes: TransitRoute[], state: FilterState): TransitRoute[] {
  const shown = new Set(state.transitShownRouteIds);
  return routes.filter((r) => shown.has(r.id));
}

export function toggleArrayItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}
