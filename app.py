import streamlit as st
import os
import json
import subprocess
from playwright.sync_api import sync_playwright

from agent.scraper import scrape_wb_products
from agent.auth import get_browser_context
from agent.main import setup_run, run_single_iteration
from agent.config import STATE_FILE, OUTPUT_DIR
from agent.storage import RunStorage

st.set_page_config(page_title="Reels Factory", page_icon="🎬", layout="wide")

st.title("🎬 Фабрика Reels: Автоматизация контента")
st.markdown("Спарсите свои товары, сгенерируйте сценарий через Gemini, создайте видео в Google Vids и выберите лучший результат.")

# ---- CSS / Styling ----
st.markdown("""
<style>
.video-container {
    border: 2px solid #4CAF50;
    border-radius: 10px;
    padding: 10px;
    background-color: #f9f9f9;
}
</style>
""", unsafe_allow_html=True)

# ---- Session State Init ----
if "stage" not in st.session_state:
    st.session_state.stage = "scraping" # scraping -> ready_to_generate -> iterating -> done
if "products" not in st.session_state:
    st.session_state.products = []
if "selected_product_url" not in st.session_state:
    st.session_state.selected_product_url = ""
if "current_run_dir" not in st.session_state:
    st.session_state.current_run_dir = None

# ---- Helper Callbacks ----
def notify_progress(update):
    msg_type = update.get("type")
    msg = update.get("message")
    data = update.get("data")

    if msg_type == "info":
        st.info(f"⏳ {msg}")
    elif msg_type == "error":
        st.error(f"❌ {msg}")

# ---- Sidebar Configuration ----
with st.sidebar:
    st.header("Настройки")
    auth_status = "✅ Авторизован" if os.path.exists(STATE_FILE) else "❌ Не авторизован"
    st.markdown(f"**Статус:** {auth_status}")

    if not os.path.exists(STATE_FILE):
        st.warning("Пройдите авторизацию!")
        if st.button("Запустить авторизацию (терминал)"):
            import sys
            subprocess.Popen([sys.executable, "-m", "agent.auth"])

    st.divider()
    if st.button("🔄 Начать всё заново"):
        st.session_state.stage = "scraping"
        st.session_state.current_run_dir = None
        st.rerun()

# ---- Stage 1: Scraping ----
if st.session_state.stage == "scraping":
    st.header("1. Сбор товаров")
    seller_url = st.text_input("Ссылка на магазин/продавца WB:", "https://www.wildberries.ru/seller/444343")

    if st.button("🔍 Спарсить товары", disabled=not os.path.exists(STATE_FILE)):
        with st.spinner("Запускаем браузер для парсинга..."):
            with sync_playwright() as p:
                try:
                    browser, context = get_browser_context(p)
                    page = context.new_page()
                    products = scrape_wb_products(page, seller_url)
                    st.session_state.products = products
                    browser.close()
                except Exception as e:
                    st.error(f"Ошибка при парсинге: {e}")

    if st.session_state.products:
        st.success(f"Найдено товаров: {len(st.session_state.products)}")
        product_options = {p["title"]: p["url"] for p in st.session_state.products}
        selected_title = st.selectbox("Выберите товар для генерации Reels:", list(product_options.keys()))

        if st.button("Перейти к генерации"):
            st.session_state.selected_product_url = product_options[selected_title]
            st.session_state.stage = "ready_to_generate"
            st.rerun()

# ---- Stage 2: Ready to Generate (Setup Run) ----
elif st.session_state.stage == "ready_to_generate":
    st.header("2. Генерация сценария")
    st.info(f"Выбран товар: {st.session_state.selected_product_url}")

    if st.button("🪄 Составить сценарий (Gemini)"):
        with st.spinner("Анализ трендов и написание сценария..."):
            storage = setup_run(st.session_state.selected_product_url, notify_progress)
            if storage and storage.state["status"] == "ready_for_iteration":
                st.session_state.current_run_dir = storage.run_dir
                st.session_state.stage = "iterating"
                st.rerun()

# ---- Stage 3: Iterating (Human in the Loop) ----
elif st.session_state.stage == "iterating":
    st.header("3. Генерация и Оценка")

    storage = RunStorage.load(st.session_state.current_run_dir)
    iterations = storage.state.get("iterations", [])

    # Display the current prompt
    with st.expander("Текущий сценарий / Промпт", expanded=False):
        st.write(storage.get_latest_prompt())

    # If we are waiting for user action (after an iteration)
    if storage.state["status"] == "awaiting_user_approval":
        last_iter = iterations[-1]

        st.markdown("### Результат генерации")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("<div class='video-container'>", unsafe_allow_html=True)
            if os.path.exists(last_iter["video_path"]):
                st.video(last_iter["video_path"])
            else:
                st.warning("Файл видео не найден.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            eval_data = last_iter.get("evaluation", {})
            st.metric(label="Оценка Gemini", value=f"{eval_data.get('score', 0)} / 10")
            st.write(f"**Вердикт:** {eval_data.get('reason', '')}")
            if eval_data.get("problems"):
                st.write("**Что улучшить:**")
                for p in eval_data["problems"]:
                    st.write(f"- {p}")

            st.markdown("---")
            st.write("Что делаем дальше?")

            # Action Buttons
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ ОК, берем это!", type="primary"):
                    storage.update_status("completed")
                    st.session_state.stage = "done"
                    st.rerun()
            with c2:
                if st.button("🔄 Переделать (Итерация +1)"):
                    storage.update_status("ready_for_iteration")
                    st.rerun()

    # If we are ready to run the next iteration
    elif storage.state["status"] == "ready_for_iteration":
        iter_num = len(iterations) + 1
        st.info(f"Готов к запуску Итерации #{iter_num}.")
        if st.button("🎬 Сгенерировать видео"):
            with st.spinner(f"Работа агента (Итерация {iter_num}). Это может занять несколько минут..."):
                storage = run_single_iteration(storage, notify_progress)
                st.rerun()

    elif storage.state["status"] == "failed":
        st.error("Произошла ошибка во время работы агента. Проверьте логи в терминале.")
        if st.button("Попробовать снова (Рестарт цикла)"):
            storage.update_status("ready_for_iteration")
            st.rerun()

# ---- Stage 4: Done ----
elif st.session_state.stage == "done":
    st.header("🎉 Готово!")
    storage = RunStorage.load(st.session_state.current_run_dir)

    st.success("Вы успешно завершили генерацию Reels!")
    st.balloons()

    best_video = storage.state.get("best_video_path")
    if not best_video and storage.state.get("iterations"):
         # fallback to last video
         best_video = storage.state["iterations"][-1]["video_path"]

    if best_video and os.path.exists(best_video):
        st.video(best_video)
        st.write(f"📁 Видео сохранено: `{best_video}`")

    if st.button("Начать заново с другим товаром"):
        st.session_state.stage = "scraping"
        st.rerun()

# ---- History Area ----
st.sidebar.divider()
if os.path.exists(OUTPUT_DIR):
    runs = sorted(os.listdir(OUTPUT_DIR), reverse=True)
    if runs:
        with st.sidebar.expander("📁 История запусков"):
             for run in runs[:5]: # show last 5
                 st.write(f"- `{run}`")
