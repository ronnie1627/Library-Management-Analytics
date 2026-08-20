# Library Pulse — Library Management Analytics

A circulation analytics dashboard built for a Data Analytics & Visualization
course project. Goes beyond a basic library catalog by layering real
analytics on top: member segmentation (RFM + KMeans), demand trends,
activity heatmaps, and a co-occurrence book recommender.

## Stack
- **Data**: Pandas-generated synthetic dataset (`generate_data.py`) with
  deliberately engineered patterns — exam-season spikes, a rising Sci-Fi/Tech
  trend, chronic late-returners, uneven branch load, weekday/afternoon peaks.
- **Backend**: Flask
- **Analytics**: Pandas (aggregation/EDA), scikit-learn (KMeans clustering)
- **Visualization**: Plotly (interactive, rendered client-side via Plotly.js)
  + Matplotlib/Seaborn for the static EDA report (`eda_report.py`)

## Setup (local) — fully automatic
```bash
pip install -r requirements-full.txt
python3 app.py
```
That's it. The first time you run it, the app automatically:
1. Tries to pull real book data from the open-source Open Library API
2. Falls back to realistic synthetic books if that's unavailable (offline, API down, etc.)
3. Generates the simulated members/transactions/branches around whichever books it ended up with
4. Starts the site at http://localhost:5000

Every run after that is instant — it detects the data already exists and
skips straight to starting the server. Delete the data/ folder if you ever
want it to regenerate everything from scratch.

Optional: `python3 eda_report.py` generates static Matplotlib/Seaborn PNGs
for a report appendix (needs the packages in requirements-full.txt).

## Deploying to Vercel
The data/ folder already has generated CSVs committed, and requirements.txt
is trimmed to just what the live site needs (flask, pandas, numpy, plotly,
scikit-learn) — Vercel's Python runtime installs from requirements.txt
automatically, and vercel.json tells it to run app.py as a serverless
function. Push this folder to GitHub, then import the repo on vercel.com
with no extra config needed.

Note: Vercel functions are stateless (no writing new files at request time)
and cap execution at 10s on the free plan, so this setup relies on the CSVs
already being present rather than regenerating them on each deploy.

## Project structure
```
library_pulse/
├── bootstrap.py           # auto-runs the setup below on first launch
├── fetch_real_books.py    # optional: pulls real books from Open Library API
├── generate_data.py       # synthetic data generator (Pandas + Faker)
├── analytics.py           # all Pandas transforms, KMeans segmentation, Plotly figures
├── app.py                 # Flask routes (calls bootstrap.py automatically)
├── eda_report.py          # Matplotlib/Seaborn static charts for the report
├── requirements.txt       # trimmed set for deployment (Vercel)
├── requirements-full.txt  # full set for local dev (includes faker/requests/etc)
├── api/index.py           # Vercel entry point
├── vercel.json            # Vercel routing config
├── data/                  # generated CSVs (members, books, branches, transactions)
├── eda_output/            # generated PNGs from eda_report.py
├── templates/              # Jinja2 HTML templates
└── static/                 # CSS, JS, bundled Plotly.js
```

## Pages
- `/` — KPIs, genre trend, activity heatmap, branch volume
- `/members` — RFM member segmentation (Power Readers / Occasional / Lapsing / Fine-Prone)
- `/trends` — genre-filterable top-10 books
- `/branches` — branch comparison table + charts
- `/book/<id>` — book detail + "readers who borrowed this also borrowed" recommendations
- `/insights` — plain-language write-up of what the analysis found

## Extending with real data
Swap the CSVs in `data/` for real exports from your library system (Koha,
Alma, etc.) with the same column names, and everything downstream — the
segmentation, trends, and dashboard — works unchanged.
