import "./App.css";
import { HousingMap } from "./components/HousingMap";
import { useHousingData } from "./useHousingData";

export default function App() {
  const { housing, error, loading } = useHousingData();

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
      <HousingMap housing={housing} />
    </div>
  );
}

