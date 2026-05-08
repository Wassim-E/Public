import "leaflet/dist/leaflet.css";
import "./HousingMap.css";
import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { Housing, Station, TileStyle, TransitRoute } from "../types";
import type { FilterState } from "../lib/filters";
import { IsochroneLayer } from "./IsochroneLayer";
import { TransitLayer } from "./TransitLayer";
import { StationLayer } from "./StationLayer";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

const TILE_CONFIG: Record<
  TileStyle,
  { url: string; attribution: string; subdomains?: string }
> = {
  color: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  "mono-light": {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
  },
  "mono-dark": {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
  },
};

const WORKPLACE_ICON = L.divIcon({
  html: `<svg width="30" height="36" viewBox="0 0 30 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M15 35C15 35 4 21 4 13a11 11 0 0 1 22 0c0 8-11 22-11 22z" fill="#7aa2ff" stroke="#0b1020" stroke-width="1.5"/>
    <polygon points="15,4 22,8 8,8" fill="rgba(255,255,255,0.85)"/>
    <rect x="8.5" y="8" width="13" height="10" rx="0.5" fill="white"/>
    <rect x="10" y="10" width="2" height="2" fill="#7aa2ff"/>
    <rect x="14" y="10" width="2" height="2" fill="#7aa2ff"/>
    <rect x="18" y="10" width="2" height="2" fill="#7aa2ff"/>
    <rect x="10" y="13.5" width="2" height="2" fill="#7aa2ff"/>
    <rect x="18" y="13.5" width="2" height="2" fill="#7aa2ff"/>
    <rect x="13.5" y="13" width="3" height="5" fill="#7aa2ff"/>
  </svg>`,
  className: "",
  iconSize: [30, 36],
  iconAnchor: [15, 35],
  popupAnchor: [0, -35],
});

type Props = {
  housing: Housing[];
  filters: FilterState;
  transitRoutes: TransitRoute[];
  stations: Station[];
  isPlacingWorkPin: boolean;
  onWorkPinChange: (pin: [number, number] | null, label?: string) => void;
};

export function HousingMap({
  housing,
  filters,
  transitRoutes,
  stations,
  isPlacingWorkPin,
  onWorkPinChange,
}: Props) {
  const workPin = filters.workPin;
  const tile = TILE_CONFIG[filters.tileStyle];

  const housingMarkers = useMemo(() => {
    return housing
      .filter((h) => Number.isFinite(h.lat) && Number.isFinite(h.lng))
      .map((h) => {
        const isCrous = h.category === "crous";
        return (
          <CircleMarker
            key={h.id}
            center={[h.lat, h.lng]}
            radius={6}
            pathOptions={{
              color: "#0b1020",
              weight: 1,
              fillColor: isCrous ? "#ffb86b" : "#7aa2ff",
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <div className="popupTitle">{h.name}</div>
              <div className="popupMeta">
                <div>Type: {h.type ?? "—"}</div>
                <div>Provider: {h.provider ?? "—"}</div>
                <div>
                  Rent:{" "}
                  {h.rent
                    ? `${h.rent}€/month`
                    : isCrous
                    ? "see CROUS (varies with aid)"
                    : "—"}
                </div>
                <div>Surface: {h.surface ? `${h.surface}m²` : "—"}</div>
                <div>Distance: {h.distance ?? "—"}</div>
                <div>Updated: {h.lastUpdated ?? "—"}</div>
              </div>
              {h.url ? (
                <a className="popupLink" href={h.url} target="_blank" rel="noreferrer">
                  View listing
                </a>
              ) : null}
            </Popup>
          </CircleMarker>
        );
      });
  }, [housing]);

  const bounds = useMemo(() => {
    const pts = housing
      .map((h) =>
        Number.isFinite(h.lat) && Number.isFinite(h.lng)
          ? ([h.lat, h.lng] as const)
          : null
      )
      .filter(Boolean) as Array<[number, number]>;
    if (pts.length === 0) return null;
    const latLngs = pts.map((p) => L.latLng(p[0], p[1]));
    return L.latLngBounds(latLngs);
  }, [housing]);

  return (
    <MapContainer
      className={`map${isPlacingWorkPin ? " is-placing" : ""}`}
      center={PARIS_CENTER}
      zoom={12}
      scrollWheelZoom
      preferCanvas
    >
      <TileLayer
        key={filters.tileStyle}
        attribution={tile.attribution}
        url={tile.url}
        subdomains={tile.subdomains ?? "abc"}
        updateWhenZooming={false}
        updateWhenIdle
        keepBuffer={6}
      />

      <MapClickHandler
        isPlacing={isPlacingWorkPin}
        onClick={(lat, lng) => onWorkPinChange([lat, lng])}
      />

      <TransitLayer routes={transitRoutes} />

      {filters.showStations && (
        <StationLayer stations={stations} visibleRouteIds={filters.transitShownRouteIds} />
      )}

      <IsochroneLayer
        workPin={workPin}
        minutes={filters.maxCommuteMinutes}
        avgSpeedKmh={filters.avgTransitSpeedKmh}
      />

      {workPin ? (
        <Marker position={workPin} icon={WORKPLACE_ICON}>
          <Popup>
            <div className="popupTitle">Workplace</div>
            <div className="popupMeta">
              <div>
                {workPin[0].toFixed(5)}, {workPin[1].toFixed(5)}
              </div>
            </div>
          </Popup>
        </Marker>
      ) : null}

      {housingMarkers}

      <AutoFit bounds={bounds} />
    </MapContainer>
  );
}

function MapClickHandler({
  isPlacing,
  onClick,
}: {
  isPlacing: boolean;
  onClick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click(e) {
      if (isPlacing) onClick(e.latlng.lat, e.latlng.lng);
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
