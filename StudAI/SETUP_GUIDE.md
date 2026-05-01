# StudAI - Student Housing Map Setup Guide

## Overview
This project displays student housing residences from Studyrama on an interactive fullscreen map.

## Project Structure

```
StudAI/
├── python/
│   ├── run.ipynb              # Jupyter notebook for API exploration
│   └── transform_data.py      # Script to fetch and transform data
├── App/
│   ├── public/
│   │   └── data/
│   │       └── housing.json   # Generated housing data (253 residences)
│   └── src/
│       ├── App.tsx            # Main app (fullscreen map)
│       ├── App.css            # Fullscreen layout styles
│       ├── types.ts           # TypeScript types for housing data
│       └── components/
│           └── HousingMap.tsx # Interactive map component
```

## Data Flow

```
Studyrama API → Python Script → housing.json → React App → Interactive Map
```

## Setup Instructions

### 1. Fetch Fresh Data from Studyrama

Run the Python script to fetch the latest housing data:

```bash
cd python
python transform_data.py
```

This will:
- Fetch 253 student residences from Studyrama API
- Transform the data to match our Housing type
- Save to `App/public/data/housing.json`
- Display statistics about providers

### 2. Run the React App

```bash
cd App
npm install    # First time only
npm run dev    # Start development server
```

The app will be available at `http://localhost:5173`

## Features

### Fullscreen Interactive Map
- **No sidebar, no clutter** - Just the map occupying the full viewport
- **253 student residences** displayed as markers on the map
- **Auto-fit bounds** - Map automatically zooms to show all residences
- **Click markers** to see residence details

### Residence Information
Each marker popup shows:
- **Name** - Residence name
- **Type** - "Résidence étudiante", "Résidence universitaire Crous", etc.
- **Provider** - ARPEJ, Nexity Studéa, YUGO, CROUS, etc.
- **Rent** - Monthly rent in euros
- **Surface** - Room size in m²
- **Distance** - Distance from Paris center
- **Link** - Direct link to Studyrama listing

## Data Structure

### Housing Type (TypeScript)
```typescript
type Housing = {
  id: string;              // "studyrama-27280"
  name: string;            // "ARPEJ \"Paul Cézanne\""
  provider?: string;       // "Arpej"
  lat: number;             // 49.041693
  lng: number;             // 2.071816
  rent?: number;           // 329 (euros/month)
  surface?: number;        // 14 (m²)
  type?: string;           // "Résidence étudiante"
  distance?: string;       // "27,24 km"
  url?: string;            // Full Studyrama URL
  imageUrl?: string;       // Residence image URL
  lastUpdated?: string;    // "2026-04-26"
};
```

## Statistics (Current Data)

- **Total Residences**: 253
- **Top Providers**:
  - ARPEJ: ~80 residences
  - Nexity Studéa: ~60 residences
  - YUGO: ~10 residences
  - CROUS: ~20 residences

- **Rent Range**: 329€ - 1111€/month
- **Surface Range**: 9m² - 26m²
- **Coverage**: Paris and surrounding areas (30km radius)

## Updating Data

To refresh the housing data:

```bash
cd python
python transform_data.py
```

The React app will automatically load the new data on next refresh.

## Customization

### Change Search Parameters

Edit the API URL in [`python/transform_data.py`](python/transform_data.py):

```python
url = "https://logement.studyrama.com/api/annuaire?center=1&distance=30&surfacemin=9&loyermax=2000..."
```

Parameters:
- `distance=30` - Search radius in km
- `surfacemin=9` - Minimum surface in m²
- `loyermax=2000` - Maximum rent in euros
- `lat=48.8588897&lng=2.3200410217200766` - Center coordinates (Paris)

### Modify Map Appearance

Edit [`App/src/components/HousingMap.tsx`](App/src/components/HousingMap.tsx):
- Change initial zoom level
- Modify popup content
- Add custom markers
- Change map tiles

### Add Filters

Currently, the map shows all residences. To add filters:
1. Add filter state in [`App.tsx`](App/src/App.tsx)
2. Filter the housing array before passing to HousingMap
3. Add UI controls (optional)

## Troubleshooting

### No data showing on map
- Check that `App/public/data/housing.json` exists
- Verify the file contains valid JSON
- Check browser console for errors

### Python script fails
- Ensure `requests` is installed: `pip install requests`
- Check internet connection
- Verify Studyrama API is accessible

### Map not fullscreen
- Clear browser cache
- Check that [`App.css`](App/src/App.css) has fullscreen styles
- Verify no browser extensions are interfering

## Next Steps

Potential enhancements:
1. **Commute time filtering** - Add work location pin and filter by commute time
2. **Price range slider** - Filter residences by rent
3. **Provider filtering** - Show/hide specific providers
4. **Clustering** - Group nearby markers for better performance
5. **Search functionality** - Search by residence name or location
6. **Favorites** - Save favorite residences to localStorage
7. **Comparison view** - Compare multiple residences side-by-side

## License

This project is for educational purposes. Respect Studyrama's terms of service when using their API.
