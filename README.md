# Niroban — Rev 1E

Persian tender monitoring app for Gostaresh Energy.

## Rev 1E purpose

Rev 1E adds the first step toward Option 2 architecture: the customer logs in to Niroban web, then Niroban tests whether its cloud backend can reach Setad Iran.

Target website:

```text
https://setadiran.ir/setad/cms
```

Rev 1E does **not** store Setad credentials and does **not** bypass CAPTCHA or OTP. It only tests cloud accessibility and records the result as a scan log.

## Added backend endpoint

```text
POST /setad/access-test
```

Protected by Supabase login token. It checks:

- Can Railway/backend reach Setad Iran?
- HTTP status and final URL
- Whether login/captcha/OTP indicators appear in the page text
- Optional Playwright browser check if enabled later

## Backend variables

```env
SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_...
FRONTEND_URL=https://niroban.vercel.app
ALLOWED_EMAILS=alireza.yavarian@gmail.com,kiamarskaveh@yahoo.com
SETAD_DEFAULT_URL=https://setadiran.ir/setad/cms
SETAD_ACCESS_TEST_TIMEOUT_SECONDS=30
SETAD_PLAYWRIGHT_ENABLED=false
```

Keep `SETAD_PLAYWRIGHT_ENABLED=false` for the first deployment. This keeps Railway stable while we test network accessibility first.

## Frontend variables

```env
VITE_API_URL=https://niroban-production.up.railway.app
VITE_SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
```

## Deployment

```powershell
cd D:\Kiamars\Niroban
git add .
git commit -m "Rev 1E add Setad cloud access test"
git push origin main
```

Then make sure Railway is running Rev 1E:

```text
https://niroban-production.up.railway.app/
```

Expected:

```json
{"app":"Niroban API","status":"running","revision":"Rev 1E"}
```

## Next after Rev 1E

If Setad is reachable from Railway/cloud, move to Rev 1F: controlled remote login session.
If Setad is blocked from cloud, move the remote browser worker to a VPS/network that can access Setad.
