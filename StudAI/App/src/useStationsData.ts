import type { Station } from "./types";
import data from "./data/stations.json";

const stations = (data as Station[]).filter(
  (s) =>
    typeof s?.id === "string" &&
    Number.isFinite(s.lat) &&
    Number.isFinite(s.lng) &&
    Array.isArray(s.lines) &&
    s.lines.length > 0
);

export function useStationsData(): Station[] {
  return stations;
}
