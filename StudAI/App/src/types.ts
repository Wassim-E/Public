export type HousingCategory = "crous" | "private";

export type RoomType = {
  type?: string;
  rent?: number;
  surface?: number;
  furnished?: boolean;
  available?: boolean;
  floor?: number;
  deposit?: number;
  applicationFee?: number;
  energyClass?: string;
  ghgClass?: string;
};

export type PriceSource = {
  source: string;           // "studyrama" | "nexity" | "action_logement"
  sourceLabel: string;      // "Studyrama" | "Nexity Studéa" | "Action Logement"
  url?: string;
  rent?: number;
  rentMax?: number;
  surface?: number;
  surfaceMax?: number;
  rooms?: RoomType[];
};

export type ReviewEntry = {
  author: string;
  rating: number | null;
  date: string;
  text: string;
};

export type Housing = {
  id: string;
  name: string;
  provider?: string;
  category?: HousingCategory;
  lat: number;
  lng: number;

  // Aggregated across all price sources (for filtering)
  rent?: number;
  rentMax?: number;
  surface?: number;
  surfaceMax?: number;

  type?: string;
  distance?: string;
  imageUrl?: string;
  images?: string[];
  description?: string;
  amenities?: string[];
  phone?: string;
  address?: string;

  // Multi-source data
  prices?: PriceSource[];
  sources?: string[];

  // Google Reviews
  googleRating?: number;
  googleRatingCount?: number;
  googleReviews?: ReviewEntry[];
  googleMapsUrl?: string;

  lastUpdated?: string;
};

export type TransitMode = "metro" | "rer" | "tram";

export type TransitRoute = {
  id: string;
  shortName: string;
  longName?: string;
  mode: TransitMode;
  color: string;
  shapes: [number, number][][];
};

export type Station = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  lines: { routeId: string; mode: TransitMode; indice: string }[];
};

export type TileStyle = "color" | "mono-light" | "mono-dark";

export type CommuteResult = {
  minutes: number;
  modes: string[];
};

export type CommuteMap = Record<string, CommuteResult>;
