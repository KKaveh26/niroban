import os
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "").split(",")
    if email.strip()
]

SETAD_DEFAULT_URL = os.getenv("SETAD_DEFAULT_URL", "https://setadiran.ir/setad/cms")
SETAD_ACCESS_TEST_TIMEOUT_SECONDS = float(os.getenv("SETAD_ACCESS_TEST_TIMEOUT_SECONDS", "30"))
SETAD_PLAYWRIGHT_ENABLED = os.getenv("SETAD_PLAYWRIGHT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}

OpportunityType = Literal["tender", "price_inquiry", "inquiry"]
OpportunityStatus = Literal["new", "reviewed", "relevant", "not_relevant", "applied", "missed"]
RegionPriority = Literal["south", "semnan", "other"]
RuleOpportunityType = Literal["tender", "price_inquiry", "inquiry", "all"]
RuleRegionPriority = Literal["south", "semnan", "other", "all"]
ScanMode = Literal["manual", "semi_automatic", "automatic"]
ScanStatus = Literal["pending", "success", "failed", "login_required", "captcha_required"]

app = FastAPI(
    title="Niroban API",
    description="Persian tender monitoring API for electrical companies.",
    version="1.0.0-rev1e",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_supabase_config() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=500,
            detail="Supabase environment variables are missing. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.",
        )


def supabase_headers(prefer_return: bool = False) -> dict[str, str]:
    check_supabase_config()

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"
    return headers


def supabase_table_url(table_name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table_name}"


async def require_user(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> dict:
    """Verify the Supabase Auth access token and optionally restrict allowed emails."""
    check_supabase_config()

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Login required")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": authorization,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="Invalid or expired login session")

    user = response.json()
    user_email = (user.get("email") or "").lower()

    if ALLOWED_EMAILS and user_email not in ALLOWED_EMAILS:
        raise HTTPException(status_code=403, detail="This email is not allowed to access Niroban")

    return user


class OpportunityCreate(BaseModel):
    customer_name: str = Field(default="Gostaresh Energy")
    title: str = Field(min_length=1)
    opportunity_type: OpportunityType
    company_name: Optional[str] = None
    province: Optional[str] = None
    region_priority: Optional[RegionPriority] = None
    matched_keyword: Optional[str] = None
    publish_date: Optional[date] = None
    deadline_date: Optional[date] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None
    status: OpportunityStatus = "new"


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    opportunity_type: Optional[OpportunityType] = None
    company_name: Optional[str] = None
    province: Optional[str] = None
    region_priority: Optional[RegionPriority] = None
    matched_keyword: Optional[str] = None
    publish_date: Optional[date] = None
    deadline_date: Optional[date] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[OpportunityStatus] = None


class SearchRuleCreate(BaseModel):
    customer_name: str = Field(default="Gostaresh Energy")
    keyword_en: Optional[str] = None
    keyword_fa: str = Field(min_length=1)
    opportunity_type: RuleOpportunityType = "all"
    region_priority: RuleRegionPriority = "all"
    active: bool = True


class ScanLogCreate(BaseModel):
    customer_name: str = Field(default="Gostaresh Energy")
    scan_date: date = Field(default_factory=date.today)
    source_name: str = Field(default="Private Tender Website")
    source_url: Optional[str] = None
    scan_mode: ScanMode = "manual"
    status: ScanStatus = "success"
    checked_opportunity_types: list[str] = Field(default_factory=lambda: ["tender", "price_inquiry", "inquiry"])
    checked_keywords: list[str] = Field(default_factory=lambda: ["relay", "feeder", "substation", "capacitor"])
    checked_regions: list[str] = Field(default_factory=lambda: ["south", "semnan", "all_iran"])
    total_found: int = 0
    new_opportunities: int = 0
    relevant_opportunities: int = 0
    notes: Optional[str] = None
    finished_at: Optional[datetime] = None


class ScanLogUpdate(BaseModel):
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    scan_mode: Optional[ScanMode] = None
    status: Optional[ScanStatus] = None
    total_found: Optional[int] = None
    new_opportunities: Optional[int] = None
    relevant_opportunities: Optional[int] = None
    notes: Optional[str] = None
    finished_at: Optional[datetime] = None

class SetadAccessTestCreate(BaseModel):
    source_url: str = Field(default_factory=lambda: SETAD_DEFAULT_URL)
    run_browser_check: bool = Field(
        default=False,
        description="When true, backend also tries a Playwright Chromium browser check. Keep false until the server has browser dependencies installed.",
    )


def detect_login_indicators(text: str) -> dict[str, bool]:
    normalized = (text or "").lower()
    login_words = [
        "ورود",
        "نام کاربری",
        "رمز عبور",
        "کلمه عبور",
        "login",
        "username",
        "password",
        "sign in",
    ]
    captcha_words = [
        "کد امنیتی",
        "کپچا",
        "captcha",
        "تصویر امنیتی",
        "عبارت امنیتی",
    ]
    otp_words = [
        "رمز یکبار",
        "رمز یک بار",
        "otp",
        "پیامک",
        "sms",
    ]
    return {
        "login_detected": any(word in normalized for word in login_words),
        "captcha_detected": any(word in normalized for word in captcha_words),
        "otp_detected": any(word in normalized for word in otp_words),
    }


def create_setad_message_fa(result: dict[str, Any]) -> str:
    if result.get("http_error") and not result.get("reachable"):
        return "اتصال از سرور نیروبان ناموفق بود؛ احتمال محدودیت شبکه، IP، DNS یا دسترسی وجود دارد."
    if result.get("browser_error"):
        return "تست HTTP انجام شد، اما تست مرورگر Playwright روی سرور آماده نیست یا خطا دارد."
    if result.get("captcha_detected") or result.get("otp_detected"):
        return "صفحه ستاد ایران قابل دسترسی است، اما ورود دستی، کپچا یا رمز یکبارمصرف محتمل است."
    if result.get("login_detected"):
        return "صفحه ورود ستاد ایران از سرور نیروبان قابل دسترسی است؛ مرحله بعد ساخت ورود دستی کنترل‌شده است."
    if result.get("reachable"):
        return "سامانه ستاد ایران از سرور نیروبان قابل دسترسی است."
    return "نتیجه تست اتصال مشخص نیست؛ لاگ و اسکرین‌شات سرور باید بررسی شود."


async def save_setad_access_scan_log(result: dict[str, Any], current_user: dict) -> dict | None:
    status: str = "failed"
    if result.get("reachable"):
        status = "login_required" if result.get("login_detected") else "success"
        if result.get("captcha_detected") or result.get("otp_detected"):
            status = "captcha_required"

    note_lines = [
        "Rev 1E cloud access test for Setad Iran.",
        f"User: {current_user.get('email')}",
        f"URL: {result.get('source_url')}",
        f"HTTP status: {result.get('http_status')}",
        f"Reachable: {result.get('reachable')}",
        f"Login detected: {result.get('login_detected')}",
        f"Captcha detected: {result.get('captcha_detected')}",
        f"OTP detected: {result.get('otp_detected')}",
        f"Playwright enabled: {result.get('playwright_enabled')}",
        f"Browser status: {result.get('browser_status')}",
        result.get("message_fa", ""),
    ]
    if result.get("http_error"):
        note_lines.append(f"HTTP error: {result.get('http_error')}")
    if result.get("browser_error"):
        note_lines.append(f"Browser error: {result.get('browser_error')}")

    payload = {
        "customer_name": "Gostaresh Energy",
        "scan_date": date.today().isoformat(),
        "source_name": "سامانه ستاد ایران - تست اتصال ابری",
        "source_url": result.get("source_url"),
        "scan_mode": "semi_automatic",
        "status": status,
        "checked_opportunity_types": ["tender", "price_inquiry", "inquiry"],
        "checked_keywords": ["relay", "feeder", "substation", "capacitor"],
        "checked_regions": ["south", "semnan", "all_iran"],
        "total_found": 0,
        "new_opportunities": 0,
        "relevant_opportunities": 0,
        "notes": "\n".join([line for line in note_lines if line]),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            supabase_table_url("tender_scan_logs"),
            headers=supabase_headers(prefer_return=True),
            json=payload,
        )

    if response.status_code >= 400:
        result["scan_log_save_error"] = response.text
        return None

    created = response.json()
    return created[0] if created else None


async def run_optional_playwright_check(source_url: str, result: dict[str, Any]) -> None:
    if not SETAD_PLAYWRIGHT_ENABLED:
        result["playwright_enabled"] = False
        result["browser_status"] = "not_enabled"
        return

    result["playwright_enabled"] = True
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception as exc:
        result["browser_status"] = "dependency_missing"
        result["browser_error"] = f"Playwright is not installed or not importable: {exc}"
        return

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = await browser.new_page(locale="fa-IR")
            response = await page.goto(source_url, wait_until="domcontentloaded", timeout=int(SETAD_ACCESS_TEST_TIMEOUT_SECONDS * 1000))
            title = await page.title()
            body_text = ""
            try:
                body_text = await page.locator("body").inner_text(timeout=5000)
            except Exception:
                body_text = await page.content()
            await browser.close()

        indicators = detect_login_indicators(body_text[:8000])
        result["browser_status"] = "success"
        result["browser_http_status"] = response.status if response else None
        result["page_title"] = title
        result["browser_login_detected"] = indicators["login_detected"]
        result["browser_captcha_detected"] = indicators["captcha_detected"]
        result["browser_otp_detected"] = indicators["otp_detected"]
        result["login_detected"] = result.get("login_detected") or indicators["login_detected"]
        result["captcha_detected"] = result.get("captcha_detected") or indicators["captcha_detected"]
        result["otp_detected"] = result.get("otp_detected") or indicators["otp_detected"]
    except Exception as exc:
        result["browser_status"] = "failed"
        result["browser_error"] = str(exc)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": "Niroban API",
        "status": "running",
        "revision": "Rev 1E",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/me")
async def me(current_user: dict = Depends(require_user)) -> dict:
    return {
        "id": current_user.get("id"),
        "email": current_user.get("email"),
        "role": current_user.get("role"),
    }


@app.get("/opportunities")
async def list_opportunities(
    status: Optional[OpportunityStatus] = None,
    opportunity_type: Optional[OpportunityType] = None,
    region_priority: Optional[RegionPriority] = None,
    search: Optional[str] = Query(default=None, description="Search title, company, province, or keyword"),
    current_user: dict = Depends(require_user),
) -> list[dict]:
    params: dict[str, str] = {
        "select": "*",
        "order": "created_at.desc",
    }

    if status:
        params["status"] = f"eq.{status}"
    if opportunity_type:
        params["opportunity_type"] = f"eq.{opportunity_type}"
    if region_priority:
        params["region_priority"] = f"eq.{region_priority}"
    if search:
        safe_search = search.strip().replace("*", "")
        if safe_search:
            params["or"] = (
                f"(title.ilike.*{safe_search}*,"
                f"company_name.ilike.*{safe_search}*,"
                f"province.ilike.*{safe_search}*,"
                f"matched_keyword.ilike.*{safe_search}*)"
            )

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            supabase_table_url("tender_opportunities"),
            headers=supabase_headers(),
            params=params,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.post("/opportunities", status_code=201)
async def create_opportunity(payload: OpportunityCreate, current_user: dict = Depends(require_user)) -> dict:
    data = payload.model_dump(mode="json", exclude_none=True)

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            supabase_table_url("tender_opportunities"),
            headers=supabase_headers(prefer_return=True),
            json=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    created = response.json()
    return created[0] if created else {}


@app.patch("/opportunities/{opportunity_id}")
async def update_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdate,
    current_user: dict = Depends(require_user),
) -> dict:
    data = payload.model_dump(mode="json", exclude_none=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(
            supabase_table_url("tender_opportunities"),
            headers=supabase_headers(prefer_return=True),
            params={"id": f"eq.{opportunity_id}"},
            json=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    updated = response.json()
    if not updated:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return updated[0]


@app.delete("/opportunities/{opportunity_id}")
async def delete_opportunity(opportunity_id: str, current_user: dict = Depends(require_user)) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.delete(
            supabase_table_url("tender_opportunities"),
            headers=supabase_headers(),
            params={"id": f"eq.{opportunity_id}"},
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "deleted", "id": opportunity_id}


@app.get("/search-rules")
async def list_search_rules(active: Optional[bool] = True, current_user: dict = Depends(require_user)) -> list[dict]:
    params: dict[str, str] = {
        "select": "*",
        "order": "created_at.desc",
    }
    if active is not None:
        params["active"] = f"eq.{str(active).lower()}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            supabase_table_url("tender_search_rules"),
            headers=supabase_headers(),
            params=params,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.post("/search-rules", status_code=201)
async def create_search_rule(payload: SearchRuleCreate, current_user: dict = Depends(require_user)) -> dict:
    data = payload.model_dump(mode="json", exclude_none=True)

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            supabase_table_url("tender_search_rules"),
            headers=supabase_headers(prefer_return=True),
            json=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    created = response.json()
    return created[0] if created else {}


@app.post("/setad/access-test", status_code=201)
async def setad_access_test(payload: SetadAccessTestCreate, current_user: dict = Depends(require_user)) -> dict:
    """Rev 1E: test whether the cloud backend can reach the Setad Iran login site.

    This endpoint does not store Setad credentials and does not bypass CAPTCHA/OTP.
    It only verifies network/page accessibility and records the result in tender_scan_logs.
    """
    source_url = str(payload.source_url or SETAD_DEFAULT_URL).strip() or SETAD_DEFAULT_URL
    result: dict[str, Any] = {
        "revision": "Rev 1E",
        "source_url": source_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reachable": False,
        "http_status": None,
        "final_url": None,
        "login_detected": False,
        "captcha_detected": False,
        "otp_detected": False,
        "playwright_enabled": False,
        "browser_status": "not_requested",
        "message_fa": "",
    }

    try:
        async with httpx.AsyncClient(
            timeout=SETAD_ACCESS_TEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 Niroban-Setad-Access-Test/1.0",
                "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6",
            },
        ) as client:
            response = await client.get(source_url)
        body_text = response.text[:12000]
        indicators = detect_login_indicators(body_text)
        result.update(
            {
                "reachable": response.status_code < 500,
                "http_status": response.status_code,
                "final_url": str(response.url),
                "content_type": response.headers.get("content-type"),
                "content_length": len(response.content),
                **indicators,
            }
        )
    except Exception as exc:
        result["http_error"] = str(exc)

    if payload.run_browser_check:
        await run_optional_playwright_check(source_url, result)

    result["message_fa"] = create_setad_message_fa(result)
    saved_log = await save_setad_access_scan_log(result, current_user)
    result["scan_log"] = saved_log
    return result


@app.get("/scan-logs")
async def list_scan_logs(
    limit: int = Query(default=10, ge=1, le=50),
    status: Optional[ScanStatus] = None,
    current_user: dict = Depends(require_user),
) -> list[dict]:
    params: dict[str, str] = {
        "select": "*",
        "order": "scan_date.desc,created_at.desc",
        "limit": str(limit),
    }
    if status:
        params["status"] = f"eq.{status}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            supabase_table_url("tender_scan_logs"),
            headers=supabase_headers(),
            params=params,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.post("/scan-logs", status_code=201)
async def create_scan_log(payload: ScanLogCreate, current_user: dict = Depends(require_user)) -> dict:
    data = payload.model_dump(mode="json", exclude_none=True)
    if data.get("status") in {"success", "failed", "login_required", "captcha_required"} and not data.get("finished_at"):
        data["finished_at"] = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            supabase_table_url("tender_scan_logs"),
            headers=supabase_headers(prefer_return=True),
            json=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    created = response.json()
    return created[0] if created else {}


@app.patch("/scan-logs/{scan_log_id}")
async def update_scan_log(
    scan_log_id: str,
    payload: ScanLogUpdate,
    current_user: dict = Depends(require_user),
) -> dict:
    data = payload.model_dump(mode="json", exclude_none=True)
    if data.get("status") in {"success", "failed", "login_required", "captcha_required"} and not data.get("finished_at"):
        data["finished_at"] = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(
            supabase_table_url("tender_scan_logs"),
            headers=supabase_headers(prefer_return=True),
            params={"id": f"eq.{scan_log_id}"},
            json=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    updated = response.json()
    if not updated:
        raise HTTPException(status_code=404, detail="Scan log not found")
    return updated[0]
