# AI-Powered Creator Intelligence Platform

Stack: React (Vite, Tailwind) + FastAPI + PostgreSQL.

## One-time setup (Windows)
1. In pgAdmin create a database named `creator_intel`.
2. Double-click `setup_backend.bat`, then edit `backend\.env` and set DB_PASSWORD.
3. Double-click `setup_frontend.bat`.

## Run (two terminals, both stay open)
- `start_backend.bat`  -> http://localhost:8000/docs
- `start_frontend.bat` -> http://localhost:5173

## Tests
`run_tests.bat`

## Dataset
Put the Kaggle CSV in `data\raw\` (never edit it).
