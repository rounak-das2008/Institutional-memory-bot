import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import CHAT_DB_PATH, MAX_CHAT_HISTORY, MAX_SESSIONS_PER_USER
from logger import query_logger

class ChatSessionManager:
    def __init__(self):
        self.db_path = CHAT_DB_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize the chat sessions database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT DEFAULT 'default_user',
                    is_active BOOLEAN DEFAULT 0
                )
                ''')
                
                conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                )
                ''')
                
                conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_updated 
                ON chat_sessions(updated_at DESC)
                ''')
                
                conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON chat_messages(session_id, created_at)
                ''')
                
                conn.commit()
                
        except Exception as e:
            query_logger.log_error(f"Failed to initialize chat database: {str(e)}")
            raise
    
    def create_session(self, title: str = None, user_id: str = "default_user") -> str:
        """Create a new chat session"""
        try:
            session_id = str(uuid.uuid4())
            
            if not title:
                title = f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
            
            # Clean up old sessions if user has too many
            self._cleanup_old_sessions(user_id)
            
            with sqlite3.connect(self.db_path) as conn:
                # Deactivate all other sessions for this user
                conn.execute('''
                UPDATE chat_sessions 
                SET is_active = 0 
                WHERE user_id = ?
                ''', (user_id,))
                
                # Create new session
                conn.execute('''
                INSERT INTO chat_sessions (id, title, user_id, is_active)
                VALUES (?, ?, ?, 1)
                ''', (session_id, title, user_id))
                
                conn.commit()
            
            query_logger.logger.info(f"Created new chat session: {session_id}")
            return session_id
            
        except Exception as e:
            query_logger.log_error(f"Failed to create chat session: {str(e)}")
            raise
    
    def get_active_session(self, user_id: str = "default_user") -> Optional[str]:
        """Get the currently active session for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                SELECT id FROM chat_sessions 
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT 1
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            query_logger.log_error(f"Failed to get active session: {str(e)}")
            return None
    
    def switch_session(self, session_id: str, user_id: str = "default_user") -> bool:
        """Switch to a different session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Deactivate all sessions for this user
                conn.execute('''
                UPDATE chat_sessions 
                SET is_active = 0 
                WHERE user_id = ?
                ''', (user_id,))
                
                # Activate the selected session
                result = conn.execute('''
                UPDATE chat_sessions 
                SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                conn.commit()
                return result.rowcount > 0
                
        except Exception as e:
            query_logger.log_error(f"Failed to switch session: {str(e)}")
            return False
    
    def get_session_list(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                SELECT id, title, created_at, updated_at, is_active,
                       (SELECT COUNT(*) FROM chat_messages WHERE session_id = chat_sessions.id) as message_count
                FROM chat_sessions 
                WHERE user_id = ?
                ORDER BY updated_at DESC
                ''', (user_id,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        'id': row[0],
                        'title': row[1],
                        'created_at': row[2],
                        'updated_at': row[3],
                        'is_active': bool(row[4]),
                        'message_count': row[5]
                    })
                
                return sessions
                
        except Exception as e:
            query_logger.log_error(f"Failed to get session list: {str(e)}")
            return []
    
    def add_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None, feedback: str = None) -> bool:
        """Add a message to a session"""
        try:
            sources_json = json.dumps(sources) if sources else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                INSERT INTO chat_messages (session_id, role, content, sources, feedback)
                VALUES (?, ?, ?, ?, ?)
                ''', (session_id, role, content, sources_json, feedback))
                
                # Update session timestamp
                conn.execute('''
                UPDATE chat_sessions 
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (session_id,))
                
                conn.commit()
            
            # Clean up old messages if session has too many
            self._cleanup_old_messages(session_id)
            return True
            
        except Exception as e:
            query_logger.log_error(f"Failed to add message: {str(e)}")
            return False
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                SELECT role, content, sources, feedback, created_at
                FROM chat_messages 
                WHERE session_id = ?
                ORDER BY created_at ASC
                ''', (session_id,))
                
                messages = []
                for row in cursor.fetchall():
                    sources = json.loads(row[2]) if row[2] else []
                    messages.append({
                        'role': row[0],
                        'content': row[1],
                        'sources': sources,
                        'feedback': row[3],
                        'created_at': row[4]
                    })
                
                return messages
                
        except Exception as e:
            query_logger.log_error(f"Failed to get session messages: {str(e)}")
            return []
    
    def update_message_feedback(self, session_id: str, message_content: str, feedback: str) -> bool:
        """Update feedback for a specific message"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                UPDATE chat_messages 
                SET feedback = ?
                WHERE session_id = ? AND content = ? AND role = 'assistant'
                ORDER BY created_at DESC
                LIMIT 1
                ''', (feedback, session_id, message_content))
                
                conn.commit()
                return result.rowcount > 0
                
        except Exception as e:
            query_logger.log_error(f"Failed to update message feedback: {str(e)}")
            return False
    
    def delete_session(self, session_id: str, user_id: str = "default_user") -> bool:
        """Delete a chat session and all its messages"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                DELETE FROM chat_sessions 
                WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                conn.commit()
                return result.rowcount > 0
                
        except Exception as e:
            query_logger.log_error(f"Failed to delete session: {str(e)}")
            return False
    
    def _cleanup_old_sessions(self, user_id: str):
        """Remove old sessions if user has too many"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get session count
                cursor = conn.execute('''
                SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?
                ''', (user_id,))
                
                count = cursor.fetchone()[0]
                
                if count >= MAX_SESSIONS_PER_USER:
                    # Delete oldest sessions beyond the limit
                    sessions_to_delete = count - MAX_SESSIONS_PER_USER + 1
                    conn.execute('''
                    DELETE FROM chat_sessions 
                    WHERE user_id = ? AND id IN (
                        SELECT id FROM chat_sessions 
                        WHERE user_id = ?
                        ORDER BY updated_at ASC 
                        LIMIT ?
                    )
                    ''', (user_id, user_id, sessions_to_delete))
                    
                    conn.commit()
                    
        except Exception as e:
            query_logger.log_error(f"Failed to cleanup old sessions: {str(e)}")
    
    def _cleanup_old_messages(self, session_id: str):
        """Remove old messages if session has too many"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get message count
                cursor = conn.execute('''
                SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
                ''', (session_id,))
                
                count = cursor.fetchone()[0]
                
                if count > MAX_CHAT_HISTORY:
                    # Delete oldest messages beyond the limit
                    messages_to_delete = count - MAX_CHAT_HISTORY
                    conn.execute('''
                    DELETE FROM chat_messages 
                    WHERE session_id = ? AND id IN (
                        SELECT id FROM chat_messages 
                        WHERE session_id = ?
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                    ''', (session_id, session_id, messages_to_delete))
                    
                    conn.commit()
                    
        except Exception as e:
            query_logger.log_error(f"Failed to cleanup old messages: {str(e)}")

# Global session manager instance
chat_session_manager = ChatSessionManager()