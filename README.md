# Niroban — Rev 1D

Persian tender monitoring app for Gostaresh Energy.

Rev 1D adds the semi-automatic website checking workflow for the private tender website:

```text
https://setadiran.ir/setad/cms
```

## What Rev 1D adds

- Keeps Rev 1B private login and protected API.
- Keeps Rev 1C daily scan logs.
- Adds a local Playwright scanner template for Setad Iran.
- The scanner is semi-automatic: the user logs in manually, then the script searches and captures candidate opportunities.
- No password is stored in the app or repository.
- Captcha/OTP is not bypassed; the user completes it manually.

## Important architecture

The Playwright scanner should run locally on an authorized computer, not on Vercel. Railway can host the API, but interactive login/captcha is safer locally.

```text
Local Playwright scanner → output JSON → import to Niroban API → Supabase
```

## Scanner setup

```powershell
cd scanner
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
copy setad_config.example.json setad_config.json
```

Edit `scanner/.env` and set:

```env
NIROBAN_API_URL=https://niroban-production.up.railway.app
VITE_SUPABASE_URL=https://qfmrryqtxxhjrxfatnuj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
NIROBAN_EMAIL=kiamarskaveh@yahoo.com
```

Run the assisted scan:

```powershell
python setad_semiauto.py
```

Then import the generated result:

```powershell
python import_to_niroban.py output\setad_opportunities.json
```

## Revision table

| Rev | Date | Description |
|---|---:|---|
| Rev 1A | 2026-05-13 | Manual Persian tender opportunity dashboard |
| Rev 1B | 2026-05-13 | Private login and protected backend API |
| Rev 1C | 2026-05-13 | Daily monitoring workflow and scan logs |
| Rev 1D | 2026-05-13 | Semi-automatic Setad Iran scanner template with Playwright |
