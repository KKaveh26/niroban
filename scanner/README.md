# Niroban Rev 1D — Setad Iran semi-automatic scanner

This scanner is for the private tender website:

```text
https://setadiran.ir/setad/cms
```

It is intentionally **semi-automatic**:

- It opens a visible browser.
- You log in manually.
- You complete captcha/OTP manually if the website asks.
- The script then tries to search the configured opportunity types and keywords.
- It saves screenshots, text snapshots, and a JSON output file.

It does not bypass login, captcha, OTP, access controls, or website restrictions.

## Setup

```powershell
cd D:\Kiamars\Niroban\scanner
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
copy setad_config.example.json setad_config.json
```

Edit `.env` and set your publishable Supabase key.

## Run scan

```powershell
python setad_semiauto.py
```

Output:

```text
scanner/output/setad_opportunities.json
scanner/output/setad_scan_log.json
scanner/screenshots/
scanner/snapshots/
```

## Import to Niroban

```powershell
python import_to_niroban.py output\setad_opportunities.json
```

The import script asks for your Supabase login password in the terminal and does not store it.
