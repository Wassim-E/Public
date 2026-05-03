import "./FilterSidebar.css";
import type { TransitMode, TransitRoute } from "../types";
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

export function FilterSidebar({ state, onChange, matchCount, totalCount, allRoutes }: Props) {
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
        <div className="filter-hint">
          Used to convert commute minutes to a circle. 25 km/h ≈ Paris metro+walk.
        </div>
      </section>

      <section className="filter-section">
        <div className="filter-section__label">Transit overlay</div>
        <div className="filter-modes">
          {(["metro", "rer", "tram"] as TransitMode[]).map((m) => {
            const on = state.transitVisibleModes.includes(m);
            return (
              <label key={m} className={`filter-mode-pill ${on ? "is-on" : ""}`}>
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() =>
                    onChange({
                      transitVisibleModes: toggleArrayItem(state.transitVisibleModes, m),
                    })
                  }
                />
                <span>
                  {MODE_LABELS[m]} ({routesByMode[m]?.length ?? 0})
                </span>
              </label>
            );
          })}
        </div>

        {(["metro", "rer", "tram"] as TransitMode[]).map((m) => {
          if (!state.transitVisibleModes.includes(m)) return null;
          const routes = routesByMode[m] ?? [];
          if (routes.length === 0) return null;
          return (
            <details key={m} className="filter-routes-details">
              <summary>{MODE_LABELS[m]} routes</summary>
              <div className="filter-routes-grid">
                {routes.map((r) => {
                  const hidden = state.transitHiddenRouteIds.includes(r.id);
                  return (
                    <label key={r.id} className={`filter-route-chip ${hidden ? "is-off" : ""}`}>
                      <input
                        type="checkbox"
                        checked={!hidden}
                        onChange={() =>
                          onChange({
                            transitHiddenRouteIds: toggleArrayItem(
                              state.transitHiddenRouteIds,
                              r.id
                            ),
                          })
                        }
                      />
                      <span className="route-dot" style={{ background: r.color }} />
                      <span className="route-name">{r.shortName || r.id}</span>
                    </label>
                  );
                })}
              </div>
            </details>
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
