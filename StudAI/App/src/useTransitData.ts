import type { TransitRoute } from "./types";
import data from "./data/transit.json";

const routes = (data as TransitRoute[]).filter(
  (r) => typeof r?.id === "string" && Array.isArray(r?.shapes) && r.shapes.length > 0
);

export function useTransitData(): TransitRoute[] {
  return routes;
}
