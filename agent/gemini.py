import time
import json
import re
import logging
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)

def wait_for_new_gemini_response(page: Page, previous_message_count: int, timeout: int = 120, stable_seconds: float = 3.0):
    """
    Waits for a NEW Gemini response by waiting until the message count increases.
    Then, polls the latest message-content text until it remains stable for stable_seconds.
    Raises TimeoutError if no new stable response is found within `timeout` seconds.
    """
    logger.info("Ожидание нового ответа от Gemini...")
    start_time = time.time()

    # 1. Wait for a new message block to appear
    new_message_appeared = False
    while time.time() - start_time < timeout:
        current_count = page.locator("message-content").count()
        if current_count > previous_message_count:
            new_message_appeared = True
            break
        page.wait_for_timeout(500)

    if not new_message_appeared:
        raise TimeoutError(f"Превышено время ожидания начала ответа от Gemini ({timeout} сек).")

    # 2. Wait for the new message text to stabilize
    logger.info("Новое сообщение появилось. Ожидание стабилизации текста...")
    last_text = None
    stable_start = None

    while time.time() - start_time < timeout:
        responses = page.locator("message-content")
        current_text = responses.nth(-1).inner_text()

        if current_text and current_text == last_text:
            if stable_start is None:
                stable_start = time.time()
            elif time.time() - stable_start >= stable_seconds:
                return current_text
        else:
            last_text = current_text
            stable_start = None

        page.wait_for_timeout(1000)

    raise TimeoutError(f"Превышено время ожидания стабилизации ответа от Gemini ({timeout} сек).")

def get_initial_prompt(page: Page, product_link: str) -> str:
    """
    Sends the initial request to Gemini to get a video script/prompt.
    """
    logger.info(f"Отправляем запрос на сценарий для товара: {product_link}")
    page.goto("https://gemini.google.com/app")

    input_box = page.locator("rich-textarea div[contenteditable='true']")
    input_box.wait_for(state="visible")

    previous_count = page.locator("message-content").count()

    prompt = f"""
Действуй как эксперт по вирусному контенту в соцсетях. Твоя задача — проанализировать текущие тренды TikTok и Instagram Reels для этой категории товаров на основе своих знаний, и создать сценарий для видео, который гарантированно соберет просмотры.
Товар находится по этой ссылке: {product_link}.

Изучи, какие форматы, хуки (зацепки) и визуальные стили сейчас популярны для подобных товаров. Напиши детальный сценарий и промпт для AI-генератора видео (Google Vids / Runway и тд).
Промпт для генератора должен быть на английском языке.

ОБЯЗАТЕЛЬНО ответь ТОЛЬКО в формате JSON, без какого-либо дополнительного текста, приветствий или форматирования markdown (без ```json).
Структура JSON должна быть строго такой:
{{
  "initial_prompt": "Твой детальный визуальный промпт на английском для генератора видео",
  "creative_angle": "Выбранный тренд/креативный угол (на русском)",
  "target_audience": "Целевая аудитория (на русском)",
  "hook": "Трендовый хук/зацепка для первых 3 секунд (на русском)",
  "cta": "Призыв к действию (на русском)"
}}
"""

    input_box.fill(prompt)
    input_box.press("Enter")

    response_text = wait_for_new_gemini_response(page, previous_count)
    logger.info("Получен изначальный промпт от Gemini.")
    return response_text

def wait_for_file_attachment_ready(page: Page, timeout: int = 60):
    """
    Waits for the file to finish uploading. If exact selectors are unknown,
    it uses a conservative fallback delay.
    """
    logger.info("Ожидание завершения загрузки файла...")

    try:
        chip = page.locator("attachment-chip, div[aria-label*='file']")
        if chip.count() > 0:
             chip.first.wait_for(state="visible", timeout=10000)
    except Exception:
        logger.warning("Индикатор загрузки не найден. Используем резервное ожидание.")

    page.wait_for_timeout(10000)
    logger.info("Файл должен быть загружен.")

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

    wait_for_file_attachment_ready(page)

    previous_count = page.locator("message-content").count()

    eval_prompt = """
Посмотри это сгенерированное видео для нашего Reels/TikTok. Действуй как строгий продюсер вирусного контента.
Оцени видео: цепляет ли оно внимание с первой секунды? Понятен ли товар? Подходит ли оно под современные тренды коротких видео?
Если видео недостаточно динамичное или не цепляет, напиши улучшенный, более детальный промпт на английском языке для генерации лучшей версии этого видео. Исправь ошибки прошлой генерации.

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

    response_text = wait_for_new_gemini_response(page, previous_count)
    logger.info("Оценка получена.")
    return response_text

def _extract_json_string(text: str) -> str:
    """
    Attempts to extract a JSON string from the response, ignoring surrounding text or markdown fences.
    Handles nested braces robustly by targeting the first opening brace and the last closing brace
    if markdown fences fail.
    """
    text = text.strip()

    # Try to find markdown json block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    # Attempt to extract using regex to find the outermost JSON structure
    # This regex looks for an opening brace, followed by valid json content (including nested braces), followed by a closing brace.
    # It avoids grabbing stray braces outside the main JSON body by requiring string keys.
    match = re.search(r'(\{(?:\s*".*?"\s*:[\s\S]*?)+\})', text)
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
