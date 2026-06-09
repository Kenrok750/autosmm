import streamlit as st
import os
import subprocess
from playwright.sync_api import sync_playwright

import agent.db as db
from agent.scraper import scrape_wb_products
from agent.auth import get_browser_context
from agent.main import setup_run, run_single_iteration
from agent.config import STATE_FILE
from agent.storage import RunStorage
from agent.product_bible import DEFAULT_DACHSHUND_BIBLE
from agent.exporter import export_post_package

# Initialize DB on startup
db.init_db()

st.set_page_config(page_title="Reels Factory", page_icon="🎬", layout="wide")

st.title("🎬 Фабрика Reels: Human-in-the-Loop")

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

# ---- Helper Callbacks ----
def notify_progress(update):
    msg_type = update.get("type")
    msg = update.get("message")
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

# ---- Tabs Layout ----
tabs = st.tabs(["🛒 Товары", "📖 Product Bible", "⏳ Очередь", "🏃 Статус", "👀 Проверка", "📦 Экспорт"])
tab_products, tab_bible, tab_queue, tab_status, tab_review, tab_export = tabs

# ---- Tab 1: Products ----
with tab_products:
    st.header("Сбор товаров")
    seller_url = st.text_input("Ссылка на магазин/продавца WB:", "https://www.wildberries.ru/seller/444343")

    if st.button("🔍 Спарсить товары", disabled=not os.path.exists(STATE_FILE)):
        with st.spinner("Запускаем браузер для парсинга..."):
            with sync_playwright() as p:
                try:
                    browser, context = get_browser_context(p)
                    from playwright_stealth import stealth_sync
                    page = context.new_page()
                    stealth_sync(page)
                    products = scrape_wb_products(page, seller_url)

                    for prod in products:
                        db.add_product(prod["title"], prod["url"])
                    st.success(f"Добавлено товаров в БД: {len(products)}")

                    browser.close()
                except Exception as e:
                    st.error(f"Ошибка при парсинге: {e}")

    st.subheader("База товаров")
    db_products = db.get_products()
    if db_products:
        for p in db_products:
            with st.expander(f"{p['title']} (ID: {p['id']})"):
                st.write(p["url"])
    else:
        st.info("Нет товаров в базе. Спарсите их.")

# ---- Tab 2: Product Bible ----
with tab_bible:
    st.header("Редактор Product Bible")
    db_products = db.get_products()
    if db_products:
        product_options = {f"{p['title']} (ID: {p['id']})": p['id'] for p in db_products}
        selected_prod_label = st.selectbox("Выберите товар", list(product_options.keys()))
        selected_prod_id = product_options[selected_prod_label]

        bible = db.get_product_bible(selected_prod_id)
        is_new_bible = bible is None
        if is_new_bible:
             bible = DEFAULT_DACHSHUND_BIBLE

        with st.form("bible_form"):
             b_name = st.text_input("Product Name", bible.get('product_name', ''))
             b_audience = st.text_area("Target Audience", bible.get('target_audience', ''))
             b_material = st.text_input("Material", bible.get('material', ''))
             b_color = st.text_input("Color", bible.get('color', ''))
             b_must_show = st.text_area("Must Show", bible.get('must_show', ''))
             b_must_not_show = st.text_area("Must NOT Show (Critical)", bible.get('must_not_show', ''))
             b_selling_points = st.text_area("Selling Points", bible.get('selling_points', ''))
             b_usage_scenarios = st.text_area("Usage Scenarios", bible.get('usage_scenarios', ''))
             b_forbidden = st.text_area("Forbidden Claims", bible.get('forbidden_claims', ''))

             if st.form_submit_button("Сохранить Product Bible"):
                 new_bible = {
                     'product_name': b_name, 'target_audience': b_audience,
                     'material': b_material, 'color': b_color, 'must_show': b_must_show,
                     'must_not_show': b_must_not_show, 'selling_points': b_selling_points,
                     'usage_scenarios': b_usage_scenarios, 'forbidden_claims': b_forbidden
                 }
                 db.save_product_bible(selected_prod_id, new_bible)
                 st.success("Product Bible сохранен!")
                 st.rerun()

        if not is_new_bible:
             if st.button("Add to queue", key=f"q_{selected_prod_id}"):
                  db.enqueue_product(selected_prod_id)
                  st.success(f"Товар {selected_prod_id} добавлен в очередь!")
        else:
             st.info("Please save the Product Bible before adding to queue.")
    else:
        st.info("Сначала добавьте товары.")

# ---- Tab 3: Queue ----
with tab_queue:
    st.header("Очередь генерации")
    queue_items = db.get_queue()
    if queue_items:
        for q in queue_items:
            with st.container(border=True):
                 st.write(f"**ID в очереди:** {q['id']} | **Товар:** {q['product_title']} | **Статус:** {q['status']}")
                 if q['status'] in ['pending', 'failed', 'ready_for_iteration']:
                      if st.button("▶️ Запустить / Продолжить", key=f"run_q_{q['id']}"):
                           if q['status'] == 'pending':
                                setup_run(q['product_url'], q['id'], q['product_id'], notify_progress)
                                st.rerun()
                           else:
                                if q['linked_run_id']:
                                     run_row = db.get_run(q['linked_run_id'])
                                     if run_row and run_row.get('run_dir'):
                                          if os.path.exists(run_row['run_dir']):
                                               storage = RunStorage.load(run_row['run_dir'])
                                               run_single_iteration(storage, notify_progress)
                                               st.rerun()
                                          else:
                                               st.error("Не удалось найти папку с артефактами (runs).")
                                     else:
                                          st.error("run_dir не найден в БД.")
    else:
        st.info("Очередь пуста.")

# ---- Tab 4: Generation Status ----
with tab_status:
    st.header("Статус генерации")
    runs = db.get_runs()

    if runs:
        for r in runs:
             st.write(f"**Run ID:** {r['id']} | **Статус:** {r['status']}")
    else:
        st.info("Нет активных генераций.")

# ---- Tab 5: Review ----
with tab_review:
    st.header("Проверка (Human-in-the-loop)")
    review_assets = db.get_assets_by_statuses(["human_review", "ai_rejected"])

    if review_assets:
        for a in review_assets:
            with st.expander(f"Asset ID: {a['id']} | {a['product_title']} ({a['status']})", expanded=True):
                 if a['status'] == 'ai_rejected':
                     st.error("⚠️ Это видео было отклонено AI.")
                     eval_data = db.get_evaluation(a['id'])
                     if eval_data and 'evaluation_data' in eval_data:
                         reject_reasons = eval_data['evaluation_data'].get('reject_reasons', [])
                         if reject_reasons:
                             st.write(f"**Причины отклонения:** {', '.join(reject_reasons)}")
                         st.write(f"Product Identity: {eval_data['evaluation_data'].get('product_identity_accuracy')}, Visibility: {eval_data['evaluation_data'].get('product_visibility')}, Quality: {eval_data['evaluation_data'].get('visual_quality')}")

                 col1, col2 = st.columns([1, 1])
                 with col1:
                      if os.path.exists(a['video_path']):
                          st.video(a['video_path'])
                      else:
                          st.error("Видео не найдено на диске.")
                 with col2:
                      eval_data = db.get_evaluation(a['id'])
                      if eval_data:
                           st.metric(label="Оценка AI", value=f"{eval_data['score']} / 10")
                           if 'evaluation_data' in eval_data:
                               st.json(eval_data['evaluation_data'])

                      st.write("---")
                      c1, c2, c3 = st.columns(3)
                      with c1:
                           appr_label = "✅ Одобрить" if a['status'] == "human_review" else "⚠️ Одобрить (Игнорировать AI)"
                           if st.button(appr_label, key=f"appr_{a['id']}", type="primary"):
                                db.update_asset_status(a['id'], "human_approved")
                                st.success("Одобрено!")
                                st.rerun()
                      with c2:
                           if st.button("❌ Отклонить окончательно", key=f"rej_{a['id']}"):
                                db.update_asset_status(a['id'], "human_rejected")
                                st.warning("Отклонено!")
                                st.rerun()
                      with c3:
                           if st.button("🔄 Сгенерировать следующую итерацию", key=f"iter_{a['id']}"):
                                if a.get('run_dir'):
                                    storage = RunStorage.load(a['run_dir'])
                                    with st.spinner("Генерация следующей итерации..."):
                                        run_single_iteration(storage, notify_progress)
                                    st.rerun()
                                else:
                                    st.error("Не найден путь к run_dir для генерации итерации.")
    else:
        st.info("Нет видео, ожидающих проверки или отклоненных AI.")

# ---- Tab 6: Export ----
with tab_export:
    st.header("Экспорт пакета")
    approved_assets = db.get_assets_by_status("human_approved")

    if approved_assets:
        for a in approved_assets:
             with st.container(border=True):
                  st.write(f"**Asset ID:** {a['id']} | **Товар:** {a['product_title']}")
                  if st.button("📦 Собрать Post Package", key=f"exp_{a['id']}"):
                       eval_data = db.get_evaluation(a['id'])
                       bible_data = db.get_product_bible(a['product_id'])
                       export_path = export_post_package(
                           asset_data=a,
                           evaluation_data=eval_data.get('evaluation_data', {}) if eval_data else {},
                           product_bible=bible_data if bible_data else {},
                           prompt_used=a['prompt'],
                           product_link=a['product_url']
                       )
                       if export_path:
                            db.add_post_package(a['id'], export_path)
                            db.update_asset_status(a['id'], "exported")
                            st.success(f"Экспортировано в {export_path}")
                            st.rerun()
                       else:
                            st.error("Ошибка при экспорте.")
    else:
        st.info("Нет одобренных видео для экспорта.")

    st.subheader("История экспортов")
    packages = db.get_post_packages()
    if packages:
         for p in packages:
              st.write(f"- Asset {p['asset_id']} ({p['product_title']}) -> `{p['export_path']}`")
