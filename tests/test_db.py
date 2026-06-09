import pytest
import sqlite3
import os
import agent.db as db

@pytest.fixture
def temp_db(tmp_path):
    # Use a temp file database for testing to avoid connection-sharing issues with :memory:
    db_file = tmp_path / "test.sqlite"
    db.DB_PATH = str(db_file)
    db.init_db()
    yield

def test_add_product(temp_db):
    pid = db.add_product("Test Product", "http://example.com")
    assert pid == 1

    products = db.get_products()
    assert len(products) == 1
    assert products[0]['title'] == "Test Product"

def test_add_duplicate_product(temp_db):
    pid1 = db.add_product("Test Product", "http://example.com")
    pid2 = db.add_product("Another Title", "http://example.com")
    assert pid1 == pid2
    assert len(db.get_products()) == 1

def test_save_product_bible(temp_db):
    pid = db.add_product("Test Product", "http://example.com")
    db.save_product_bible(pid, {"product_name": "New Name", "color": "Red"})

    bible = db.get_product_bible(pid)
    assert bible is not None
    assert bible['product_name'] == "New Name"
    assert bible['color'] == "Red"

def test_enqueue_product(temp_db):
    pid = db.add_product("Test", "http://example.com")
    qid = db.enqueue_product(pid)
    assert qid == 1

    q_items = db.get_queue()
    assert len(q_items) == 1
    assert q_items[0]['status'] == 'pending'

    db.update_queue_status(qid, "running", linked_run_id="run123")
    q_items = db.get_queue()
    assert q_items[0]['status'] == "running"
    assert q_items[0]['linked_run_id'] == "run123"

def test_runs_and_assets(temp_db):
    pid = db.add_product("Test", "http://example.com")
    qid = db.enqueue_product(pid)
    db.create_run("run1", pid, qid)

    aid = db.add_generated_asset("run1", 1, "test.mp4", "prompt")
    assert aid == 1

    db.update_asset_status(aid, "human_review")
    assets = db.get_assets_by_status("human_review")
    assert len(assets) == 1
    assert assets[0]['id'] == aid

def test_evaluation(temp_db):
    pid = db.add_product("Test", "http://example.com")
    qid = db.enqueue_product(pid)
    db.create_run("run1", pid, qid)
    aid = db.add_generated_asset("run1", 1, "test.mp4", "prompt")

    db.add_evaluation(aid, {"score": 8}, 8.0)
    eval_data = db.get_evaluation(aid)
    assert eval_data is not None
    assert eval_data['score'] == 8.0
    assert eval_data['evaluation_data']['score'] == 8
