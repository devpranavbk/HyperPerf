import json
from playwright.sync_api import sync_playwright
import os


# CONFIGURABLE SECTION
# SITE_URL = "https://demoapp-5owbzfpse-dev-pranavs-projects.vercel.app/"
# USERNAME = "admin"
# PASSWORD = "password"
SITE_URL = os.getenv("SITE_URL", "https://demoapp-ashen.vercel.app/")
USERNAME = os.getenv("USERNAME", "admin")
PASSWORD = os.getenv("PASSWORD", "password")


USERNAME_SELECTOR = 'input[placeholder="Username"]'
PASSWORD_SELECTOR = 'input[placeholder="Password"]'
LOGIN_BUTTON_SELECTOR = 'button[type="submit"], button:has-text("Login")'
HOME_PAGE_SELECTOR = 'h1, .home, .dashboard'  # Change to a unique selector on your home page
OUTPUT_FILE = "api_calls_login_and_home.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    api_calls = []

    def log_request(request):
        # For POST requests, capture URL and body
        if request.method == "POST":
            try:
                post_data = request.post_data
            except Exception:
                post_data = None
            print("POST request:", request.url)
            print("POST data:", post_data)
            api_calls.append({"url": request.url, "method": "POST", "post_data": post_data})
        else:
            api_calls.append({"url": request.url, "method": request.method})

    page.on("request", log_request)
    page.goto(SITE_URL)
    # page.get_by_text("Visit Site").click()
    page.fill(USERNAME_SELECTOR, USERNAME)
    page.fill(PASSWORD_SELECTOR, PASSWORD)
    page.click(LOGIN_BUTTON_SELECTOR)
    page.wait_for_selector(HOME_PAGE_SELECTOR, timeout=15000)
    # Optionally, wait a bit more for post-login API calls
    page.wait_for_timeout(3000)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(api_calls, f, indent=2)
    print(f"Extracted {len(api_calls)} API calls. Output written to {OUTPUT_FILE}")
    browser.close()
