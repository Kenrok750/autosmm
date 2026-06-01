import time
import os
from playwright.sync_api import Page, expect

def generate_video(page: Page, prompt: str, iteration: int) -> str:
    """
    Navigates to Google Vids, inputs the prompt, generates the video,
    downloads it, and returns the path to the downloaded file.
    """
    print(f"Генерация видео в Google Vids (итерация {iteration})...")

    # 1. Navigate to Google Vids creation page
    # The exact URL or process to create a new video might vary.
    # Typically, you might go to docs.google.com/video or a similar workspace URL.
    page.goto("https://docs.google.com/video") # Placeholder URL, might need adjustment
    time.sleep(5)

    # Look for "Create new" or "Blank" button
    # These selectors are highly speculative and WILL need to be updated based on the actual Google Vids DOM.
    try:
        # Click 'Blank' or 'New' to start a new project
        new_btn = page.locator("div[aria-label='Blank'], div[aria-label='Create new video']")
        if new_btn.count() > 0:
             new_btn.first.click()
        else:
             print("Кнопка 'Создать новое' не найдена. Возможно, мы уже в редакторе.")
    except Exception as e:
        print(f"Ошибка при попытке создать новое видео: {e}")

    time.sleep(5)

    # 2. Enter the prompt
    # In Vids, there is likely a text box for the AI prompt ("Help me create...")
    try:
        # Find the input box for AI prompt
        prompt_input = page.locator("textarea[placeholder*='prompt'], div[contenteditable='true']")
        prompt_input.wait_for(state="visible", timeout=10000)
        prompt_input.fill(prompt)

        # Find and click the generate button
        generate_btn = page.locator("button:has-text('Generate'), button:has-text('Create')")
        generate_btn.click()

    except Exception as e:
        print(f"Не удалось ввести промпт или нажать 'Генерировать': {e}")
        # Need manual intervention or selector update
        print("Ожидаем 30 секунд для ручной корректировки...")
        time.sleep(30)

    # 3. Wait for generation
    print("Ожидание генерации видео (это может занять несколько минут)...")
    # We wait for some indicator that generation is complete.
    # This could be a progress bar disappearing, or a timeline appearing.
    page.wait_for_timeout(60000) # Wait at least 60 seconds. In reality, might need a dynamic check.

    # 4. Export / Download
    # Look for the export button
    video_filename = f"generated_video_iter_{iteration}.mp4"
    video_path = os.path.abspath(video_filename)

    try:
        # Find export menu
        export_menu_btn = page.locator("button:has-text('Export'), button[aria-label='Export options']")
        if export_menu_btn.count() > 0:
            export_menu_btn.click()
            time.sleep(1)

            # Find MP4 download option
            download_mp4_btn = page.locator("menuitem:has-text('MP4'), div:has-text('Download MP4')")

            # Start waiting for the download
            with page.expect_download(timeout=120000) as download_info:
                download_mp4_btn.click()

            download = download_info.value
            download.save_as(video_path)
            print(f"Видео успешно скачано: {video_path}")
            return video_path
        else:
             print("Кнопка 'Экспорт' не найдена.")

    except Exception as e:
        print(f"Ошибка при попытке скачать видео: {e}")

    # Fallback if download fails: just return a placeholder or wait for manual download
    print("Автоматическое скачивание не удалось. Пожалуйста, скачайте видео вручную.")
    print(f"Сохраните его как '{video_filename}' в папке скрипта.")
    print("Ожидание 60 секунд...")
    time.sleep(60)

    if os.path.exists(video_path):
        return video_path
    else:
        raise Exception("Файл видео не найден. Цикл прерван.")
