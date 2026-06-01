import time
import json
import re
import logging
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)

def wait_for_gemini_response(page: Page, timeout: int = 120):
    """
    Waits for Gemini to finish generating its response by polling the latest
    message-content text until it remains stable for 3 seconds.
    Raises TimeoutError if no stable response is found within `timeout` seconds.
    """
    logger.info("Ожидание ответа от Gemini...")
    time.sleep(3) # Initial wait for generation to start

    start_time = time.time()
    last_text = None
    stable_start = None

    while time.time() - start_time < timeout:
        responses = page.locator("message-content")
        if responses.count() > 0:
            current_text = responses.nth(-1).inner_text()
            if current_text and current_text == last_text:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= 3.0:
                    return current_text
            else:
                last_text = current_text
                stable_start = None

        page.wait_for_timeout(1000) # Poll every 1 second

    raise TimeoutError(f"Превышено время ожидания ответа от Gemini ({timeout} сек).")

def get_initial_prompt(page: Page, product_link: str) -> str:
    """
    Sends the initial request to Gemini to get a video script/prompt.
    """
    logger.info(f"Отправляем запрос на сценарий для товара: {product_link}")
    page.goto("https://gemini.google.com/app")

    input_box = page.locator("rich-textarea div[contenteditable='true']")
    input_box.wait_for(state="visible")

    prompt = f"""
Напиши детальный сценарий и промпт для генерации короткого вирального Reels (видео) для этого товара: {product_link}.
Промпт должен быть на английском языке, чтобы я мог скормить его генератору видео.
ОБЯЗАТЕЛЬНО ответь ТОЛЬКО в формате JSON, без какого-либо дополнительного текста, приветствий или форматирования markdown (без ```json).
Структура JSON должна быть строго такой:
{{
  "initial_prompt": "Твой промпт на английском для генератора",
  "creative_angle": "Креативный угол (на русском)",
  "target_audience": "Целевая аудитория (на русском)",
  "hook": "Хук/зацепка (на русском)",
  "cta": "Призыв к действию (на русском)"
}}
"""

    input_box.fill(prompt)
    input_box.press("Enter")

    response_text = wait_for_gemini_response(page)
    logger.info("Получен изначальный промпт от Gemini.")
    return response_text

def evaluate_video(page: Page, video_path: str) -> str:
    """
    Uploads a video to Gemini and asks for evaluation and a new prompt.
    """
    logger.info(f"Загружаем видео на оценку: {video_path}")

    input_box = page.locator("rich-textarea div[contenteditable='true']")
    input_box.wait_for(state="visible")

    file_input = page.locator("input[type='file']")
    if file_input.count() > 0:
         file_input.first.set_input_files(video_path)
    else:
        logger.warning("Не удалось найти поле для загрузки файла в Gemini (input[type='file']). Пробуем кнопку.")
        with page.expect_file_chooser() as fc_info:
            page.locator("button[aria-label='Upload image or file']").click()
        file_chooser = fc_info.value
        file_chooser.set_files(video_path)

    logger.info("Ожидание загрузки файла...")
    time.sleep(10)

    eval_prompt = """
Посмотри это сгенерированное видео. Оцени его виральность и качество. Затем напиши улучшенный, более детальный промпт на английском языке для генерации лучшей версии этого видео.
ОБЯЗАТЕЛЬНО ответь ТОЛЬКО в формате JSON, без какого-либо дополнительного текста, приветствий или форматирования markdown (без ```json).
Структура JSON должна быть строго такой:
{
  "score": 0-10,
  "hook_score": 0-10,
  "product_visibility": 0-10,
  "viral_potential": 0-10,
  "visual_quality": 0-10,
  "clarity": 0-10,
  "cta_strength": 0-10,
  "reason": "Краткая причина оценки (на русском)",
  "problems": ["Проблема 1", "Проблема 2"],
  "improved_prompt": "Твой улучшенный промпт на английском",
  "next_strategy": "Следующая стратегия (на русском)"
}
"""
    input_box.fill(eval_prompt)
    input_box.press("Enter")

    response_text = wait_for_gemini_response(page)
    logger.info("Оценка получена.")
    return response_text

def _extract_json_string(text: str) -> str:
    """
    Attempts to extract a JSON string from the response, ignoring surrounding text or markdown fences.
    """
    text = text.strip()

    # Try to find markdown json block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    # Try to find just the outermost braces
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
         return match.group(1)

    return text

def extract_initial_prompt_from_response(response_text: str) -> dict:
    """
    Extracts the initial prompt JSON.
    """
    json_str = _extract_json_string(response_text)
    try:
        data = json.loads(json_str)
        if "initial_prompt" not in data:
            raise ValueError("Missing 'initial_prompt' key in JSON")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from response. Raw response: {response_text}. Error: {e}")

def extract_evaluation_from_response(response_text: str) -> dict:
    """
    Extracts the evaluation JSON and ensures improved_prompt is present.
    Returns the parsed JSON dictionary.
    """
    json_str = _extract_json_string(response_text)
    try:
        data = json.loads(json_str)
        if "improved_prompt" not in data:
            raise ValueError("Missing 'improved_prompt' key in JSON")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from evaluation response. Raw response: {response_text}. Error: {e}")

# Backward compatibility alias
extract_prompt_from_response = extract_evaluation_from_response
