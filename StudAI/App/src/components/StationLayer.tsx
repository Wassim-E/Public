import { CircleMarker, Tooltip } from "react-leaflet";
import { useMemo } from "react";
import type { Station } from "../types";

type Props = {
  stations: Station[];
  visibleRouteIds: string[];
};

export function StationLayer({ stations, visibleRouteIds }: Props) {
  const visible = useMemo(() => {
    if (visibleRouteIds.length === 0) return [];
    const set = new Set(visibleRouteIds);
    return stations.filter((s) => s.lines.some((l) => set.has(l.routeId)));
  }, [stations, visibleRouteIds]);

  return (
    <>
      {visible.map((s) => (
        <CircleMarker
          key={s.id}
          center={[s.lat, s.lng]}
          radius={3}
          pathOptions={{
            color: "#ffffff",
            weight: 1,
            fillColor: "#0b1020",
            fillOpacity: 1,
          }}
        >
          <Tooltip direction="top" offset={[0, -2]}>
            {s.name}
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  );
}
