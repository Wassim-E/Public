import type { Housing, TransitMode, TransitRoute } from "../types";
import { commuteRadiusKm, haversineKm } from "./isochrone";

export type FilterState = {
  maxRent: number | null;
  workPin: [number, number] | null;
  maxCommuteMinutes: number | null;
  avgTransitSpeedKmh: number;
  transitVisibleModes: TransitMode[];
  transitHiddenRouteIds: string[];
};

export const initialFilterState: FilterState = {
  maxRent: null,
  workPin: null,
  maxCommuteMinutes: null,
  avgTransitSpeedKmh: 25,
  transitVisibleModes: ["metro", "rer", "tram"],
  transitHiddenRouteIds: [],
};

export function applyFilters(housing: Housing[], state: FilterState): Housing[] {
  return housing.filter((h) => {
    if (state.maxRent != null && h.rent != null && h.rent > state.maxRent) {
      return false;
    }
    if (state.workPin && state.maxCommuteMinutes != null) {
      const radius = commuteRadiusKm(state.maxCommuteMinutes, state.avgTransitSpeedKmh);
      const d = haversineKm(state.workPin, [h.lat, h.lng]);
      if (d > radius) return false;
    }
    return true;
  });
}

export function visibleRoutes(routes: TransitRoute[], state: FilterState): TransitRoute[] {
  const hidden = new Set(state.transitHiddenRouteIds);
  const modes = new Set(state.transitVisibleModes);
  return routes.filter((r) => modes.has(r.mode) && !hidden.has(r.id));
}

export function toggleArrayItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}
