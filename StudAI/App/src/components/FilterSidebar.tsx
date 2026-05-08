import "./FilterSidebar.css";
import { useState, useCallback, useRef } from "react";
import type { HousingCategory, TileStyle, TransitMode, TransitRoute, Station } from "../types";
import { toggleArrayItem, type FilterState } from "../lib/filters";
import { haversineKm } from "../lib/isochrone";

const WALK_SPEED_KMH = 5;

function nearbyRouteIds(
  workPin: [number, number],
  stations: Station[],
  maxWalkMinutes: number
): string[] {
  const maxDistKm = (maxWalkMinutes / 60) * WALK_SPEED_KMH;
  const ids = new Set<string>();
  for (const s of stations) {
    if (haversineKm(workPin, [s.lat, s.lng]) <= maxDistKm) {
      for (const line of s.lines) ids.add(line.routeId);
    }
  }
  return Array.from(ids);
}

type Props = {
  state: FilterState;
  onChange: (patch: Partial<FilterState>) => void;
  matchCount: number;
  totalCount: number;
  allRoutes: TransitRoute[];
  stations: Station[];
  isPlacingWorkPin: boolean;
  onStartPlacingWorkPin: () => void;
  onCancelPlacingWorkPin: () => void;
};

const TILE_OPTIONS: { value: TileStyle; label: string }[] = [
  { value: "mono-light", label: "Light" },
  { value: "mono-dark", label: "Dark" },
  { value: "color", label: "Color" },
];

const CATEGORY_LABELS: Record<HousingCategory, string> = {
  private: "Private",
  crous: "CROUS",
};

const MODE_LABELS: Record<TransitMode, string> = {
  metro: "Metro",
  rer: "RER",
  tram: "Tram",
};

const CANONICAL_AMENITIES = [
  "WiFi",
  "Parking",
  "Laverie",
  "Ascenseur",
  "Salle de sport",
  "Local vélos",
  "Vidéosurveillance",
  "Service ménage",
  "Espace commun",
  "Salle informatique",
  "Accueil",
  "Interphone",
  "Piscine",
  "Jardin / Terrasse",
  "Meublé",
  "Kit vaisselle",
  "Prêt matériel",
  "Distributeur",
  "Local poubelles",
];

type SectionId = "map" | "workplace" | "filters" | "surface" | "transit" | "amenities";

type SearchResult = { lat: number; lng: number; label: string };

async function geocodeSearch(query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    limit: "5",
    countrycodes: "fr",
  });
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?${params}`,
      { headers: { "Accept-Language": "fr,en" } }
    );
    const data = await res.json();
    return data.map((item: { lat: string; lon: string; display_name: string }) => ({
      lat: parseFloat(item.lat),
      lng: parseFloat(item.lon),
      label: item.display_name,
    }));
  } catch {
    return [];
  }
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

export function FilterSidebar({
  state,
  onChange,
  matchCount,
  totalCount,
  allRoutes,
  stations,
  isPlacingWorkPin,
  onStartPlacingWorkPin,
  onCancelPlacingWorkPin,
}: Props) {
  const routesByMode = groupRoutesByMode(allRoutes);

  const [open, setOpen] = useState<Record<SectionId, boolean>>({
    map: false,
    workplace: true,
    filters: true,
    surface: false,
    transit: false,
    amenities: false,
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();

  const handleSearchChange = useCallback((q: string) => {
    setSearchQuery(q);
    clearTimeout(searchTimer.current);
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      setIsSearching(true);
      const results = await geocodeSearch(q);
      setSearchResults(results);
      setIsSearching(false);
    }, 350);
  }, []);

  function toggle(id: SectionId) {
    setOpen((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  const surfaceBadge =
    state.minSurface != null || state.maxSurface != null
      ? `${state.minSurface ?? 0}–${state.maxSurface ?? "∞"} m²`
      : undefined;

  return (
    <aside className="panel">
      <div className="panel__header">
        <span className="panel__title">StudAI</span>
        <span className="panel__count">
          {matchCount} / {totalCount}
        </span>
      </div>

      {/* Map style */}
      <Section
        title="Map"
        badge={TILE_OPTIONS.find((o) => o.value === state.tileStyle)?.label}
        open={open.map}
        onToggle={() => toggle("map")}
      >
        <div className="pill-group">
          {TILE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`pill ${state.tileStyle === opt.value ? "pill--on" : ""}`}
              onClick={() => onChange({ tileStyle: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </Section>

      {/* Workplace */}
      <Section
        title="Workplace"
        badge={
          state.workPin
            ? state.workLabel
              ? truncate(state.workLabel.split(",")[0], 20)
              : "Set"
            : "Not set"
        }
        open={open.workplace}
        onToggle={() => toggle("workplace")}
      >
        <div className="workplace-section">
          {state.workPin && (
            <div className="workplace-current">
              <span className="workplace-name">
                {state.workLabel
                  ? truncate(state.workLabel, 48)
                  : `${state.workPin[0].toFixed(4)}, ${state.workPin[1].toFixed(4)}`}
              </span>
              <button
                className="btn-ghost btn--sm"
                onClick={() => onChange({ workPin: null, workLabel: null })}
              >
                Reset
              </button>
            </div>
          )}

          <div className="search-wrap">
            <input
              className="search-input"
              type="text"
              placeholder="Search a place…"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onBlur={() => setTimeout(() => setSearchResults([]), 150)}
            />
            {isSearching && <span className="search-spinner">···</span>}
            {searchResults.length > 0 && (
              <div className="search-dropdown">
                {searchResults.map((r, i) => (
                  <button
                    key={i}
                    className="search-result"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      onChange({ workPin: [r.lat, r.lng], workLabel: r.label });
                      setSearchQuery("");
                      setSearchResults([]);
                    }}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="workplace-actions">
            {isPlacingWorkPin ? (
              <button className="btn-placing btn--sm" onClick={onCancelPlacingWorkPin}>
                Cancel placing
              </button>
            ) : (
              <button className="btn-ghost btn--sm" onClick={onStartPlacingWorkPin}>
                + Click to place on map
              </button>
            )}
            {state.workPin && (
              <>
                <span className="nearby-label">Nearby transit:</span>
                {([5, 10, 15] as const).map((min) => (
                  <button
                    key={min}
                    className="btn-accent btn--sm"
                    onClick={() =>
                      onChange({
                        transitShownRouteIds: nearbyRouteIds(state.workPin!, stations, min),
                        showStations: true,
                      })
                    }
                    title={`Show transit lines reachable by foot in ${min} min`}
                  >
                    {min} min
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      </Section>

      {/* Residence type */}
      <Section
        title="Residence type"
        badge={
          state.categories.length === 2
            ? "All"
            : state.categories.map((c) => CATEGORY_LABELS[c]).join(", ") || "None"
        }
        open={open.filters}
        onToggle={() => toggle("filters")}
      >
        <div className="filters-inner">
          <div className="filter-row">
            <span className="filter-label">Type</span>
            <div className="pill-group">
              {(["private", "crous"] as HousingCategory[]).map((c) => {
                const on = state.categories.includes(c);
                return (
                  <button
                    key={c}
                    className={`pill ${on ? "pill--on" : ""}`}
                    onClick={() =>
                      onChange({ categories: toggleArrayItem(state.categories, c) })
                    }
                  >
                    {CATEGORY_LABELS[c]}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="filter-row">
            <label className="filter-label filter-label--toggle">
              <input
                type="checkbox"
                checked={state.maxRent != null}
                onChange={(e) => onChange({ maxRent: e.target.checked ? 1000 : null })}
              />
              <span>Max rent</span>
              {state.maxRent != null && (
                <span className="filter-val">{state.maxRent} €</span>
              )}
            </label>
            {state.maxRent != null && (
              <input
                className="range"
                type="range"
                min={200}
                max={2000}
                step={50}
                value={state.maxRent}
                onChange={(e) => onChange({ maxRent: Number(e.target.value) })}
              />
            )}
          </div>

          <div className="filter-row">
            <label className="filter-label filter-label--toggle">
              <input
                type="checkbox"
                checked={state.maxCommuteMinutes != null}
                onChange={(e) =>
                  onChange({ maxCommuteMinutes: e.target.checked ? 30 : null })
                }
              />
              <span>Max commute</span>
              {state.maxCommuteMinutes != null && (
                <span className="filter-val">{state.maxCommuteMinutes} min</span>
              )}
            </label>
            {state.maxCommuteMinutes != null && (
              <>
                <input
                  className="range"
                  type="range"
                  min={5}
                  max={90}
                  step={5}
                  value={state.maxCommuteMinutes}
                  onChange={(e) =>
                    onChange({ maxCommuteMinutes: Number(e.target.value) })
                  }
                />
                {!state.workPin && (
                  <span className="filter-hint">Set a workplace first</span>
                )}
              </>
            )}
          </div>

          <div className="filter-row">
            <div className="filter-label">
              <span>Transit speed</span>
              <span className="filter-val">{state.avgTransitSpeedKmh} km/h</span>
            </div>
            <input
              className="range"
              type="range"
              min={10}
              max={50}
              step={1}
              value={state.avgTransitSpeedKmh}
              onChange={(e) =>
                onChange({ avgTransitSpeedKmh: Number(e.target.value) })
              }
            />
          </div>
        </div>
      </Section>

      {/* Surface */}
      <Section
        title="Surface"
        badge={surfaceBadge}
        open={open.surface}
        onToggle={() => toggle("surface")}
      >
        <div className="surface-section">
          <div className="minmax-row">
            <div className="minmax-field">
              <label className="field-label">Min m²</label>
              <input
                className="number-input"
                type="number"
                min={0}
                max={500}
                placeholder="—"
                value={state.minSurface ?? ""}
                onChange={(e) =>
                  onChange({
                    minSurface: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </div>
            <span className="minmax-sep">–</span>
            <div className="minmax-field">
              <label className="field-label">Max m²</label>
              <input
                className="number-input"
                type="number"
                min={0}
                max={500}
                placeholder="—"
                value={state.maxSurface ?? ""}
                onChange={(e) =>
                  onChange({
                    maxSurface: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </div>
          </div>
          {(state.minSurface != null || state.maxSurface != null) && (
            <button
              className="btn-ghost btn--sm"
              onClick={() => onChange({ minSurface: null, maxSurface: null })}
            >
              Clear
            </button>
          )}
        </div>
      </Section>

      {/* Amenities */}
      <Section
        title="Amenities"
        badge={
          state.requiredAmenities.length > 0
            ? `${state.requiredAmenities.length} required`
            : undefined
        }
        open={open.amenities}
        onToggle={() => toggle("amenities")}
      >
        <div className="amenities-section">
          <div className="pill-group">
            {CANONICAL_AMENITIES.map((a) => {
              const on = state.requiredAmenities.includes(a);
              return (
                <button
                  key={a}
                  className={`pill ${on ? "pill--on" : ""}`}
                  onClick={() =>
                    onChange({
                      requiredAmenities: toggleArrayItem(state.requiredAmenities, a),
                    })
                  }
                >
                  {a}
                </button>
              );
            })}
          </div>
          {state.requiredAmenities.length > 0 && (
            <button
              className="btn-ghost btn--sm"
              onClick={() => onChange({ requiredAmenities: [] })}
            >
              Clear
            </button>
          )}
        </div>
      </Section>

      {/* Transit overlay */}
      <Section
        title="Transit overlay"
        badge={
          state.transitShownRouteIds.length > 0
            ? `${state.transitShownRouteIds.length} routes`
            : "Off"
        }
        open={open.transit}
        onToggle={() => toggle("transit")}
      >
        <div className="transit-section">
          <div className="transit-top">
            <div className="pill-group">
              <button
                className="pill"
                onClick={() =>
                  onChange({ transitShownRouteIds: allRoutes.map((r) => r.id) })
                }
              >
                All
              </button>
              <button className="pill" onClick={() => onChange({ transitShownRouteIds: [] })}>
                None
              </button>
              {(["metro", "rer", "tram"] as TransitMode[]).map((m) => (
                <button
                  key={m}
                  className="pill"
                  onClick={() =>
                    onChange({
                      transitShownRouteIds: allRoutes
                        .filter((r) => r.mode === m)
                        .map((r) => r.id),
                    })
                  }
                >
                  {MODE_LABELS[m]}
                </button>
              ))}
            </div>
            <label className="filter-label filter-label--toggle">
              <input
                type="checkbox"
                checked={state.showStations}
                onChange={(e) => onChange({ showStations: e.target.checked })}
              />
              <span>Stations</span>
            </label>
          </div>

          {(["metro", "rer", "tram"] as TransitMode[]).map((m) => {
            const routes = routesByMode[m] ?? [];
            if (routes.length === 0) return null;
            return (
              <div key={m} className="route-group">
                <div className="route-group__label">{MODE_LABELS[m]}</div>
                <div className="route-group__chips">
                  {routes.map((r) => {
                    const on = state.transitShownRouteIds.includes(r.id);
                    return (
                      <button
                        key={r.id}
                        className={`route-chip ${on ? "is-on" : ""}`}
                        style={
                          on
                            ? { background: r.color, borderColor: r.color, color: "#fff" }
                            : { borderColor: r.color, color: r.color }
                        }
                        onClick={() =>
                          onChange({
                            transitShownRouteIds: toggleArrayItem(
                              state.transitShownRouteIds,
                              r.id
                            ),
                          })
                        }
                        title={r.longName ?? r.shortName}
                      >
                        {r.shortName || r.id}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </Section>
    </aside>
  );
}

function Section({
  title,
  badge,
  open,
  onToggle,
  children,
}: {
  title: string;
  badge?: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className={`panel-section ${open ? "is-open" : ""}`}>
      <button className="panel-section__head" onClick={onToggle}>
        <span className="panel-section__title">{title}</span>
        {badge && <span className="panel-section__badge">{badge}</span>}
        <svg
          className="panel-section__chevron"
          width="12"
          height="12"
          viewBox="0 0 12 12"
        >
          <path
            d="M2 4L6 8L10 4"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <div className="panel-section__body">
        <div className="panel-section__inner">{children}</div>
      </div>
    </div>
  );
}

function groupRoutesByMode(routes: TransitRoute[]): Record<TransitMode, TransitRoute[]> {
  const out: Record<TransitMode, TransitRoute[]> = { metro: [], rer: [], tram: [] };
  for (const r of routes) {
    if (r.mode in out) out[r.mode].push(r);
  }
  for (const m of Object.keys(out) as TransitMode[]) {
    out[m].sort((a, b) => natCmp(a.shortName, b.shortName));
  }
  return out;
}

function natCmp(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}
