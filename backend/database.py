"""
SugarClaw SQLite 持久化层
6 张表: users, food_cache, cgm_readings, search_history, conversations, pubmed_cache
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "sugarclaw.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """创建所有表（幂等）。"""
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            name        TEXT DEFAULT '',
            age         INTEGER DEFAULT 0 CHECK(age >= 0 AND age <= 150),
            weight      REAL DEFAULT 0,
            height      REAL DEFAULT 0,
            diabetes_type TEXT DEFAULT '',
            medications TEXT DEFAULT '[]',
            isf         REAL DEFAULT 0 CHECK(isf >= 0 AND isf <= 20),
            icr         REAL DEFAULT 0,
            regional_preference TEXT DEFAULT '全国',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS food_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name   TEXT UNIQUE NOT NULL,
            gi_value    REAL,
            gi_level    TEXT,
            gl_per_serving REAL,
            serving_size_g REAL,
            carb_g      REAL DEFAULT 0,
            protein_g   REAL DEFAULT 0,
            fat_g       REAL DEFAULT 0,
            fiber_g     REAL DEFAULT 0,
            regional_tag TEXT DEFAULT '全国',
            food_category TEXT DEFAULT '其他',
            counter_strategy TEXT DEFAULT '',
            data_source TEXT DEFAULT 'DeepSeek AI 估算',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cgm_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            glucose_mmol REAL NOT NULL,
            glucose_mgdl REAL,
            event       TEXT DEFAULT '',
            source      TEXT DEFAULT 'simulation',
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cgm_session ON cgm_readings(session_id);

        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query       TEXT NOT NULL,
            mode        TEXT DEFAULT 'custom',
            results_json TEXT DEFAULT '[]',
            total_count INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS glucose_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER DEFAULT 1,
            timestamp   TEXT NOT NULL,
            glucose_mmol REAL NOT NULL,
            note        TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_glucose_log_ts ON glucose_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_glucose_log_user ON glucose_log(user_id);

        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER DEFAULT 1,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content     TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

        CREATE TABLE IF NOT EXISTS pubmed_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key   TEXT UNIQUE NOT NULL,
            results_json TEXT NOT NULL,
            total_count INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- 插入默认用户（id=1），如果不存在
        INSERT OR IGNORE INTO users (id, name) VALUES (1, '默认用户');
    """)
    conn.commit()
    conn.close()


# ─── 用户档案 ──────────────────────────────

def get_user(user_id: int = 1) -> Optional[dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["medications"] = json.loads(d.get("medications") or "[]")
    return d


def update_user(user_id: int = 1, **fields) -> dict:
    conn = _conn()
    if "medications" in fields and isinstance(fields["medications"], (list, dict)):
        fields["medications"] = json.dumps(fields["medications"], ensure_ascii=False)
    allowed = {"name", "age", "weight", "height", "diabetes_type",
               "medications", "isf", "icr", "regional_preference"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [datetime.now().isoformat(), user_id]
        conn.execute(
            f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?",
            values,
        )
        conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    d = dict(row)
    d["medications"] = json.loads(d.get("medications") or "[]")
    return d


# ─── 食物缓存 ──────────────────────────────

def cache_food(food_data: dict):
    """缓存 AI 估算的食物数据到 SQLite。"""
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO food_cache
            (food_name, gi_value, gi_level, gl_per_serving, serving_size_g,
             carb_g, protein_g, fat_g, fiber_g,
             regional_tag, food_category, counter_strategy, data_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        food_data.get("food_name", ""),
        food_data.get("gi_value", 0),
        food_data.get("gi_level", ""),
        food_data.get("gl_per_serving", 0),
        food_data.get("serving_size_g", 0),
        food_data.get("carb_g", 0),
        food_data.get("protein_g", 0),
        food_data.get("fat_g", 0),
        food_data.get("fiber_g", 0),
        food_data.get("regional_tag", "全国"),
        food_data.get("food_category", "其他"),
        food_data.get("counter_strategy", ""),
        food_data.get("data_source", "DeepSeek AI 估算"),
    ))
    conn.commit()
    conn.close()


def get_cached_food(food_name: str) -> Optional[dict]:
    """从缓存中查询食物。"""
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM food_cache WHERE food_name = ?", (food_name,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


# ─── CGM 读数 ──────────────────────────────

def save_cgm_readings(session_id: str, readings: list, source: str = "simulation"):
    """批量保存 CGM 读数。"""
    conn = _conn()
    conn.executemany("""
        INSERT INTO cgm_readings (session_id, timestamp, glucose_mmol, glucose_mgdl, event, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            session_id,
            r.get("timestamp", ""),
            r.get("glucose_mmol", 0),
            r.get("glucose_mgdl", r.get("glucose_mmol", 0) * 18.0),
            r.get("event", ""),
            source,
        )
        for r in readings
    ])
    conn.commit()
    conn.close()


def get_cgm_session(session_id: str) -> list:
    """获取指定会话的所有读数。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM cgm_readings WHERE session_id = ? ORDER BY timestamp",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_cgm_sessions() -> list:
    """列出所有 CGM 会话。"""
    conn = _conn()
    rows = conn.execute("""
        SELECT session_id, source, MIN(timestamp) as start_time,
               MAX(timestamp) as end_time, COUNT(*) as reading_count
        FROM cgm_readings
        GROUP BY session_id
        ORDER BY start_time DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cgm_history(limit: int = 100) -> list:
    """获取最近 N 条 CGM 读数。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM cgm_readings ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── 血糖日志 ──────────────────────────────

def save_glucose_entry(timestamp: str, glucose_mmol: float, note: str = "", user_id: int = 1) -> dict:
    """保存一条手动血糖记录。"""
    conn = _conn()
    cur = conn.execute("""
        INSERT INTO glucose_log (user_id, timestamp, glucose_mmol, note)
        VALUES (?, ?, ?, ?)
    """, (user_id, timestamp, glucose_mmol, note))
    row_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM glucose_log WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row)


def get_glucose_log(limit: int = 100, user_id: int = 1) -> list:
    """获取用户的血糖日志，按时间倒序。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM glucose_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_glucose_entry(entry_id: int, user_id: int = 1) -> bool:
    """删除一条血糖记录。"""
    conn = _conn()
    cur = conn.execute(
        "DELETE FROM glucose_log WHERE id = ? AND user_id = ?",
        (entry_id, user_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── 搜索历史 ──────────────────────────────

def save_search(query: str, mode: str, results: list, total_count: int = 0):
    """保存 PubMed 搜索历史。"""
    conn = _conn()
    conn.execute("""
        INSERT INTO search_history (query, mode, results_json, total_count)
        VALUES (?, ?, ?, ?)
    """, (query, mode, json.dumps(results, ensure_ascii=False), total_count))
    conn.commit()
    conn.close()


def get_recent_searches(limit: int = 20) -> list:
    """获取最近的搜索历史。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM search_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["results"] = json.loads(d.pop("results_json", "[]"))
        result.append(d)
    return result


# ─── 聊天记录 ──────────────────────────────

def save_message(session_id: str, role: str, content: str, user_id: int = 1) -> dict:
    """保存一条聊天消息。"""
    conn = _conn()
    cur = conn.execute("""
        INSERT INTO conversations (user_id, session_id, role, content)
        VALUES (?, ?, ?, ?)
    """, (user_id, session_id, role, content))
    row_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row)


def get_conversation(session_id: str, limit: int = 50) -> list:
    """获取一个会话的最近消息（按时间正序）。"""
    conn = _conn()
    rows = conn.execute("""
        SELECT * FROM conversations
        WHERE session_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (session_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_sessions(user_id: int = 1, limit: int = 10) -> list:
    """获取用户最近的会话列表（每个会话取第一条消息作为标题）。"""
    conn = _conn()
    rows = conn.execute("""
        SELECT session_id,
               MIN(created_at) as started_at,
               COUNT(*) as message_count,
               (SELECT content FROM conversations c2
                WHERE c2.session_id = c1.session_id AND c2.role = 'user'
                ORDER BY c2.created_at ASC LIMIT 1) as first_message
        FROM conversations c1
        WHERE user_id = ?
        GROUP BY session_id
        ORDER BY started_at DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(session_id: str, user_id: int = 1) -> bool:
    """删除一个会话的所有消息。"""
    conn = _conn()
    cur = conn.execute(
        "DELETE FROM conversations WHERE session_id = ? AND user_id = ?",
        (session_id, user_id)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── PubMed 缓存 ──────────────────────────────

def get_pubmed_cache(query: str, mode: str) -> Optional[dict]:
    """获取 PubMed 搜索缓存（24小时内有效）。"""
    import hashlib
    cache_key = hashlib.md5(f"{query}:{mode}".encode()).hexdigest()
    conn = _conn()
    row = conn.execute("""
        SELECT * FROM pubmed_cache
        WHERE cache_key = ?
        AND created_at > datetime('now', '-24 hours')
    """, (cache_key,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["results"] = json.loads(d.pop("results_json", "[]"))
    return d


def set_pubmed_cache(query: str, mode: str, results: list, total_count: int = 0):
    """写入 PubMed 搜索缓存。"""
    import hashlib
    cache_key = hashlib.md5(f"{query}:{mode}".encode()).hexdigest()
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO pubmed_cache (cache_key, results_json, total_count)
        VALUES (?, ?, ?)
    """, (cache_key, json.dumps(results, ensure_ascii=False), total_count))
    conn.commit()
    conn.close()
