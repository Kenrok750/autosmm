import time
import os
import logging
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)

def generate_video(page: Page, prompt: str, iteration: int, output_video_path: str) -> str:
    """
    Navigates to Google Vids, inputs the prompt, generates the video,
    downloads it, and saves it to output_video_path.
    """
    logger.info(f"Генерация видео в Google Vids (итерация {iteration})...")

    page.goto("https://docs.google.com/video")
    time.sleep(5)

    try:
        new_btn = page.locator("div[aria-label='Blank'], div[aria-label='Create new video']")
        if new_btn.count() > 0:
             new_btn.first.click()
        else:
             logger.warning("Кнопка 'Создать новое' не найдена. Возможно, мы уже в редакторе.")
    except Exception as e:
        logger.error(f"Ошибка при попытке создать новое видео: {e}")

    time.sleep(5)

    try:
        prompt_input = page.locator("textarea[placeholder*='prompt'], div[contenteditable='true']")
        prompt_input.wait_for(state="visible", timeout=10000)
        prompt_input.fill(prompt)

        generate_btn = page.locator("button:has-text('Generate'), button:has-text('Create')")
        generate_btn.click()

    except Exception as e:
        logger.error(f"Не удалось ввести промпт или нажать 'Генерировать': {e}")
        logger.info("Ожидаем 30 секунд для ручной корректировки...")
        time.sleep(30)

    logger.info("Ожидание генерации видео (это может занять несколько минут)...")
    page.wait_for_timeout(60000)

    try:
        export_menu_btn = page.locator("button:has-text('Export'), button[aria-label='Export options']")
        if export_menu_btn.count() > 0:
            export_menu_btn.click()
            time.sleep(1)

            download_mp4_btn = page.locator("menuitem:has-text('MP4'), div:has-text('Download MP4')")

            with page.expect_download(timeout=120000) as download_info:
                download_mp4_btn.click()

            download = download_info.value
            download.save_as(output_video_path)
            logger.info(f"Видео успешно скачано: {output_video_path}")
            return output_video_path
        else:
             logger.warning("Кнопка 'Экспорт' не найдена.")

    except Exception as e:
        logger.error(f"Ошибка при попытке скачать видео: {e}")

    logger.info("Автоматическое скачивание не удалось. Пожалуйста, скачайте видео вручную.")
    logger.info(f"Сохраните его по пути '{output_video_path}'. Ожидание 60 секунд...")
    time.sleep(60)

    if os.path.exists(output_video_path):
        return output_video_path
    else:
        raise Exception("Файл видео не найден. Цикл прерван.")
