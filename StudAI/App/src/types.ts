export type HousingCategory = "crous" | "private";

export type Housing = {
  id: string;
  name: string;
  provider?: string;
  category?: HousingCategory;   // crous = state-subsidized, private = paid market
  lat: number;
  lng: number;
  rent?: number;                // monthly rent in euros (null for CROUS)
  surface?: number;             // surface in m²
  type?: string;                // "Résidence étudiante", etc.
  distance?: string;            // distance from center
  url?: string;
  imageUrl?: string;
  lastUpdated?: string;
};

export type TransitMode = "metro" | "rer" | "tram";

export type TransitRoute = {
  id: string;
  shortName: string;            // "1", "A", "T3a"
  longName?: string;            // commercial name
  mode: TransitMode;
  color: string;                // "#FFCD00"
  shapes: [number, number][][]; // multiple polylines per route ([lat,lng])
};

export type Station = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  lines: { routeId: string; mode: TransitMode; indice: string }[];
};

export type TileStyle = "color" | "mono-light" | "mono-dark";

