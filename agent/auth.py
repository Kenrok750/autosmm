import os
import json
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"

def perform_auth():
    """
    Launches a visible browser for the user to log in manually.
    Saves the session state (cookies, local storage) to a file.
    """
    print("=" * 50)
    print("ВНИМАНИЕ: Сейчас откроется окно браузера.")
    print("Пожалуйста, войдите в свой аккаунт Google.")
    print("Решите все капчи, если они появятся.")
    print("Убедитесь, что у вас есть доступ к Gemini Advanced и Google Vids.")
    print("Когда закончите авторизацию, ПРОСТО ЗАКРОЙТЕ ОКНО БРАУЗЕРА.")
    print("=" * 50)

    with sync_playwright() as p:
        # We need a non-headless browser so the user can interact
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://accounts.google.com/signin")

        # We wait for the user to close the page manually.
        # This gives them infinite time to log in and pass 2FA/Captchas.
        try:
            page.wait_for_event("close", timeout=0)
        except Exception as e:
            pass # Handle timeout or manual close gracefully

        print("Окно закрыто. Сохраняем сессию...")

        # Save state to file
        context.storage_state(path=STATE_FILE)
        browser.close()
        print(f"Сессия успешно сохранена в файл '{STATE_FILE}'.")
        print("Теперь вы можете запускать main.py!")

def get_browser_context(playwright, headless=False):
    """
    Returns a browser context. If state.json exists, it loads it.
    Otherwise, it prompts the user to run auth.py first.
    """
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(f"Файл '{STATE_FILE}' не найден. Пожалуйста, сначала запустите 'python agent/auth.py' для авторизации.")

    browser = playwright.chromium.launch(headless=headless)
    # Load the state
    context = browser.new_context(storage_state=STATE_FILE)
    return browser, context

if __name__ == "__main__":
    perform_auth()
