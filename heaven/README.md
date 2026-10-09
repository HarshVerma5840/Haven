# Heaven – Employee Wellbeing Suite

Heaven is an AI-powered **burnout risk analysis** platform embedded inside Frappe HRMS.

## Overview

HR managers can type natural-language queries and instantly get insights about:
- 🔥 Burnout risk scores per employee / team
- 📊 Stress trend analysis
- 🤖 AI-powered recommendations
- 🔔 Early warning alerts

## Project Structure

```
heaven/
├── frontend/          ← Vue.js 3 + Frappe UI frontend (future)
│   ├── src/
│   │   ├── views/
│   │   │   ├── Dashboard.vue
│   │   │   ├── BurnoutAnalysis.vue
│   │   │   └── ChatInterface.vue
│   │   └── main.js
│   └── package.json
├── backend/           ← Python FastAPI backend (see /haven-backend)
└── README.md
```

## Status

> **Frontend & Backend – Coming Soon** 🚀

Currently in active development. The desk app card is live at `/heaven`.

## Integration

Heaven runs as a **sub-app** inside the HRMS Frappe site:
- Frappe desk shows the Heaven app tile (sequence 1)
- Clicking it opens `/heaven` (coming soon page for now)
- Future: will embed the full Vue SPA via Frappe's `www` route

## Development

```bash
# Backend is in /haven-backend (FastAPI)
cd haven-backend
uvicorn app.main:app --reload

# Frontend will be in /heaven/frontend
cd heaven/frontend
yarn dev
```

