import time
from playwright.sync_api import Page, expect

def wait_for_gemini_response(page: Page):
    """
    Waits for Gemini to finish generating its response.
    This is tricky because the UI doesn't have a simple "done" state.
    We typically look for the 'Generating...' indicator to disappear or for the send button to become active again.
    """
    print("Ожидание ответа от Gemini...")
    # Wait for the send button to be enabled (or not loading)
    # The actual selectors change frequently.
    # Current strategy: wait for the stop button to disappear or the send button to be visible and enabled.

    # Wait a bit for the generation to actually start
    time.sleep(3)

    # Wait until the "Stop generating" button is gone, or a similar indicator.
    # Alternatively, just wait for the last message to finish rendering.
    # A generic approach is to wait for network idle, but Gemini uses WebSockets/SSE.
    # Let's wait for a reasonable time and check if the input is enabled.
    page.wait_for_timeout(10000) # Wait 10 seconds as a baseline

    # Try to find the latest response text
    responses = page.locator("message-content")
    if responses.count() > 0:
        latest_response = responses.nth(-1).inner_text()
        return latest_response
    return "Не удалось получить ответ. Проверьте селекторы."

def get_initial_prompt(page: Page, product_link: str) -> str:
    """
    Sends the initial request to Gemini to get a video script/prompt.
    """
    print(f"Отправляем запрос на сценарий для товара: {product_link}")
    page.goto("https://gemini.google.com/app")

    # Wait for the input field to be ready
    input_box = page.locator("rich-textarea div[contenteditable='true']")
    input_box.wait_for(state="visible")

    prompt = f"Напиши детальный сценарий и промпт для генерации короткого вирального Reels (видео) для этого товара: {product_link}. Промпт должен быть на английском языке, чтобы я мог скормить его генератору видео. В ответе выдай ТОЛЬКО сам промпт на английском, без лишних слов."

    input_box.fill(prompt)
    input_box.press("Enter")

    response_text = wait_for_gemini_response(page)
    print("Получен изначальный промпт от Gemini.")
    return response_text

def evaluate_video(page: Page, video_path: str) -> str:
    """
    Uploads a video to Gemini and asks for evaluation and a new prompt.
    """
    print(f"Загружаем видео на оценку: {video_path}")

    # Ensure we are on the page and the input is visible
    input_box = page.locator("rich-textarea div[contenteditable='true']")
    input_box.wait_for(state="visible")

    # Upload the video file
    # Note: Gemini file upload might use a file input element that is hidden.
    # We need to find the <input type="file"> element and use set_input_files.
    file_input = page.locator("input[type='file']")
    if file_input.count() > 0:
         file_input.first.set_input_files(video_path)
    else:
        print("Не удалось найти поле для загрузки файла в Gemini! Возможно, изменился интерфейс.")
        # Alternatively, we could try to click the upload button and wait for the file chooser event.
        with page.expect_file_chooser() as fc_info:
            page.locator("button[aria-label='Upload image or file']").click() # Adjust selector if needed
        file_chooser = fc_info.value
        file_chooser.set_files(video_path)

    # Wait for upload to complete (this can take a while for video)
    print("Ожидание загрузки файла...")
    time.sleep(10) # Adjust based on typical upload speeds

    eval_prompt = "Посмотри это сгенерированное видео. Оцени его виральность и качество по шкале от 1 до 10. Затем напиши улучшенный, более детальный промпт на английском языке для генерации лучшей версии этого видео. Выдай оценку и новый промпт."
    input_box.fill(eval_prompt)
    input_box.press("Enter")

    response_text = wait_for_gemini_response(page)
    print(f"Оценка и новый промпт получены:\n{response_text[:200]}...") # Print a snippet
    return response_text

def extract_prompt_from_response(response_text: str) -> str:
    """
    Tries to extract just the english prompt from Gemini's response,
    in case it outputs extra text.
    """
    # Simple extraction logic: look for text that looks like a prompt.
    # Since we asked it to output ONLY the prompt, we might just return the whole thing,
    # but for safety, let's assume it might still add context.
    # A more robust solution would ask Gemini to wrap the prompt in XML tags like <prompt></prompt>
    # and use regex to extract it.

    # For now, we will return the text as is, assuming Gemini followed instructions.
    return response_text
