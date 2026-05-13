"""Niroban Rev 1D: semi-automatic Setad Iran scanner.

This script opens https://setadiran.ir/setad/cms in a visible Chromium browser.
The user logs in manually. Captcha/OTP must be completed by the user.
The script then tries a best-effort keyword scan and saves JSON output.

Because the website is private and may change, selectors may need tuning in
setad_config.json after the first real run.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "setad_config.json"
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SNAPSHOT_DIR = BASE_DIR / "snapshots"
USER_DATA_DIR = BASE_DIR / "storage" / "setad_user_data"

for folder in [OUTPUT_DIR, SCREENSHOT_DIR, SNAPSHOT_DIR, USER_DATA_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit("Missing setad_config.json. Copy setad_config.example.json to setad_config.json first.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_name(value: str) -> str:
    value = re.sub(r"[^\w\u0600-\u06FF-]+", "_", value, flags=re.UNICODE)
    return value.strip("_")[:80] or "snapshot"


def click_first_visible_text(page, labels: list[str]) -> bool:
    for label in labels:
        candidates = [
            page.get_by_text(label, exact=False),
            page.locator(f"text={label}"),
        ]
        for locator in candidates:
            try:
                if locator.count() > 0:
                    locator.first.click(timeout=2500)
                    page.wait_for_load_state("networkidle", timeout=8000)
                    return True
            except Exception:
                continue
    return False


def fill_search_box(page, keyword: str, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 8)
            for index in range(count):
                item = locator.nth(index)
                if item.is_visible(timeout=800):
                    item.click(timeout=1000)
                    item.fill(keyword, timeout=1500)
                    item.press("Enter", timeout=1500)
                    page.wait_for_timeout(2500)
                    return True
        except Exception:
            continue
    return False


def extract_candidates(page, config: dict[str, Any], opportunity_type: str, keyword_fa: str, keyword_en: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    selectors = config.get("result_container_selectors", [])
    regions = config.get("priority_regions", [])

    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 80)
        except Exception:
            continue

        for index in range(count):
            try:
                text = clean_text(locator.nth(index).inner_text(timeout=1000))
            except Exception:
                continue

            if len(text) < 8:
                continue

            lowered = text.lower()
            if keyword_fa not in text and keyword_en.lower() not in lowered:
                continue

            matched_region = next((region for region in regions if region in text), "")
            region_priority = "semnan" if "سمنان" in text or "Semnan" in text else "south" if matched_region else "other"

            title = text[:220]
            candidates.append(
                {
                    "customer_name": config.get("customer_name", "Gostaresh Energy"),
                    "title": title,
                    "opportunity_type": opportunity_type,
                    "company_name": "",
                    "province": matched_region,
                    "region_priority": region_priority,
                    "matched_keyword": keyword_fa,
                    "source_url": page.url,
                    "notes": f"Captured by Niroban Rev 1D semi-automatic scanner. Full row text: {text[:800]}",
                    "status": "new",
                }
            )
    return candidates


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = f"{item.get('title','')}|{item.get('opportunity_type','')}|{item.get('matched_keyword','')}".lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def main() -> int:
    config = load_config()
    start_url = config["start_url"]
    all_candidates: list[dict[str, Any]] = []
    start_time = datetime.now(timezone.utc)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
            slow_mo=80,
        )
        page = browser.new_page()
        page.goto(start_url, wait_until="domcontentloaded", timeout=60000)

        print("\nNiroban Rev 1D semi-automatic scanner")
        print(f"Opened: {start_url}")
        print("Log in manually. Complete captcha/OTP if required.")
        input("After the website dashboard/search page is visible, press ENTER here to continue...")

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        page.screenshot(path=str(SCREENSHOT_DIR / f"login_ready_{timestamp}.png"), full_page=True)

        opportunity_types = config.get("opportunity_types", [])
        keywords = config.get("keywords", [])
        search_selectors = config.get("search_input_selectors", [])

        for opp_type in opportunity_types:
            opp_value = opp_type["value"]
            labels = opp_type.get("labels", [])
            print(f"\n--- Opportunity type: {opp_value} / {labels} ---")
            clicked = click_first_visible_text(page, labels)
            if not clicked:
                print("Could not auto-click this opportunity type. You may navigate manually in the browser.")
                input("Navigate to the correct section, then press ENTER to continue...")

            for kw in keywords:
                keyword_fa = kw.get("fa", "")
                keyword_en = kw.get("en", "")
                search_term = keyword_fa or keyword_en
                print(f"Searching keyword: {search_term}")

                searched = fill_search_box(page, search_term, search_selectors)
                if not searched:
                    print("Could not find a search input automatically.")
                    print(f"Please search manually for: {search_term}")
                    input("After results are visible, press ENTER to capture this page...")

                page.wait_for_timeout(1500)
                tag = f"{timestamp}_{opp_value}_{safe_name(search_term)}"
                page.screenshot(path=str(SCREENSHOT_DIR / f"{tag}.png"), full_page=True)
                text = clean_text(page.locator("body").inner_text(timeout=5000))
                (SNAPSHOT_DIR / f"{tag}.txt").write_text(text, encoding="utf-8")

                candidates = extract_candidates(page, config, opp_value, keyword_fa, keyword_en)
                print(f"Captured candidates: {len(candidates)}")
                all_candidates.extend(candidates)

        browser.close()

    unique_candidates = dedupe(all_candidates)
    opportunities_path = OUTPUT_DIR / "setad_opportunities.json"
    scan_log_path = OUTPUT_DIR / "setad_scan_log.json"

    opportunities_path.write_text(json.dumps(unique_candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    scan_log = {
        "customer_name": config.get("customer_name", "Gostaresh Energy"),
        "scan_date": datetime.now().date().isoformat(),
        "source_name": config.get("source_name", "سامانه ستاد ایران"),
        "source_url": start_url,
        "scan_mode": "semi_automatic",
        "status": "success",
        "checked_opportunity_types": [item["value"] for item in opportunity_types],
        "checked_keywords": [item.get("en") or item.get("fa") for item in keywords],
        "checked_regions": ["south", "semnan", "all_iran"],
        "total_found": len(unique_candidates),
        "new_opportunities": len(unique_candidates),
        "relevant_opportunities": len(unique_candidates),
        "notes": "Generated by local Rev 1D semi-automatic Playwright scanner. Review captured opportunities before submitting proposals.",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    scan_log_path.write_text(json.dumps(scan_log, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nScan finished.")
    print(f"Opportunities: {opportunities_path}")
    print(f"Scan log: {scan_log_path}")
    print(f"Start time UTC: {start_time.isoformat()}")
    print(f"Total unique candidates: {len(unique_candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
