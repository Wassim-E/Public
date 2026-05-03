import { Polyline } from "react-leaflet";
import type { TransitRoute } from "../types";

const WEIGHT_BY_MODE: Record<string, number> = {
  rer: 4,
  metro: 3,
  tram: 2,
};

export function TransitLayer({ routes }: { routes: TransitRoute[] }) {
  return (
    <>
      {routes.flatMap((r) =>
        r.shapes.map((shape, i) => (
          <Polyline
            key={`${r.id}-${i}`}
            positions={shape}
            pathOptions={{
              color: r.color,
              weight: WEIGHT_BY_MODE[r.mode] ?? 3,
              opacity: 0.8,
            }}
          />
        ))
      )}
    </>
  );
}
