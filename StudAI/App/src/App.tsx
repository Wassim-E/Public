import "./App.css";
import { useEffect, useReducer, useMemo, useState } from "react";
import { HousingMap } from "./components/HousingMap";
import { FilterSidebar } from "./components/FilterSidebar";
import { ResidenceDetail } from "./components/ResidenceDetail";
import { useHousingData } from "./useHousingData";
import { useTransitData } from "./useTransitData";
import { useStationsData } from "./useStationsData";
import {
  applyFilters,
  initialFilterState,
  visibleRoutes,
  type FilterState,
} from "./lib/filters";
import { useCommuteData } from "./useCommuteData";
import type { Housing } from "./types";

const FILTERS_KEY = "studai_filters";

function loadFilters(): FilterState {
  try {
    const raw = localStorage.getItem(FILTERS_KEY);
    if (!raw) return initialFilterState;
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
  const [selectedHousing, setSelectedHousing] = useState<Housing | null>(null);

  const [filters, dispatch] = useReducer(reducer, undefined, loadFilters);

  useEffect(() => {
    localStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
  }, [filters]);

  const { commuteMap, isComputing, remaining, total, routingError } = useCommuteData(
    housing,
    filters.workPin
  );

  const filteredHousing = useMemo(
    () => applyFilters(housing, filters, stations, commuteMap),
    [housing, filters, stations, commuteMap]
  );
  const shownRoutes = useMemo(
    () => visibleRoutes(allRoutes, filters),
    [allRoutes, filters]
  );

  const ratedCount = useMemo(
    () => housing.filter((h) => h.googleRating != null).length,
    [housing]
  );

  function handleWorkPinChange(pin: [number, number] | null, label?: string) {
    dispatch({ workPin: pin, workLabel: label ?? null });
    setIsPlacingWorkPin(false);
  }

  const selectedCommute = selectedHousing
    ? (commuteMap[selectedHousing.id] ?? null)
    : null;

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

      {selectedHousing && (
        <ResidenceDetail
          housing={selectedHousing}
          onClose={() => setSelectedHousing(null)}
          commuteResult={selectedCommute}
        />
      )}

      <HousingMap
        housing={filteredHousing}
        filters={filters}
        transitRoutes={shownRoutes}
        stations={stations}
        commuteMap={commuteMap}
        isPlacingWorkPin={isPlacingWorkPin}
        selectedId={selectedHousing?.id ?? null}
        onWorkPinChange={handleWorkPinChange}
        onSelect={(h) => setSelectedHousing(h)}
      />
      {isPlacingWorkPin && (
        <div className="placing-overlay">
          <div className="placing-hint">Click on the map to place your workplace</div>
        </div>
      )}
      <FilterSidebar
        state={filters}
        onChange={(patch) => dispatch(patch)}
        matchCount={filteredHousing.length}
        totalCount={housing.length}
        ratedCount={ratedCount}
        allRoutes={allRoutes}
        stations={stations}
        isComputing={isComputing}
        routingRemaining={remaining}
        routingTotal={total}
        routingError={routingError}
        isPlacingWorkPin={isPlacingWorkPin}
        onStartPlacingWorkPin={() => setIsPlacingWorkPin(true)}
        onCancelPlacingWorkPin={() => setIsPlacingWorkPin(false)}
      />
    </div>
  );
}
