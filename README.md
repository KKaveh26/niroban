# Niroban — Rev 1C

Persian tender monitoring app for Gostaresh Energy.

## Rev 1C purpose

Rev 1C adds the real daily monitoring workflow:

- Daily check log for a private tender website
- Manual registration of daily scan result
- Scan status: success, failed, login required, captcha required
- Target opportunity types: tenders, price inquiry only, inquiries
- Target keywords: relay, feeder, substation, capacitor
- Target regions: all Iran, with priority for south of Iran and Semnan
- Protected backend API through Supabase Auth

## Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Required backend variables:

```env
SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_...
FRONTEND_URL=http://localhost:5173
ALLOWED_EMAILS=alireza.yavarian@gmail.com,kiamarskaveh@yahoo.com
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Required frontend variables:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
```

## Deployment

Railway backend:

```env
SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_...
FRONTEND_URL=https://niroban.vercel.app
ALLOWED_EMAILS=alireza.yavarian@gmail.com,kiamarskaveh@yahoo.com
```

Vercel frontend:

```env
VITE_API_URL=https://niroban-production.up.railway.app
VITE_SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
```

## Revision table

| Rev | Date | Description |
|---|---:|---|
| Rev 1A | 2026-05-13 | Manual Persian tender dashboard |
| Rev 1B | 2026-05-13 | Private login and protected backend API |
| Rev 1C | 2026-05-13 | Daily monitoring workflow and scan logs |
