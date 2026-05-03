import { Circle } from "react-leaflet";
import { commuteRadiusKm } from "../lib/isochrone";

type Props = {
  workPin: [number, number] | null;
  minutes: number | null;
  avgSpeedKmh: number;
};

export function IsochroneLayer({ workPin, minutes, avgSpeedKmh }: Props) {
  if (!workPin || minutes == null) return null;
  const radiusKm = commuteRadiusKm(minutes, avgSpeedKmh);
  return (
    <Circle
      center={workPin}
      radius={radiusKm * 1000}
      pathOptions={{
        color: "#7aa2ff",
        weight: 1,
        fillColor: "#7aa2ff",
        fillOpacity: 0.08,
      }}
    />
  );
}
