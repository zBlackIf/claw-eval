# -*- coding: utf-8 -*-
"""期货消息面汇总系统 - 数据库层"""
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional


class FuturesDatabase:
    def __init__(self, db_path: str = "futures_news.db"):
        self.db_path = db_path
        self.init_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 消息记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variety TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            source_date DATE NOT NULL,
            raw_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 品种配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS varieties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 早评历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS morning_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE UNIQUE NOT NULL,
            content TEXT NOT NULL,
            sent_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 初始化默认品种
        default_varieties = ['铝', '铜', '锌', '铅', '镍', '锡', '不锈钢', '工业硅']
        for var in default_varieties:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO varieties (name) VALUES (?)",
                    (var,)
                )
            except:
                pass

        conn.commit()
        conn.close()

    def insert_message(self, variety: str, category: str, content: str,
                       source_date: Optional[date] = None, raw_content: Optional[str] = None) -> int:
        """插入一条消息"""
        if source_date is None:
            source_date = date.today()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO messages (variety, category, content, source_date, raw_content)
        VALUES (?, ?, ?, ?, ?)
        ''', (variety, category, content, source_date.isoformat(), raw_content))
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_messages_by_date(self, target_date: date, variety: Optional[str] = None) -> List[Dict]:
        """获取指定日期的消息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if variety:
            cursor.execute('''
            SELECT * FROM messages WHERE source_date = ? AND variety = ?
            ORDER BY variety, category
            ''', (target_date.isoformat(), variety))
        else:
            cursor.execute('''
            SELECT * FROM messages WHERE source_date = ?
            ORDER BY variety, category
            ''', (target_date.isoformat(),))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_varieties(self) -> List[str]:
        """获取所有启用的品种"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM varieties WHERE enabled = 1 ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        return [row['name'] for row in rows]


# 全局数据库实例
db = FuturesDatabase()
