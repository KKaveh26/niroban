# Niroban — Rev 1A

**Niroban** is a Persian RTL tender and inquiry monitoring dashboard for electrical companies.

Rev 1A is the manual version for the first customer use case: **Gostaresh Energy**.
It helps the customer register and track tenders, price inquiries, and inquiries related to electrical keywords such as relay, feeder, substation, and capacitor.

## Stack

- Frontend: React + Vite
- Backend: Python FastAPI
- Database: Supabase PostgreSQL
- Frontend Hosting: Vercel
- Backend Hosting: Railway

## Project Structure

```text
niroban-rev1a/
  backend/
    main.py
    requirements.txt
    .env.example
    railway.json
  frontend/
    index.html
    package.json
    vite.config.js
    vercel.json
    .env.example
    src/
      main.jsx
      App.jsx
      styles.css
      pages/
        TenderMonitor.jsx
      services/
        api.js
  database/
    niroban_rev1a.sql
```

## Backend Setup — Local VS Code

```bash
cd backend
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload
```

Backend local URL:

```text
http://localhost:8000
```

## Backend Environment Variables

Create `backend/.env` locally and add:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
FRONTEND_URL=http://localhost:5173
```

On Railway, add the same variables, but set:

```env
FRONTEND_URL=https://YOUR_VERCEL_APP.vercel.app
```

Important: keep `SUPABASE_SERVICE_KEY` only in Railway/backend. Never expose it in the frontend.

## Frontend Setup — Local VS Code

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend local URL:

```text
http://localhost:5173
```

## Frontend Environment Variables

Create `frontend/.env.local` locally:

```env
VITE_API_URL=http://localhost:8000
```

On Vercel, add:

```env
VITE_API_URL=https://YOUR_RAILWAY_BACKEND.up.railway.app
```

## Deployment Flow

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Rev 1A create Niroban tender monitor"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

### 2. Deploy Backend to Railway

Railway project root should point to:

```text
backend
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 3. Deploy Frontend to Vercel

Vercel project root should point to:

```text
frontend
```

Build command:

```bash
npm run build
```

Output directory:

```text
dist
```

## Revision Table

| Rev | Date | Description |
|---|---:|---|
| Rev 1A | 2026-05-13 | Created Niroban project structure with Persian RTL frontend, FastAPI backend, Supabase REST connection, Vercel config, and Railway config. |
