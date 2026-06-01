import sys
from playwright.sync_api import sync_playwright

from auth import get_browser_context
from gemini import get_initial_prompt, evaluate_video, extract_prompt_from_response
from vids import generate_video

MAX_ITERATIONS = 5

def main():
    product_url = input("Введите ссылку на товар (например, Wildberries): ").strip()
    if not product_url:
        print("Ссылка не может быть пустой.")
        return

    print("\nЗапуск агента...")
    with sync_playwright() as playwright:
        try:
            # We use headless=False so you can see what's happening and intervene if selectors break
            browser, context = get_browser_context(playwright, headless=False)
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)

        # Open two pages: one for Gemini, one for Vids
        gemini_page = context.new_page()
        vids_page = context.new_page()

        # Step 1: Get initial prompt from Gemini
        try:
            gemini_response = get_initial_prompt(gemini_page, product_url)
            current_prompt = extract_prompt_from_response(gemini_response)
            print(f"\n--- ИСХОДНЫЙ ПРОМПТ ---\n{current_prompt}\n-----------------------\n")
        except Exception as e:
            print(f"Ошибка при получении начального промпта: {e}")
            browser.close()
            return

        # Main Loop
        iteration = 1
        while iteration <= MAX_ITERATIONS:
            print(f"\n=== ИТЕРАЦИЯ {iteration} ИЗ {MAX_ITERATIONS} ===")

            # Step 2: Generate video in Google Vids
            try:
                # Bring Vids page to front
                vids_page.bring_to_front()
                video_path = generate_video(vids_page, current_prompt, iteration)
            except Exception as e:
                print(f"Критическая ошибка при генерации видео: {e}")
                break

            if iteration == MAX_ITERATIONS:
                print(f"\nДостигнут лимит в {MAX_ITERATIONS} итераций. Последнее сгенерированное видео: {video_path}")
                break

            # Step 3: Evaluate video in Gemini
            try:
                # Bring Gemini page to front
                gemini_page.bring_to_front()
                gemini_eval_response = evaluate_video(gemini_page, video_path)

                print(f"\n--- ОТВЕТ GEMINI (ОЦЕНКА И НОВЫЙ ПРОМПТ) ---\n{gemini_eval_response}\n------------------------------------------\n")

                current_prompt = extract_prompt_from_response(gemini_eval_response)

            except Exception as e:
                 print(f"Ошибка при оценке видео в Gemini: {e}")
                 break

            iteration += 1

        print("\nЦикл завершен.")
        choice = input("Хотите продолжить генерацию еще на 1 итерацию? (y/n): ").strip().lower()
        if choice == 'y':
            # Run one more manually requested iteration
            print("Запуск дополнительной итерации...")
            vids_page.bring_to_front()
            try:
                final_video_path = generate_video(vids_page, current_prompt, iteration)
                print(f"Финальное видео: {final_video_path}")
            except Exception as e:
                print(f"Ошибка в дополнительной итерации: {e}")
        else:
            print("Работа завершена. Лучшее видео сохранено в папке проекта.")

        # Keep browser open for a moment before closing
        gemini_page.wait_for_timeout(5000)
        browser.close()

if __name__ == "__main__":
    main()
