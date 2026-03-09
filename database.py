# database.py
import sqlite3
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_FILE = "dacreator_history.db"

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                direction TEXT NOT NULL,
                time_str TEXT NOT NULL,
                time_ms INTEGER NOT NULL,
                rank TEXT,
                car TEXT,
                national_rank TEXT,
                record_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_course_direction ON records(course, direction)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_time_ms ON records(time_ms)
        ''')
        conn.commit()

def str_time_to_ms(time_str: str) -> int:
    """将时间字符串转换为毫秒数"""
    try:
        if "'" in time_str and '"' in time_str:
            m, rest = time_str.split("'")
            s, ms = rest.split('"')
            return int(m)*60000 + int(s)*1000 + int(ms)
        elif ":" in time_str and "." in time_str:
            m, rest = time_str.split(":")
            s, ms = rest.split(".")
            return int(m)*60000 + int(s)*1000 + int(ms)
        else:
            return 99999999
    except:
        return 99999999

def insert_records(df: pd.DataFrame, source: str):
    """
    将DataFrame中的记录插入数据库。
    df 应包含列: コース, ルート, タイム, タイム評価, 記録車種, 全国順位 (可选), 記録日
    """
    if df.empty:
        return
    
    # 确保 time_ms 列存在
    if 'time_ms' not in df.columns:
        df['time_ms'] = df['タイム'].apply(str_time_to_ms)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            # 检查是否已存在完全相同的记录（相同赛道、方向、时间毫秒）
            cursor.execute('''
                SELECT id FROM records 
                WHERE course = ? AND direction = ? AND time_ms = ?
            ''', (row['コース'], row['ルート'], row['time_ms']))
            if cursor.fetchone():
                continue  # 已存在，跳过
            
            # 插入新记录
            cursor.execute('''
                INSERT INTO records 
                (course, direction, time_str, time_ms, rank, car, national_rank, record_date, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['コース'],
                row['ルート'],
                row['タイム'],
                row['time_ms'],
                row.get('タイム評価', ''),
                row.get('記録車種', ''),
                row.get('全国順位', ''),
                row.get('記録日', ''),
                source
            ))
        conn.commit()

def get_history(course: Optional[str] = None, direction: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    获取历史记录，可按赛道、方向筛选，按创建时间倒序排列（最新的在前）
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM records"
        params = []
        conditions = []
        if course:
            conditions.append("course = ?")
            params.append(course)
        if direction:
            conditions.append("direction = ?")
            params.append(direction)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_best_records() -> List[Dict[str, Any]]:
    """
    获取每个赛道方向的最佳记录（最快时间）
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT course, direction, MIN(time_ms) as best_time_ms,
                   time_str, rank, car, national_rank, record_date, created_at
            FROM records
            GROUP BY course, direction
            ORDER BY course, direction
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_recent_improvements(limit: int = 50) -> List[Dict[str, Any]]:
    """
    获取最近的进步记录（新记录比前一条快的情况）
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # 使用窗口函数 LAG 获取前一条记录的时间
        cursor.execute('''
            SELECT course, direction, time_ms, time_str, rank, record_date, created_at,
                   LAG(time_ms) OVER (PARTITION BY course, direction ORDER BY created_at) as prev_time_ms
            FROM records
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        improvements = []
        for row in rows:
            if row['prev_time_ms'] is not None and row['time_ms'] < row['prev_time_ms']:
                improvement = row['prev_time_ms'] - row['time_ms']
                improvements.append({
                    'course': row['course'],
                    'direction': row['direction'],
                    'new_time': row['time_str'],
                    'old_time_ms': row['prev_time_ms'],
                    'improvement_ms': improvement,
                    'record_date': row['record_date'],
                    'created_at': row['created_at']
                })
        return improvements

def get_distinct_courses() -> List[str]:
    """获取所有不重复的赛道名称"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT course FROM records ORDER BY course")
        rows = cursor.fetchall()
        return [row['course'] for row in rows]

def close():
    """关闭数据库连接（实际上连接会自动关闭，此函数保留以兼容）"""
    pass