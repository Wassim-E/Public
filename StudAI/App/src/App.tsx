import "./App.css";
import { useMemo, useReducer } from "react";
import { HousingMap } from "./components/HousingMap";
import { FilterSidebar } from "./components/FilterSidebar";
import { useHousingData } from "./useHousingData";
import { useTransitData } from "./useTransitData";
import {
  applyFilters,
  initialFilterState,
  visibleRoutes,
  type FilterState,
} from "./lib/filters";

function reducer(state: FilterState, patch: Partial<FilterState>): FilterState {
  return { ...state, ...patch };
}

export default function App() {
  const { housing, error, loading } = useHousingData();
  const allRoutes = useTransitData();
  const [filters, dispatch] = useReducer(reducer, initialFilterState);

  const filteredHousing = useMemo(
    () => applyFilters(housing, filters),
    [housing, filters]
  );
  const shownRoutes = useMemo(
    () => visibleRoutes(allRoutes, filters),
    [allRoutes, filters]
  );

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
        onWorkPinChange={(pin) => dispatch({ workPin: pin })}
      />
      <FilterSidebar
        state={filters}
        onChange={(patch) => dispatch(patch)}
        matchCount={filteredHousing.length}
        totalCount={housing.length}
        allRoutes={allRoutes}
      />
    </div>
  );
}
