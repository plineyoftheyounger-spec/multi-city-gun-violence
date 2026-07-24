"""
fetch_gva.py
────────────
Playwright automation against gunviolencearchive.org/query, generalized from
orlando_gun_violence/06_auto_update.py:download_gva_csv() to take state/city/
date-range as parameters instead of hardcoding Orlando/Florida.
"""

import logging
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

log = logging.getLogger(__name__)


def download_gva_csv(state: str, city: str, start: date, end: date,
                      out_path: Path, debug_dir: Path) -> Path:
    """Automate a GVA state+city+date-range query and download the result CSV."""
    start_str = start.strftime("%m/%d/%Y")
    end_str   = end.strftime("%m/%d/%Y")

    log.info(f"GVA query: {state}/{city}  {start_str} to {end_str}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()

        try:
            page.goto("https://www.gunviolencearchive.org/query",
                      wait_until="networkidle", timeout=30_000)

            # ── Location filter ───────────────────────────────────────────────
            page.evaluate("document.querySelector('a.filter-dropdown-trigger').click()")
            page.wait_for_timeout(600)
            page.evaluate("document.querySelector('a[data-value=\"IncidentLocation\"]').click()")
            page.wait_for_timeout(2_000)

            page.locator('[name$="[state][select]"]').first.select_option(label=state)
            page.wait_for_timeout(300)
            page.locator('[name$="[city_county][city][textfield]"]').first.fill(city)

            # ── Date filter ───────────────────────────────────────────────────
            page.evaluate("document.querySelector('a.filter-dropdown-trigger').click()")
            page.wait_for_timeout(600)
            page.evaluate("document.querySelector('a[data-value=\"IncidentDate\"]').click()")
            page.wait_for_timeout(2_000)

            page.locator('[name$="[date-from]"]').last.fill(start_str)
            page.locator('[name$="[date-to]"]').last.fill(end_str)

            # ── Search ────────────────────────────────────────────────────────
            page.locator("#edit-actions-execute").click()
            page.wait_for_load_state("networkidle", timeout=30_000)
            log.info(f"Search returned: {page.url}")

            # ── Trigger export ────────────────────────────────────────────────
            page.locator('a[href="#"]').first.click()
            page.wait_for_load_state("networkidle", timeout=60_000)

            if "export-finished" not in page.url:
                _save_debug(page, debug_dir, "export_redirect_failed")
                raise RuntimeError(f"Unexpected URL after export click: {page.url}")

            # ── Download ──────────────────────────────────────────────────────
            dl_link = page.locator('a[href*="export-finished/download"]').first
            dl_href = dl_link.get_attribute("href")
            if not dl_href:
                _save_debug(page, debug_dir, "no_download_link")
                raise RuntimeError("Download link not found on export-finished page")

            dl_url = f"https://www.gunviolencearchive.org{dl_href}"
            log.info(f"Downloading: {dl_url}")

            with page.expect_download(timeout=60_000) as dl_info:
                dl_link.click()
            dl = dl_info.value
            dl.save_as(str(out_path))
            log.info(f"Saved to: {out_path}")

        except Exception:
            _save_debug(page, debug_dir, "error")
            browser.close()
            raise

        browser.close()
    return out_path


def _save_debug(page, debug_dir: Path, label: str):
    debug_dir.mkdir(parents=True, exist_ok=True)
    path = debug_dir / f"{label}_{date.today()}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        log.info(f"Debug screenshot: {path}")
    except Exception:
        pass
