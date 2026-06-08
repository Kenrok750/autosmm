import sys
import json
import logging
import argparse
from playwright.sync_api import sync_playwright

from agent.auth import get_browser_context
from agent.gemini import get_initial_prompt, evaluate_video, extract_initial_prompt_from_response, extract_evaluation_from_response
from agent.vids import generate_video
from agent.config import MAX_ITERATIONS as DEFAULT_MAX_ITERATIONS
from agent.config import MIN_ACCEPTABLE_SCORE as DEFAULT_MIN_ACCEPTABLE_SCORE
from agent.storage import RunStorage

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def capture_screenshot(page, storage, filename):
    try:
        path = storage.get_screenshot_path(filename)
        page.screenshot(path=path)
        logger.info(f"Скриншот сохранен: {path}")
    except Exception as e:
        logger.error(f"Не удалось сохранить скриншот: {e}")

def notify_cb(progress_callback, msg_type, message, data=None):
    if progress_callback:
        progress_callback({"type": msg_type, "message": message, "data": data})
    if msg_type == "error":
        logger.error(message)
    else:
        logger.info(message)

def setup_run(product_url: str, progress_callback=None) -> RunStorage:
    """
    Initializes the run storage and gets the initial prompt from Gemini.
    Returns the initialized RunStorage object.
    """
    if not product_url:
        notify_cb(progress_callback, "error", "Ссылка не может быть пустой.")
        return None

    notify_cb(progress_callback, "info", "Инициализация хранилища запуска...")
    storage = RunStorage()
    storage.init_run(product_url)
    notify_cb(progress_callback, "info", f"Папка запуска: {storage.run_dir}")

    notify_cb(progress_callback, "info", "Подключение к Gemini...")
    with sync_playwright() as playwright:
        try:
            browser, context = get_browser_context(playwright)
        except FileNotFoundError as e:
            notify_cb(progress_callback, "error", str(e))
            storage.update_status("failed")
            return storage

        from playwright_stealth import stealth_sync
        gemini_page = context.new_page()
        stealth_sync(gemini_page)

        notify_cb(progress_callback, "info", "Анализ трендов и получение начального промпта от Gemini...")
        try:
            gemini_response = get_initial_prompt(gemini_page, product_url)
            prompt_data = extract_initial_prompt_from_response(gemini_response)

            storage.save_prompt("iter_00_initial.json", json.dumps(prompt_data, ensure_ascii=False, indent=2))
            notify_cb(progress_callback, "prompt", f"Сценарий готов", data=prompt_data)
            storage.update_status("ready_for_iteration")

        except Exception as e:
            notify_cb(progress_callback, "error", f"Ошибка при получении начального промпта: {e}")
            capture_screenshot(gemini_page, storage, "error_initial_prompt.png")
            storage.update_status("failed")

        gemini_page.wait_for_timeout(3000)
        browser.close()

    return storage

def run_single_iteration(storage: RunStorage, progress_callback=None):
    """
    Executes a single generation and evaluation iteration using the latest prompt.
    """
    iteration = len(storage.state.get("iterations", [])) + 1
    current_prompt = storage.get_latest_prompt()

    if not current_prompt:
        notify_cb(progress_callback, "error", "Не найден промпт для генерации. Прерывание.")
        storage.update_status("failed")
        return storage

    notify_cb(progress_callback, "info", f"=== ИТЕРАЦИЯ {iteration} ===")

    with sync_playwright() as playwright:
        try:
            browser, context = get_browser_context(playwright)
        except FileNotFoundError as e:
            notify_cb(progress_callback, "error", str(e))
            storage.update_status("failed")
            return storage

        from playwright_stealth import stealth_sync
        vids_page = context.new_page()
        gemini_page = context.new_page()
        stealth_sync(vids_page)
        stealth_sync(gemini_page)

        # Step 1: Generate video in Google Vids
        notify_cb(progress_callback, "info", f"Генерация видео в Google Vids...")
        try:
            vids_page.bring_to_front()
            output_video_path = storage.get_video_path(iteration)
            video_path = generate_video(vids_page, current_prompt, iteration, output_video_path)
            notify_cb(progress_callback, "video", f"Видео сгенерировано", data={"path": video_path})
        except Exception as e:
            notify_cb(progress_callback, "error", f"Ошибка при генерации видео: {e}")
            capture_screenshot(vids_page, storage, f"error_vids_iter_{iteration}.png")
            storage.update_status("failed")
            browser.close()
            return storage

        # Step 2: Evaluate video in Gemini
        notify_cb(progress_callback, "info", "Оценка видео в Gemini...")
        try:
            gemini_page.bring_to_front()
            gemini_eval_response = evaluate_video(gemini_page, video_path)
            eval_data = extract_evaluation_from_response(gemini_eval_response)

            storage.save_evaluation(f"iter_{iteration:02d}.json", eval_data)
            storage.record_iteration(iteration, current_prompt, video_path, eval_data)

            notify_cb(progress_callback, "eval", "Оценка получена", data=eval_data)

            current_prompt = eval_data["improved_prompt"]
            storage.save_prompt(f"iter_{iteration:02d}_improved.json", json.dumps({"improved_prompt": current_prompt}, ensure_ascii=False, indent=2))

            storage.update_status("awaiting_user_approval")

        except Exception as e:
             notify_cb(progress_callback, "error", f"Ошибка при оценке видео в Gemini: {e}")
             capture_screenshot(gemini_page, storage, f"error_gemini_eval_iter_{iteration}.png")
             storage.update_status("failed")

        gemini_page.wait_for_timeout(3000)
        browser.close()

    return storage

def run_agent_cycle_cli(product_url, max_iterations=DEFAULT_MAX_ITERATIONS, min_acceptable_score=DEFAULT_MIN_ACCEPTABLE_SCORE):
    """
    Original monolithic loop behavior for CLI usage.
    """
    storage = setup_run(product_url)
    if storage.state["status"] == "failed":
        return

    iteration = 1
    while iteration <= max_iterations and storage.state["status"] not in ["failed", "completed"]:
        storage = run_single_iteration(storage)

        if storage.state["status"] == "failed":
            break

        # CLI auto-approval logic based on score
        eval_data = storage.state["iterations"][-1].get("evaluation", {})
        current_score = float(eval_data.get("score", 0))

        if current_score >= min_acceptable_score:
            logger.info(f"Достигнута минимальная оценка ({current_score}). Остановка.")
            storage.update_status("completed")
            break

        if iteration == max_iterations:
            logger.info("Достигнут лимит итераций.")
            storage.update_status("completed")
            break

        iteration += 1

def main():
    parser = argparse.ArgumentParser(description="Автономный агент для создания Reels")
    parser.add_argument("--url", type=str, help="Ссылка на товар")
    parser.add_argument("--iterations", type=int, default=DEFAULT_MAX_ITERATIONS, help="Максимальное количество итераций")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_ACCEPTABLE_SCORE, help="Минимальная приемлемая оценка")

    args = parser.parse_args()

    product_url = args.url
    if not product_url:
        product_url = input("Введите ссылку на товар (например, Wildberries): ").strip()

    run_agent_cycle_cli(product_url, args.iterations, args.min_score)

if __name__ == "__main__":
    main()
