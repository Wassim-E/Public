import "./FilterSidebar.css";
import type {
  HousingCategory,
  TileStyle,
  TransitMode,
  TransitRoute,
} from "../types";
import { toggleArrayItem, type FilterState } from "../lib/filters";

type Props = {
  state: FilterState;
  onChange: (patch: Partial<FilterState>) => void;
  matchCount: number;
  totalCount: number;
  allRoutes: TransitRoute[];
};

const MODE_LABELS: Record<TransitMode, string> = {
  metro: "Metro",
  rer: "RER",
  tram: "Tram",
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

export function FilterSidebar({
  state,
  onChange,
  matchCount,
  totalCount,
  allRoutes,
}: Props) {
  const routesByMode = groupRoutesByMode(allRoutes);

  return (
    <aside className="filter-sidebar">
      <header className="filter-sidebar__header">
        <div className="filter-sidebar__title">Filters</div>
        <div className="filter-sidebar__count">
          {matchCount} / {totalCount}
        </div>
      </header>

      <section className="filter-section">
        <div className="filter-section__label">Map</div>
        <div className="filter-pills">
          {TILE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`filter-pill ${state.tileStyle === opt.value ? "is-on" : ""}`}
              onClick={() => onChange({ tileStyle: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>

      <section className="filter-section">
        <div className="filter-section__label">Residence type</div>
        <div className="filter-pills">
          {(["private", "crous"] as HousingCategory[]).map((c) => {
            const on = state.categories.includes(c);
            return (
              <button
                key={c}
                className={`filter-pill ${on ? "is-on" : ""}`}
                onClick={() =>
                  onChange({ categories: toggleArrayItem(state.categories, c) })
                }
              >
                {CATEGORY_LABELS[c]}
              </button>
            );
          })}
        </div>
        {state.categories.includes("crous") && !state.categories.includes("private") && (
          <div className="filter-hint">CROUS rents vary with CAF aid; budget filter does not apply</div>
        )}
      </section>

      <section className="filter-section">
        <div className="filter-section__label">Workplace</div>
        {state.workPin ? (
          <div className="filter-pin-status">
            <span>
              {state.workPin[0].toFixed(4)}, {state.workPin[1].toFixed(4)}
            </span>
            <button className="filter-clear" onClick={() => onChange({ workPin: null })}>
              Clear
            </button>
          </div>
        ) : (
          <div className="filter-hint">Click on the map to place</div>
        )}
      </section>

      <section className="filter-section">
        <label className="filter-section__label">
          <input
            type="checkbox"
            checked={state.maxCommuteMinutes != null}
            onChange={(e) =>
              onChange({ maxCommuteMinutes: e.target.checked ? 30 : null })
            }
          />
          <span>Max commute</span>
          {state.maxCommuteMinutes != null && (
            <span className="filter-value">{state.maxCommuteMinutes} min</span>
          )}
        </label>
        {state.maxCommuteMinutes != null && (
          <>
            <input
              type="range"
              min={5}
              max={90}
              step={5}
              value={state.maxCommuteMinutes}
              onChange={(e) => onChange({ maxCommuteMinutes: Number(e.target.value) })}
            />
            {!state.workPin && (
              <div className="filter-hint">Click the map to set a workplace</div>
            )}
          </>
        )}
      </section>

      <section className="filter-section">
        <label className="filter-section__label">
          <input
            type="checkbox"
            checked={state.maxRent != null}
            onChange={(e) => onChange({ maxRent: e.target.checked ? 1000 : null })}
          />
          <span>Max rent</span>
          {state.maxRent != null && (
            <span className="filter-value">{state.maxRent} €</span>
          )}
        </label>
        {state.maxRent != null && (
          <input
            type="range"
            min={200}
            max={2000}
            step={50}
            value={state.maxRent}
            onChange={(e) => onChange({ maxRent: Number(e.target.value) })}
          />
        )}
      </section>

      <section className="filter-section">
        <label className="filter-section__label">
          <span>Transit speed</span>
          <span className="filter-value">{state.avgTransitSpeedKmh} km/h</span>
        </label>
        <input
          type="range"
          min={10}
          max={50}
          step={1}
          value={state.avgTransitSpeedKmh}
          onChange={(e) => onChange({ avgTransitSpeedKmh: Number(e.target.value) })}
        />
      </section>

      <section className="filter-section">
        <div className="filter-section__row">
          <div className="filter-section__label">Transit overlay</div>
          <label className="filter-mini-toggle">
            <input
              type="checkbox"
              checked={state.showStations}
              onChange={(e) => onChange({ showStations: e.target.checked })}
            />
            <span>Stations</span>
          </label>
        </div>

        <div className="filter-pills">
          <button
            className="filter-pill"
            onClick={() => onChange({ transitShownRouteIds: allRoutes.map((r) => r.id) })}
          >
            All
          </button>
          <button
            className="filter-pill"
            onClick={() => onChange({ transitShownRouteIds: [] })}
          >
            None
          </button>
          {(["metro", "rer", "tram"] as TransitMode[]).map((m) => (
            <button
              key={m}
              className="filter-pill"
              onClick={() =>
                onChange({
                  transitShownRouteIds: allRoutes
                    .filter((r) => r.mode === m)
                    .map((r) => r.id),
                })
              }
            >
              {MODE_LABELS[m]}s
            </button>
          ))}
        </div>

        {(["metro", "rer", "tram"] as TransitMode[]).map((m) => {
          const routes = routesByMode[m] ?? [];
          if (routes.length === 0) return null;
          return (
            <div key={m} className="filter-route-row">
              <div className="filter-route-row__label">{MODE_LABELS[m]}</div>
              <div className="filter-route-row__chips">
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
      </section>
    </aside>
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
