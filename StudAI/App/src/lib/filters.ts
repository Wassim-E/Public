import type { Housing, HousingCategory, TileStyle, TransitRoute } from "../types";
import { commuteRadiusKm, haversineKm } from "./isochrone";

export type FilterState = {
  // housing filters
  maxRent: number | null;
  categories: HousingCategory[];

  // workplace + commute
  workPin: [number, number] | null;
  maxCommuteMinutes: number | null;
  avgTransitSpeedKmh: number;

  // transit overlay (additive: only routes in this list are drawn)
  transitShownRouteIds: string[];
  showStations: boolean;

  // map style
  tileStyle: TileStyle;
};

export const initialFilterState: FilterState = {
  maxRent: null,
  categories: ["crous", "private"],
  workPin: null,
  maxCommuteMinutes: null,
  avgTransitSpeedKmh: 25,
  transitShownRouteIds: [],
  showStations: true,
  tileStyle: "mono-light",
};

export function applyFilters(housing: Housing[], state: FilterState): Housing[] {
  return housing.filter((h) => {
    if (h.category && !state.categories.includes(h.category)) return false;
    if (state.maxRent != null && h.rent != null && h.rent > state.maxRent) return false;
    if (state.workPin && state.maxCommuteMinutes != null) {
      const radius = commuteRadiusKm(state.maxCommuteMinutes, state.avgTransitSpeedKmh);
      const d = haversineKm(state.workPin, [h.lat, h.lng]);
      if (d > radius) return false;
    }
    return true;
  });
}

export function visibleRoutes(routes: TransitRoute[], state: FilterState): TransitRoute[] {
  const shown = new Set(state.transitShownRouteIds);
  return routes.filter((r) => shown.has(r.id));
}

export function toggleArrayItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}
