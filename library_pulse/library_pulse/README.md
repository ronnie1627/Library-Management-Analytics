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

## Setup (local)
```bash
pip install -r requirements-full.txt   # includes data-generation tools
python3 generate_data.py                # creates data/*.csv (only needed once)
python3 eda_report.py                   # optional: static PNGs -> eda_output/
python3 app.py                          # starts the site at http://localhost:5000
```

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
├── generate_data.py     # synthetic data generator (Pandas + Faker)
├── analytics.py          # all Pandas transforms, KMeans segmentation, Plotly figures
├── app.py                 # Flask routes
├── eda_report.py          # Matplotlib/Seaborn static charts for the report
├── requirements.txt
├── data/                  # generated CSVs (members, books, branches, transactions)
├── eda_output/             # generated PNGs from eda_report.py
├── templates/               # Jinja2 HTML templates
└── static/css/style.css     # design system
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
