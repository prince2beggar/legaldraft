"""
Capture browser screenshots of updated Tax & VAT workspace.
"""
import time

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # Navigate to Tax workspace
        page.goto("http://127.0.0.1:8000/tax", wait_until="networkidle")
        time.sleep(1.5)

        # 1. Capture Income Tax view with new fields & saved table
        page.screenshot(path="storage/screenshots/tax_workspace_updated_income.png", full_page=False)

        # 2. Scroll to saved returns history table
        saved_section = page.locator("#savedReturnsSection")
        if saved_section.count() > 0:
            saved_section.scroll_into_view_if_needed()
            time.sleep(0.5)
            page.screenshot(path="storage/screenshots/tax_workspace_saved_history.png", full_page=False)

        # 3. Switch to VAT tab
        page.locator("#tabBtnVat").click()
        time.sleep(1)
        page.screenshot(path="storage/screenshots/tax_workspace_updated_vat.png", full_page=False)

        browser.close()
        print("Screenshots captured successfully.")

if __name__ == "__main__":
    main()
