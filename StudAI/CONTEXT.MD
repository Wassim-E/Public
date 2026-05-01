# Paris Student Housing "Truth" Map

## 🎯 Objective
A specialized data visualization tool to find student housing in Paris by cross-referencing official listings with "ground truth" data (Google Reviews) to bypass deceptive marketing. The goal is to filter by actual commute time, building age, and sentiment-extracted criteria (e.g., "no cockroaches").

## 👤 Context
* **Developer:** AI/Data Science MS grad.
* **Problem:** Discrepancy between official site ratings (5 stars) vs. Google Reviews (2 stars). Existing tools lack commute-time filtering from specific work addresses and qualitative filters (pests, noise, building age).

## 🛠 Tech Stack (The "Lean" Architecture)
* **Backend/Data:** Python-based scrapers (running via GitHub Actions).
* **Storage:** Static `JSON` files (Flat-file database approach).
* **AI/NLP:** LLM-based sentiment analysis to extract features from review text (cockroach sightings, management quality, noise).
* **Frontend:** Vite + React/Vue hosted on **GitHub Pages** (Zero-cost hosting).
* **Mapping:** Leaflet.js or MapLibre GL for the interactive map.

## 📊 Data Pipeline
1.  **Scraping:** * **Housing:** Studapart, Nexity, Adele, etc.
    * **Reviews:** Google Maps Reviews (via 3rd party APIs like Outscraper to bypass 5-review limits).
    * **Urban Data:** Open Data Paris (for building construction dates) and Insee (for neighborhood socio-economic proxies).
2.  **Processing (Python):**
    * Calculate **"Truth Scores"** (Delta between official vs. public ratings).
    * Run NLP keyword extraction for red flags (pests, heating issues).
    * Pre-compute proximity to Metro/RER lines.
3.  **Frontend Logic (JS):**
    * Client-side filtering of the JSON dataset.
    * Distance/Commute visualization based on selected transport lines or pre-calculated hubs.

## 🚀 Key Features
* **Commute Filter:** Show housing within 30 min of a user-defined work address.
* **Cockroach-Free Toggle:** Filter out residences with pest mentions in the last 12 months.
* **Age Filter:** Focus on modern buildings (>2015) to ensure better insulation.
* **Zero-Maintenance:** GitHub Actions automatically updates the data and redeploys the site weekly.
