"""Open a dashboard from file:// in headless Chrome, fail on console errors, screenshot every tab.

Usage: python tools/screenshot.py dashboard/index.html reports/figures/dashboard
Writes <prefix>_<tab>.png for each element matching `[data-tab]` and exits non-zero
if the page logs a console error or an uncaught exception.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def launch(p):
    # Prefer the locally installed Chrome; fall back to Playwright's bundled Chromium (CI).
    for kwargs in ({"channel": "chrome"}, {"channel": "msedge"}, {}):
        try:
            return p.chromium.launch(headless=True, **kwargs)
        except Exception:  # noqa: BLE001 - try the next browser
            continue
    raise RuntimeError("no Chromium-based browser available for screenshots")


def main(html_path: str, prefix: str) -> int:
    url = Path(html_path).resolve().as_uri()
    out = Path(prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("[data-tab]")
        page.wait_for_timeout(1500)
        tabs = page.query_selector_all("[data-tab]")
        names = [t.get_attribute("data-tab") for t in tabs]
        for name in names:
            page.click(f"[data-tab='{name}']")
            page.wait_for_timeout(900)
            page.screenshot(path=f"{out}_{name}.png", full_page=True)
            print(f"screenshot: {out}_{name}.png")
        browser.close()
    if errors:
        print("console errors:\n  " + "\n  ".join(errors))
        return 1
    print(f"screenshot: OK - {len(names)} tab(s), no console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
