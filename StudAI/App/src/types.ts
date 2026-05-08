export type HousingCategory = "crous" | "private";

export type RoomType = {
  type?: string;                // "Studio", "Type 1", etc.
  rent?: number;                // monthly rent incl. charges
  surface?: number;             // m²
  available?: boolean;
  floor?: number;
  deposit?: number;             // security deposit in €
  applicationFee?: number;      // dossier fee in €
  energyClass?: string;         // "A"–"G"
  ghgClass?: string;            // greenhouse gas class
};

export type Housing = {
  id: string;
  name: string;
  provider?: string;
  category?: HousingCategory;   // crous = state-subsidized, private = paid market
  lat: number;
  lng: number;
  rent?: number;                // lowest monthly rent in euros
  rentMax?: number;             // highest monthly rent (multi-room residences)
  surface?: number;             // smallest room surface in m²
  surfaceMax?: number;          // largest room surface in m²
  type?: string;                // "Résidence étudiante", etc.
  distance?: string;            // formatted distance from Paris centre
  url?: string;
  imageUrl?: string;            // primary image
  images?: string[];            // full photo gallery
  description?: string;         // free-text description of the residence
  amenities?: string[];         // list of services/equipment offered
  phone?: string;               // contact phone number
  address?: string;             // full street address
  rooms?: RoomType[];           // per-room-type details
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

