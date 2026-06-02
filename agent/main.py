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

def run_agent_cycle(product_url, max_iterations=DEFAULT_MAX_ITERATIONS, min_acceptable_score=DEFAULT_MIN_ACCEPTABLE_SCORE, progress_callback=None):
    """
    Core logic extracted so it can be called from CLI or Streamlit UI.
    progress_callback is a function that takes a dict, e.g. {"status": "info", "message": "...", "data": ...}
    """
    def notify(msg_type, message, data=None):
        if progress_callback:
            progress_callback({"type": msg_type, "message": message, "data": data})
        if msg_type == "error":
            logger.error(message)
        else:
            logger.info(message)

    if not product_url:
        notify("error", "Ссылка не может быть пустой.")
        return None

    notify("info", "Инициализация хранилища запуска...")
    storage = RunStorage()
    storage.init_run(product_url)
    notify("info", f"Папка запуска: {storage.run_dir}")

    notify("info", "Запуск агента...")
    with sync_playwright() as playwright:
        try:
            browser, context = get_browser_context(playwright)
        except FileNotFoundError as e:
            notify("error", str(e))
            storage.update_status("failed")
            return storage

        gemini_page = context.new_page()
        vids_page = context.new_page()

        # Step 1: Get initial prompt from Gemini
        notify("info", "Получение начального промпта от Gemini...")
        try:
            gemini_response = get_initial_prompt(gemini_page, product_url)
            prompt_data = extract_initial_prompt_from_response(gemini_response)
            current_prompt = prompt_data["initial_prompt"]

            storage.save_prompt("iter_00_initial.json", json.dumps(prompt_data, ensure_ascii=False, indent=2))
            notify("prompt", f"Исходный промпт получен", data=prompt_data)

        except Exception as e:
            notify("error", f"Ошибка при получении начального промпта: {e}")
            capture_screenshot(gemini_page, storage, "error_initial_prompt.png")
            storage.update_status("failed")
            browser.close()
            return storage

        iteration = 1
        best_score_reached = False
        final_video_path = None

        while iteration <= max_iterations and not best_score_reached:
            notify("info", f"=== ИТЕРАЦИЯ {iteration} ИЗ {max_iterations} ===")

            # Step 2: Generate video in Google Vids
            notify("info", f"Генерация видео в Google Vids (Итерация {iteration})...")
            try:
                vids_page.bring_to_front()
                output_video_path = storage.get_video_path(iteration)
                video_path = generate_video(vids_page, current_prompt, iteration, output_video_path)
                final_video_path = video_path
                notify("video", f"Видео сгенерировано: {video_path}", data={"path": video_path})
            except Exception as e:
                notify("error", f"Критическая ошибка при генерации видео: {e}")
                capture_screenshot(vids_page, storage, f"error_vids_iter_{iteration}.png")
                storage.update_status("failed")
                break

            # Step 3: Evaluate video in Gemini
            notify("info", "Оценка видео в Gemini...")
            try:
                gemini_page.bring_to_front()
                gemini_eval_response = evaluate_video(gemini_page, video_path)
                eval_data = extract_evaluation_from_response(gemini_eval_response)

                storage.save_evaluation(f"iter_{iteration:02d}.json", eval_data)
                storage.record_iteration(iteration, current_prompt, video_path, eval_data)

                notify("eval", "Оценка получена", data=eval_data)

                current_score = float(eval_data.get("score", 0))
                if current_score >= min_acceptable_score:
                     notify("info", f"Достигнута минимальная приемлемая оценка ({current_score} >= {min_acceptable_score}). Остановка цикла.")
                     best_score_reached = True
                     storage.update_status("stopped_score_reached")
                     break
                else:
                     current_prompt = eval_data["improved_prompt"]
                     storage.save_prompt(f"iter_{iteration:02d}_improved.json", json.dumps({"improved_prompt": current_prompt}, ensure_ascii=False, indent=2))
                     notify("info", "Цикл продолжается с новым промптом.")

            except Exception as e:
                 notify("error", f"Ошибка при оценке видео в Gemini: {e}")
                 capture_screenshot(gemini_page, storage, f"error_gemini_eval_iter_{iteration}.png")
                 storage.update_status("failed")
                 break

            if iteration == max_iterations:
                notify("info", f"Достигнут лимит в {max_iterations} итераций.")
                storage.update_status("stopped_max_iterations")
                break

            iteration += 1

        if storage.state["status"] not in ["failed", "stopped_score_reached", "stopped_max_iterations"]:
            # Fallback if loop ends unexpectedly
            storage.update_status("completed")

        notify("done", "Цикл завершен.", data={"final_status": storage.state['status'], "run_dir": storage.run_dir, "final_video": final_video_path})

        gemini_page.wait_for_timeout(3000)
        browser.close()

    return storage

def main():
    parser = argparse.ArgumentParser(description="Автономный агент для создания Reels через Gemini и Google Vids")
    parser.add_argument("--url", type=str, help="Ссылка на товар")
    parser.add_argument("--iterations", type=int, default=DEFAULT_MAX_ITERATIONS, help="Максимальное количество итераций")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_ACCEPTABLE_SCORE, help="Минимальная приемлемая оценка")

    args = parser.parse_args()

    product_url = args.url
    if not product_url:
        product_url = input("Введите ссылку на товар (например, Wildberries): ").strip()

    run_agent_cycle(product_url, args.iterations, args.min_score)

if __name__ == "__main__":
    main()
