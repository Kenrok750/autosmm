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

def main():
    parser = argparse.ArgumentParser(description="Автономный агент для создания Reels через Gemini и Google Vids")
    parser.add_argument("--url", type=str, help="Ссылка на товар")
    parser.add_argument("--iterations", type=int, default=DEFAULT_MAX_ITERATIONS, help="Максимальное количество итераций")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_ACCEPTABLE_SCORE, help="Минимальная приемлемая оценка")

    args = parser.parse_args()

    product_url = args.url
    max_iterations = args.iterations
    min_acceptable_score = args.min_score

    if not product_url:
        product_url = input("Введите ссылку на товар (например, Wildberries): ").strip()

    if not product_url:
        logger.error("Ссылка не может быть пустой.")
        return

    logger.info("Инициализация хранилища запуска...")
    storage = RunStorage()
    storage.init_run(product_url)
    logger.info(f"Папка запуска: {storage.run_dir}")

    logger.info("Запуск агента...")
    with sync_playwright() as playwright:
        try:
            browser, context = get_browser_context(playwright)
        except FileNotFoundError as e:
            logger.error(e)
            storage.update_status("failed")
            sys.exit(1)

        gemini_page = context.new_page()
        vids_page = context.new_page()

        # Step 1: Get initial prompt from Gemini
        try:
            gemini_response = get_initial_prompt(gemini_page, product_url)
            prompt_data = extract_initial_prompt_from_response(gemini_response)
            current_prompt = prompt_data["initial_prompt"]

            storage.save_prompt("iter_00_initial.json", json.dumps(prompt_data, ensure_ascii=False, indent=2))
            logger.info(f"\n--- ИСХОДНЫЙ ПРОМПТ ---\n{current_prompt}\n-----------------------\n")

        except Exception as e:
            logger.error(f"Ошибка при получении начального промпта: {e}")
            capture_screenshot(gemini_page, storage, "error_initial_prompt.png")
            storage.update_status("failed")
            browser.close()
            return

        iteration = 1
        best_score_reached = False

        while iteration <= max_iterations and not best_score_reached:
            logger.info(f"\n=== ИТЕРАЦИЯ {iteration} ИЗ {max_iterations} ===")

            # Step 2: Generate video in Google Vids
            try:
                vids_page.bring_to_front()
                output_video_path = storage.get_video_path(iteration)
                video_path = generate_video(vids_page, current_prompt, iteration, output_video_path)
            except Exception as e:
                logger.error(f"Критическая ошибка при генерации видео: {e}")
                capture_screenshot(vids_page, storage, f"error_vids_iter_{iteration}.png")
                storage.update_status("failed")
                break

            # Step 3: Evaluate video in Gemini
            try:
                gemini_page.bring_to_front()
                gemini_eval_response = evaluate_video(gemini_page, video_path)
                eval_data = extract_evaluation_from_response(gemini_eval_response)

                storage.save_evaluation(f"iter_{iteration:02d}.json", eval_data)
                storage.record_iteration(iteration, current_prompt, video_path, eval_data)

                logger.info(f"\n--- ОЦЕНКА И НОВЫЙ ПРОМПТ ---\nОценка: {eval_data.get('score')}\nУлучшенный промпт: {eval_data['improved_prompt']}\n------------------------------------------\n")

                current_score = float(eval_data.get("score", 0))
                if current_score >= min_acceptable_score:
                     logger.info(f"Достигнута минимальная приемлемая оценка ({current_score} >= {min_acceptable_score}). Остановка цикла.")
                     best_score_reached = True
                     storage.update_status("stopped_score_reached")
                     break
                else:
                     current_prompt = eval_data["improved_prompt"]
                     storage.save_prompt(f"iter_{iteration:02d}_improved.json", json.dumps({"improved_prompt": current_prompt}, ensure_ascii=False, indent=2))

            except Exception as e:
                 logger.error(f"Ошибка при оценке видео в Gemini: {e}")
                 capture_screenshot(gemini_page, storage, f"error_gemini_eval_iter_{iteration}.png")
                 storage.update_status("failed")
                 break

            if iteration == max_iterations:
                logger.info(f"\nДостигнут лимит в {max_iterations} итераций. Последнее видео: {video_path}")
                storage.update_status("stopped_max_iterations")
                break

            iteration += 1

        if storage.state["status"] not in ["failed", "stopped_score_reached", "stopped_max_iterations"]:
            # Fallback if loop ends unexpectedly
            storage.update_status("completed")

        logger.info("\nЦикл завершен.")
        logger.info(f"Все результаты сохранены в папке: {storage.run_dir}")
        logger.info(f"Финальный статус: {storage.state['status']}")

        gemini_page.wait_for_timeout(5000)
        browser.close()

if __name__ == "__main__":
    main()
