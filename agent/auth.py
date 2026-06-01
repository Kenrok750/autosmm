import os
from playwright.sync_api import sync_playwright

from agent.config import STATE_FILE, HEADLESS

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
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://accounts.google.com/signin")

        input("\nКогда закончите авторизацию и увидите главную страницу Google, нажмите Enter в этой консоли...\n")

        print("Сохраняем сессию...")

        context.storage_state(path=STATE_FILE)
        browser.close()
        print(f"Сессия успешно сохранена в файл '{STATE_FILE}'.")
        print("Теперь вы можете запускать основной скрипт!")

def get_browser_context(playwright):
    """
    Returns a browser context. If state.json exists, it loads it.
    Otherwise, it prompts the user to run auth.py first.
    """
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(f"Файл '{STATE_FILE}' не найден. Пожалуйста, сначала запустите 'python -m agent.auth' для авторизации.")

    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(storage_state=STATE_FILE)
    return browser, context

if __name__ == "__main__":
    perform_auth()
