#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
独立数据库模块 - 支持命令行调用
用法：
    python database.py --init                    # 初始化数据库
    python database.py --insert <json_file>      # 从 JSON 文件插入记录
    python database.py --query [--course <名>]   # 查询历史记录
    python database.py --courses                  # 列出所有赛道
"""

import sqlite3
import os
import json
import argparse
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "dacreator_history.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_course_direction ON records(course, direction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_ms ON records(time_ms)')
        conn.commit()

def str_time_to_ms(time_str: str) -> int:
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

def insert_records_from_df(df: pd.DataFrame, source: str):
    """从 DataFrame 插入记录（用于内部调用）"""
    if df.empty:
        return
    if 'time_ms' not in df.columns:
        df['time_ms'] = df['タイム'].apply(str_time_to_ms)
    with get_connection() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute('''
                SELECT id FROM records 
                WHERE course = ? AND direction = ? AND time_ms = ?
            ''', (row['コース'], row['ルート'], row['time_ms']))
            if cursor.fetchone():
                continue
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

def insert_records_from_json(json_file: str):
    """从 JSON 文件插入记录（JSON 应为 DataFrame 的 records 格式）"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        source = json_file  # 或用文件名标识
        insert_records_from_df(df, source)
        return True
    except Exception as e:
        return str(e)

def get_history(course: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM records"
        params = []
        conditions = []
        if course:
            conditions.append("course = ?")
            params.append(course)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_distinct_courses() -> List[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT course FROM records ORDER BY course")
        return [row['course'] for row in cursor.fetchall()]

# ---------- 命令行入口 ----------
def main():
    parser = argparse.ArgumentParser(description="DACreator 数据库模块")
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--insert', metavar='JSON_FILE', help='从 JSON 文件插入记录')
    parser.add_argument('--query', action='store_true', help='查询历史记录')
    parser.add_argument('--course', help='按赛道筛选（与 --query 一起使用）')
    parser.add_argument('--limit', type=int, default=100, help='最大返回条数')
    parser.add_argument('--courses', action='store_true', help='列出所有赛道')
    args = parser.parse_args()

    output = {}

    if args.init:
        init_db()
        output['success'] = '数据库初始化成功'
        print(json.dumps(output, ensure_ascii=False))
        return

    if args.insert:
        result = insert_records_from_json(args.insert)
        if result is True:
            output['success'] = f'已从 {args.insert} 插入记录'
        else:
            output['error'] = f'插入失败: {result}'
        print(json.dumps(output, ensure_ascii=False))
        return

    if args.query:
        records = get_history(course=args.course, limit=args.limit)
        # 将 datetime 对象转换为字符串
        for r in records:
            if 'created_at' in r and isinstance(r['created_at'], str):
                pass  # 已经是字符串
            elif 'created_at' in r:
                r['created_at'] = str(r['created_at'])
        output['records'] = records
        print(json.dumps(output, ensure_ascii=False, default=str))
        return

    if args.courses:
        courses = get_distinct_courses()
        output['courses'] = courses
        print(json.dumps(output, ensure_ascii=False))
        return

    parser.print_help()

if __name__ == '__main__':
    main()