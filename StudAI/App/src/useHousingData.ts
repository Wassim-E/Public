import type { Housing } from "./types";
import housingData from "./data/housing.json";

type State = {
  housing: Housing[];
  loading: boolean;
  error: string | null;
};

const sanitizedHousing = sanitize(housingData as Housing[]);

export function useHousingData(): State {
  return { housing: sanitizedHousing, loading: false, error: null };
}

function sanitize(items: Housing[]) {
  return items
    .filter((h) => typeof h?.id === "string" && typeof h?.name === "string")
    .map((h) => ({ ...h }));
}

