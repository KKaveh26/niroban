# Niroban — Rev 1B

Persian tender and inquiry monitoring dashboard for Gostaresh Energy.

## Rev 1B adds

- Supabase email/password login on the frontend
- Private dashboard after login only
- Backend API protection with Supabase Auth access token
- Allowed email restriction with `ALLOWED_EMAILS`
- Logout button

## Local backend

```bash
cd backend
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

`backend/.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=YOUR_SUPABASE_SERVICE_ROLE_OR_SB_SECRET_KEY
FRONTEND_URL=http://localhost:5173
ALLOWED_EMAILS=your-email@example.com
```

## Local frontend

```bash
cd frontend
npm install
npm run dev
```

`frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY
```

## Supabase Auth setup

Create an Auth user in Supabase for the allowed email. Use the same email in Railway `ALLOWED_EMAILS`.

## Railway variables

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=YOUR_SUPABASE_SERVICE_ROLE_OR_SB_SECRET_KEY
FRONTEND_URL=https://niroban.vercel.app
ALLOWED_EMAILS=your-email@example.com
```

## Vercel variables

```env
VITE_API_URL=https://niroban-production.up.railway.app
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY
```

## Deployment

After changing files:

```bash
git add .
git commit -m "Rev 1B add private login"
git push origin main
```

Then redeploy Railway and Vercel if they do not auto-deploy.
