# StudAI (Frontend)

Vite + React app for the Paris student housing "truth" map.

## Dev

```bash
cd App
npm install
npm run dev
```

## Build (GitHub Pages friendly)

```bash
cd App
npm run build
```

The app uses `base: "./"` so it can be hosted from a subpath on GitHub Pages.

## Data

The map loads `App/public/data/housing.json` at runtime. Minimal schema:

- `id`, `name`, `lat`, `lng`
- Optional: `officialRating`, `googleRating`, `reviewCount`, `builtYear`, `cockroachMentionsLast12Mo`, `url`, `lastUpdated`
