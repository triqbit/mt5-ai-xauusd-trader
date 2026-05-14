import os

from playwright.sync_api import sync_playwright


def verify_report_html():
    # Use absolute path for the generated HTML report
    report_path = os.path.abspath("reports/strategy_audit_report.html")

    if not os.path.exists(report_path):
        print(f"Error: Report not found at {report_path}")
        return

    # Use file:// protocol for Playwright
    url = f"file://{report_path}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Set viewport size for a clear dashboard view
        page.set_viewport_size({"width": 1280, "height": 2000})

        print(f"Navigating to {url}")
        page.goto(url)

        # Wait for the specific sections to be visible
        page.wait_for_selector("#stress-tests")
        page.wait_for_selector("#trade-patterns")

        # Take a screenshot of the top part (Executive Summary + KPIs + Stress Tests)
        screenshot_path = os.path.abspath("verification_report.png")
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()


if __name__ == "__main__":
    verify_report_html()
