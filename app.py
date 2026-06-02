import streamlit as st
import os
import json
import subprocess
import threading
from agent.main import run_agent_cycle
from agent.config import MAX_ITERATIONS, MIN_ACCEPTABLE_SCORE, STATE_FILE, OUTPUT_DIR

st.set_page_config(page_title="AI Reels Agent", page_icon="🎬", layout="wide")

st.title("🎬 AI Reels Agent: Gemini + Google Vids")
st.markdown("Этот локальный агент автоматизирует создание коротких видеороликов.")

# ---- Sidebar Configuration ----
st.sidebar.header("Настройки запуска")

# Auth Status Check
auth_status = "✅ Авторизован" if os.path.exists(STATE_FILE) else "❌ Не авторизован"
st.sidebar.markdown(f"**Статус сессии:** {auth_status}")

if not os.path.exists(STATE_FILE):
    st.sidebar.warning("Вам необходимо пройти авторизацию перед запуском.")
    if st.sidebar.button("Запустить авторизацию в терминале"):
        st.sidebar.info("Откройте терминал, где запущен Streamlit, и следуйте инструкциям!")
        # Run auth script
        subprocess.Popen(["python", "-m", "agent.auth"])

st.sidebar.divider()

url_input = st.sidebar.text_input("Ссылка на товар (Wildberries и т.д.):", "https://www.wildberries.ru/catalog/1050994766/detail.aspx")
iterations_input = st.sidebar.slider("Максимальное количество итераций:", min_value=1, max_value=10, value=MAX_ITERATIONS)
score_input = st.sidebar.slider("Минимальная приемлемая оценка (1-10):", min_value=1.0, max_value=10.0, value=MIN_ACCEPTABLE_SCORE, step=0.5)

# ---- Main Area: Execution ----
st.header("Управление")

if "is_running" not in st.session_state:
    st.session_state.is_running = False

# We need a placeholder for dynamic updates
status_placeholder = st.empty()
log_container = st.container()
results_container = st.container()

def progress_callback(update):
    msg_type = update.get("type")
    msg = update.get("message")
    data = update.get("data")

    if msg_type == "info":
        status_placeholder.info(f"⏳ {msg}")
    elif msg_type == "error":
        status_placeholder.error(f"❌ {msg}")
    elif msg_type == "prompt":
        with log_container.expander("Исходный промпт (JSON)", expanded=False):
            st.json(data)
    elif msg_type == "eval":
        with log_container.expander(f"Оценка Gemini (Оценка: {data.get('score')})", expanded=True):
            st.json(data)
    elif msg_type == "video":
        with log_container.expander("Сгенерировано видео", expanded=True):
            st.success(msg)
    elif msg_type == "done":
        st.session_state.is_running = False
        status_placeholder.success(f"✅ {msg} (Статус: {data.get('final_status')})")

        # Show final video if available
        if data.get('final_video') and os.path.exists(data['final_video']):
             with results_container:
                 st.subheader("Финальное видео")
                 st.video(data['final_video'])

if st.button("🚀 Запустить генерацию", disabled=st.session_state.is_running or not os.path.exists(STATE_FILE)):
    st.session_state.is_running = True
    status_placeholder.info("Подготовка к запуску...")

    with st.spinner("Агент работает... Пожалуйста, не закрывайте вкладку."):
        # Run in the main thread (Streamlit will wait until done, which is fine for our use case)
        # Using a separate thread requires complex state queueing for Streamlit.
        storage = run_agent_cycle(
            product_url=url_input,
            max_iterations=iterations_input,
            min_acceptable_score=score_input,
            progress_callback=progress_callback
        )

    st.session_state.is_running = False

# ---- History Area ----
st.divider()
st.header("📁 История запусков")

if os.path.exists(OUTPUT_DIR):
    runs = sorted(os.listdir(OUTPUT_DIR), reverse=True)
    if runs:
        selected_run = st.selectbox("Выберите запуск для просмотра:", runs)
        run_path = os.path.join(OUTPUT_DIR, selected_run)
        state_file = os.path.join(run_path, "run_state.json")

        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Статус:** {state_data.get('status')}")
                st.write(f"**Лучшая оценка:** {state_data.get('best_score')}")

            with col2:
                best_video = state_data.get("best_video_path")
                if best_video and os.path.exists(best_video):
                    st.video(best_video)
                else:
                    st.warning("Финальное видео не найдено в этом запуске.")

            with st.expander("Детали всех итераций"):
                for it in state_data.get("iterations", []):
                    st.markdown(f"#### Итерация {it.get('iteration')}")
                    v_path = it.get('video_path')
                    if v_path and os.path.exists(v_path):
                        st.video(v_path)
                    st.json(it.get("evaluation", {}))
    else:
        st.info("История запусков пуста.")
else:
    st.info("Директория запусков еще не создана.")
