import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = "auto_smm.sqlite"

def get_db_connection():
    # Allow overriding path if running tests
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_bible (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT,
            target_audience TEXT,
            material TEXT,
            color TEXT,
            must_show TEXT,
            must_not_show TEXT,
            selling_points TEXT,
            usage_scenarios TEXT,
            forbidden_claims TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            content_format TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            linked_run_id TEXT,
            latest_asset_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_runs (
            id TEXT PRIMARY KEY,
            product_id INTEGER,
            queue_id INTEGER,
            status TEXT,
            run_dir TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(queue_id) REFERENCES queue(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            iteration INTEGER,
            video_path TEXT,
            prompt TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES generation_runs(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER,
            evaluation_data TEXT,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(asset_id) REFERENCES generated_assets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER,
            export_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(asset_id) REFERENCES generated_assets(id)
        )
    """)

    conn.commit()
    conn.close()

# Product methods
def add_product(title: str, url: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO products (title, url) VALUES (?, ?)", (title, url))
        conn.commit()
        product_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
        product_id = cursor.fetchone()['id']
    finally:
        conn.close()
    return product_id

def get_products() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products

# Product Bible methods
def save_product_bible(product_id: int, bible_data: Dict[str, str]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM product_bible WHERE product_id = ?", (product_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE product_bible
            SET product_name=?, target_audience=?, material=?, color=?, must_show=?,
                must_not_show=?, selling_points=?, usage_scenarios=?, forbidden_claims=?
            WHERE product_id=?
        """, (
            bible_data.get('product_name'), bible_data.get('target_audience'),
            bible_data.get('material'), bible_data.get('color'),
            bible_data.get('must_show'), bible_data.get('must_not_show'),
            bible_data.get('selling_points'), bible_data.get('usage_scenarios'),
            bible_data.get('forbidden_claims'), product_id
        ))
    else:
        cursor.execute("""
            INSERT INTO product_bible
            (product_id, product_name, target_audience, material, color, must_show, must_not_show, selling_points, usage_scenarios, forbidden_claims)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, bible_data.get('product_name'), bible_data.get('target_audience'),
            bible_data.get('material'), bible_data.get('color'),
            bible_data.get('must_show'), bible_data.get('must_not_show'),
            bible_data.get('selling_points'), bible_data.get('usage_scenarios'),
            bible_data.get('forbidden_claims')
        ))
    conn.commit()
    conn.close()

def get_product_bible(product_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM product_bible WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_runs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generation_runs ORDER BY created_at DESC")
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return runs

# Queue methods
def enqueue_product(product_id: int, content_format: str = "reels", priority: int = 0) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO queue (product_id, content_format, priority)
        VALUES (?, ?, ?)
    """, (product_id, content_format, priority))
    conn.commit()
    queue_id = cursor.lastrowid
    conn.close()
    return queue_id

def get_queue() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, p.title as product_title, p.url as product_url
        FROM queue q
        JOIN products p ON q.product_id = p.id
        ORDER BY q.priority DESC, q.created_at ASC
    """)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def update_queue_status(queue_id: int, status: str, linked_run_id: Optional[str] = None, latest_asset_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if linked_run_id:
        cursor.execute("UPDATE queue SET status = ?, linked_run_id = ? WHERE id = ?", (status, linked_run_id, queue_id))
    elif latest_asset_id:
        cursor.execute("UPDATE queue SET status = ?, latest_asset_id = ? WHERE id = ?", (status, latest_asset_id, queue_id))
    else:
         cursor.execute("UPDATE queue SET status = ? WHERE id = ?", (status, queue_id))
    conn.commit()
    conn.close()

# Run methods
def create_run(run_id: str, product_id: int, queue_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO generation_runs (id, product_id, queue_id, status)
        VALUES (?, ?, ?, 'running')
    """, (run_id, product_id, queue_id))
    conn.commit()
    conn.close()

def update_run_status(run_id: str, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE generation_runs SET status = ? WHERE id = ?", (status, run_id))
    conn.commit()
    conn.close()

def update_run_dir(run_id: str, run_dir: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE generation_runs SET run_dir = ? WHERE id = ?", (run_dir, run_id))
    conn.commit()
    conn.close()

def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generation_runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Asset methods
def add_generated_asset(run_id: str, iteration: int, video_path: str, prompt: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO generated_assets (run_id, iteration, video_path, prompt)
        VALUES (?, ?, ?, ?)
    """, (run_id, iteration, video_path, prompt))
    conn.commit()
    asset_id = cursor.lastrowid
    conn.close()
    return asset_id

def update_asset_status(asset_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE generated_assets SET status = ? WHERE id = ?", (status, asset_id))
    conn.commit()
    conn.close()

def get_asset(asset_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_assets_by_status(status: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, r.product_id, r.run_dir, p.title as product_title, p.url as product_url
        FROM generated_assets a
        JOIN generation_runs r ON a.run_id = r.id
        JOIN products p ON r.product_id = p.id
        WHERE a.status = ?
        ORDER BY a.created_at DESC
    """, (status,))
    assets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return assets

def get_assets_by_statuses(statuses: List[str]) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ', '.join(['?'] * len(statuses))
    cursor.execute(f"""
        SELECT a.*, r.product_id, r.run_dir, r.queue_id, p.title as product_title, p.url as product_url
        FROM generated_assets a
        JOIN generation_runs r ON a.run_id = r.id
        JOIN products p ON r.product_id = p.id
        WHERE a.status IN ({placeholders})
        ORDER BY a.created_at DESC
    """, statuses)
    assets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return assets

# Evaluation methods
def add_evaluation(asset_id: int, eval_data: dict, score: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO evaluations (asset_id, evaluation_data, score)
        VALUES (?, ?, ?)
    """, (asset_id, json.dumps(eval_data, ensure_ascii=False), score))
    conn.commit()
    conn.close()

def get_evaluation(asset_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations WHERE asset_id = ? ORDER BY id DESC LIMIT 1", (asset_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        res['evaluation_data'] = json.loads(res['evaluation_data'])
        return res
    return None

# Post Package Methods
def add_post_package(asset_id: int, export_path: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO post_packages (asset_id, export_path)
        VALUES (?, ?)
    """, (asset_id, export_path))
    conn.commit()
    conn.close()

def get_post_packages() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.*, a.video_path, r.product_id, p.title as product_title
        FROM post_packages pp
        JOIN generated_assets a ON pp.asset_id = a.id
        JOIN generation_runs r ON a.run_id = r.id
        JOIN products p ON r.product_id = p.id
        ORDER BY pp.created_at DESC
    """)
    packages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return packages
