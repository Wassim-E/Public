export type Housing = {
  id: string;
  name: string;
  provider?: string;
  lat: number;
  lng: number;
  rent?: number;        // monthly rent in euros
  surface?: number;     // surface in m²
  type?: string;        // "Résidence étudiante", etc.
  distance?: string;    // distance from center
  url?: string;
  imageUrl?: string;
  lastUpdated?: string;
};

