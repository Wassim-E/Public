import "./App.css";
import { useEffect, useReducer, useMemo, useState } from "react";
import { HousingMap } from "./components/HousingMap";
import { FilterSidebar } from "./components/FilterSidebar";
import { useHousingData } from "./useHousingData";
import { useTransitData } from "./useTransitData";
import { useStationsData } from "./useStationsData";
import {
  applyFilters,
  initialFilterState,
  visibleRoutes,
  type FilterState,
} from "./lib/filters";

const FILTERS_KEY = "studai_filters";

function loadFilters(): FilterState {
  try {
    const raw = localStorage.getItem(FILTERS_KEY);
    if (!raw) return initialFilterState;
    // Merge with initialFilterState so any new keys added in the future get defaults
    return { ...initialFilterState, ...JSON.parse(raw) };
  } catch {
    return initialFilterState;
  }
}

function reducer(state: FilterState, patch: Partial<FilterState>): FilterState {
  return { ...state, ...patch };
}

export default function App() {
  const { housing, error, loading } = useHousingData();
  const allRoutes = useTransitData();
  const stations = useStationsData();
  const [isPlacingWorkPin, setIsPlacingWorkPin] = useState(false);

  // Initializer form — loadFilters() is called exactly once
  const [filters, dispatch] = useReducer(reducer, undefined, loadFilters);

  useEffect(() => {
    localStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
  }, [filters]);

  const filteredHousing = useMemo(
    () => applyFilters(housing, filters, stations),
    [housing, filters, stations]
  );
  const shownRoutes = useMemo(
    () => visibleRoutes(allRoutes, filters),
    [allRoutes, filters]
  );

  function handleWorkPinChange(pin: [number, number] | null, label?: string) {
    dispatch({ workPin: pin, workLabel: label ?? null });
    setIsPlacingWorkPin(false);
  }

  return (
    <div className="fullscreen-layout">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-content">Loading residences...</div>
        </div>
      )}
      {error && (
        <div className="error-overlay">
          <div className="error-content">Error: {error}</div>
        </div>
      )}
      <HousingMap
        housing={filteredHousing}
        filters={filters}
        transitRoutes={shownRoutes}
        stations={stations}
        isPlacingWorkPin={isPlacingWorkPin}
        onWorkPinChange={handleWorkPinChange}
      />
      {isPlacingWorkPin && (
        <div className="placing-overlay">
          <div className="placing-hint">
            Click on the map to place your workplace
          </div>
        </div>
      )}
      <FilterSidebar
        state={filters}
        onChange={(patch) => dispatch(patch)}
        matchCount={filteredHousing.length}
        totalCount={housing.length}
        allRoutes={allRoutes}
        stations={stations}
        isPlacingWorkPin={isPlacingWorkPin}
        onStartPlacingWorkPin={() => setIsPlacingWorkPin(true)}
        onCancelPlacingWorkPin={() => setIsPlacingWorkPin(false)}
      />
    </div>
  );
}
