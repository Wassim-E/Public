import "leaflet/dist/leaflet.css";
import "./HousingMap.css";
import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { Housing, TransitRoute } from "../types";
import type { FilterState } from "../lib/filters";
import { IsochroneLayer } from "./IsochroneLayer";
import { TransitLayer } from "./TransitLayer";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

type Props = {
  housing: Housing[];
  filters: FilterState;
  transitRoutes: TransitRoute[];
  onWorkPinChange: (pin: [number, number] | null) => void;
};

export function HousingMap({ housing, filters, transitRoutes, onWorkPinChange }: Props) {
  const workPin = filters.workPin;

  const housingMarkers = useMemo(() => {
    return housing
      .filter((h) => Number.isFinite(h.lat) && Number.isFinite(h.lng))
      .map((h) => (
        <CircleMarker
          key={h.id}
          center={[h.lat, h.lng]}
          radius={6}
          pathOptions={{
            color: "#0b1020",
            weight: 1,
            fillColor: "#7aa2ff",
            fillOpacity: 0.85,
          }}
        >
          <Popup>
            <div className="popupTitle">{h.name}</div>
            <div className="popupMeta">
              <div>Type: {h.type ?? "—"}</div>
              <div>Provider: {h.provider ?? "—"}</div>
              <div>Rent: {h.rent ? `${h.rent}€/month` : "—"}</div>
              <div>Surface: {h.surface ? `${h.surface}m²` : "—"}</div>
              <div>Distance: {h.distance ?? "—"}</div>
              <div>Updated: {h.lastUpdated ?? "—"}</div>
            </div>
            {h.url ? (
              <a className="popupLink" href={h.url} target="_blank" rel="noreferrer">
                View on Studyrama
              </a>
            ) : null}
          </Popup>
        </CircleMarker>
      ));
  }, [housing]);

  const bounds = useMemo(() => {
    const pts = housing
      .map((h) => (Number.isFinite(h.lat) && Number.isFinite(h.lng) ? ([h.lat, h.lng] as const) : null))
      .filter(Boolean) as Array<[number, number]>;
    if (pts.length === 0) return null;
    const latLngs = pts.map((p) => L.latLng(p[0], p[1]));
    return L.latLngBounds(latLngs);
  }, [housing]);

  return (
    <MapContainer className="map" center={PARIS_CENTER} zoom={12} scrollWheelZoom preferCanvas>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        updateWhenZooming={false}
        updateWhenIdle
        keepBuffer={6}
      />

      <MapClickHandler onClick={(lat, lng) => onWorkPinChange([lat, lng])} />

      <TransitLayer routes={transitRoutes} />

      <IsochroneLayer
        workPin={workPin}
        minutes={filters.maxCommuteMinutes}
        avgSpeedKmh={filters.avgTransitSpeedKmh}
      />

      {workPin ? (
        <CircleMarker center={workPin} radius={10} pathOptions={{ color: "#7aa2ff", weight: 3 }}>
          <Popup>
            <div className="popupTitle">Workplace</div>
            <div className="popupMeta">
              <div>
                {workPin[0].toFixed(5)}, {workPin[1].toFixed(5)}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ) : null}

      {housingMarkers}

      <AutoFit bounds={bounds} />
    </MapContainer>
  );
}

function MapClickHandler({ onClick }: { onClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function AutoFit({ bounds }: { bounds: L.LatLngBounds | null }) {
  const map = useMap();
  const hasFitRef = useRef(false);
  useEffect(() => {
    if (!bounds || hasFitRef.current) return;
    map.fitBounds(bounds.pad(0.2));
    hasFitRef.current = true;
  }, [bounds, map]);
  return null;
}

function fmt(n: number | undefined) {
  if (n == null) return "—";
  return (Math.round(n * 10) / 10).toFixed(1);
}

function fmtSigned(n: number) {
  const fixed = (Math.round(n * 10) / 10).toFixed(1);
  return n >= 0 ? `+${fixed}` : fixed;
}
