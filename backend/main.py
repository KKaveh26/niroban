import os
from datetime import date, datetime, timezone
from typing import Literal, Optional

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
    version="1.0.0-rev1c",
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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": "Niroban API",
        "status": "running",
        "revision": "Rev 1C",
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
