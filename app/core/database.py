import sqlite3
import os
import logging
from datetime import datetime

class DatabaseManager:
    _instance = None
    _db_path = "voice_spirit.db"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """Initialize the database tables."""
        if not os.path.exists(self._db_path):
             logging.info("Creating new database...")
        
        self.conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Create Sessions Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Messages Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        
        # Create Podcasts Table (播客项目)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS podcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                language TEXT DEFAULT 'zh',
                audio_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Podcast Scripts Table (播客脚本行)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS podcast_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id INTEGER,
                line_index INTEGER,
                role TEXT,
                content TEXT,
                FOREIGN KEY(podcast_id) REFERENCES podcasts(id)
            )
        ''')
        self.conn.commit()

    def create_session(self, title="New Chat"):
        """Creates a new chat session."""
        self.cursor.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_session_title(self, session_id, new_title):
        """Updates the title of a session."""
        self.cursor.execute("UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_title, session_id))
        self.conn.commit()

    def add_message(self, session_id, role, content):
        """Adds a message to a session."""
        self.cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
        msg_id = self.cursor.lastrowid
        # Update session timestamp
        self.cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
        self.conn.commit()
        return msg_id

    def get_sessions(self, limit=20):
        """Retrieves recent sessions."""
        self.cursor.execute("SELECT id, title, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()

    def get_messages(self, session_id):
        """Retrieves messages for a specific session."""
        self.cursor.execute("SELECT id, role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        return self.cursor.fetchall()

    def delete_session(self, session_id):
        """Deletes a session and its messages."""
        self.cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self.cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def delete_message(self, message_id):
        """Deletes a single message."""
        self.cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        self.conn.commit()

    def clear_all_history(self):
        """Deletes all sessions and messages."""
        self.cursor.execute("DELETE FROM messages")
        self.cursor.execute("DELETE FROM sessions")
        self.conn.commit()
    
    # ========== 播客相关方法 ==========
    
    def create_podcast(self, topic: str, language: str = "zh") -> int:
        """创建新的播客项目"""
        self.cursor.execute(
            "INSERT INTO podcasts (topic, language) VALUES (?, ?)",
            (topic, language)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_podcast(self, podcast_id: int, topic: str = None, audio_path: str = None):
        """更新播客项目"""
        updates = []
        params = []
        if topic is not None:
            updates.append("topic = ?")
            params.append(topic)
        if audio_path is not None:
            updates.append("audio_path = ?")
            params.append(audio_path)
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(podcast_id)
            self.cursor.execute(
                f"UPDATE podcasts SET {', '.join(updates)} WHERE id = ?",
                params
            )
            self.conn.commit()
    
    def save_podcast_script(self, podcast_id: int, script_lines: list):
        """保存播客脚本（先删除旧的，再插入新的）"""
        # 删除旧脚本
        self.cursor.execute("DELETE FROM podcast_scripts WHERE podcast_id = ?", (podcast_id,))
        # 插入新脚本
        for idx, line in enumerate(script_lines):
            self.cursor.execute(
                "INSERT INTO podcast_scripts (podcast_id, line_index, role, content) VALUES (?, ?, ?, ?)",
                (podcast_id, idx, line.get('role', 'A'), line.get('text', ''))
            )
        self.cursor.execute(
            "UPDATE podcasts SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (podcast_id,)
        )
        self.conn.commit()
    
    def get_podcasts(self, limit: int = 20) -> list:
        """获取最近的播客项目列表"""
        self.cursor.execute(
            "SELECT id, topic, language, audio_path, updated_at FROM podcasts ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        return self.cursor.fetchall()
    
    def get_podcast(self, podcast_id: int) -> dict:
        """获取单个播客项目详情"""
        self.cursor.execute(
            "SELECT id, topic, language, audio_path, created_at, updated_at FROM podcasts WHERE id = ?",
            (podcast_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'topic': row[1],
                'language': row[2],
                'audio_path': row[3],
                'created_at': row[4],
                'updated_at': row[5]
            }
        return None
    
    def get_podcast_script(self, podcast_id: int) -> list:
        """获取播客脚本"""
        self.cursor.execute(
            "SELECT role, content FROM podcast_scripts WHERE podcast_id = ? ORDER BY line_index ASC",
            (podcast_id,)
        )
        return [{'role': row[0], 'text': row[1]} for row in self.cursor.fetchall()]
    
    def delete_podcast(self, podcast_id: int):
        """删除播客项目及其脚本"""
        self.cursor.execute("DELETE FROM podcast_scripts WHERE podcast_id = ?", (podcast_id,))
        self.cursor.execute("DELETE FROM podcasts WHERE id = ?", (podcast_id,))
        self.conn.commit()
    
    def get_latest_podcast(self) -> dict:
        """获取最新的播客项目"""
        self.cursor.execute(
            "SELECT id, topic, language, audio_path, updated_at FROM podcasts ORDER BY updated_at DESC LIMIT 1"
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'topic': row[1],
                'language': row[2],
                'audio_path': row[3],
                'updated_at': row[4]
            }
        return None
