# React frontend (alternative to the Streamlit dashboard)

This is a second, optional frontend for the ESG Claim Verification &
Greenwashing Risk Analyzer. It talks to the exact same FastAPI backend
(`app/api/main.py`) as the Streamlit dashboard in `streamlit_app/app.py` -
both are kept, both are real, pick whichever you want to demo with.

It contains **no business logic**. Every verdict, score, and explanation
rendered here is exactly what the backend returned - the same rule that
applies to the Streamlit app.

## Run it

The FastAPI backend must already be running (see the main project README):

```bash
uvicorn app.api.main:app --reload
```

Then, in this `web/` directory:

```bash
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`). The backend URL
is configurable in the sidebar if it's not running on `http://127.0.0.1:8000`.

## What's here

- `src/lib/api.ts` - thin fetch wrapper around `/health`, `/analyze`,
  `/demo/dataset`. Throws on any error; never swallows a failure into a fake
  success.
- `src/lib/types.ts` - TypeScript types mirroring the backend's JSON shapes.
- `src/components/` - `ConfigPanel` (sidebar), `UploadAnalyzePage`,
  `DatasetDemoPage`, `ExecutiveSummary`, `ClaimsTable`, `ClaimDetail` (the six
  tabs: Checkability / Evidence / Verification / Numerical Checks / Risk Score
  / Audit Trail), `DisclaimerBanner`.

## Build for production

```bash
npm run build
```

Outputs static files to `dist/`, servable by any static file server. CORS on
the backend is currently open (`allow_origins=["*"]`) for local academic-demo
use - tighten this before deploying either frontend anywhere public.
