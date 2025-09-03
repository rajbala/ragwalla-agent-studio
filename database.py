#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiosqlite==0.19.0",
# ]
# ///

import aiosqlite
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleDatabaseService:
    """Minimal database service - just sessions and messages, no fluff"""
    
    def __init__(self, db_path: str = "ragwalla_chat.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Create the only two tables we actually need"""
        async with aiosqlite.connect(self.db_path) as db:
            # Chat sessions - minimal info
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Chat messages - just the conversation
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
                )
            """)
            
            await db.commit()
            logger.info("Simple database initialized with 2 tables")
    
    # ========== SESSION OPERATIONS ==========
    
    async def create_session(self, agent_id: str) -> Dict[str, Any]:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO chat_sessions (id, agent_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, agent_id, now, now)
            )
            await db.commit()
        
        return {
            "id": session_id,
            "agent_id": agent_id,
            "created_at": now,
            "updated_at": now
        }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, agent_id, created_at, updated_at FROM chat_sessions WHERE id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "agent_id": row[1],
                        "created_at": row[2],
                        "updated_at": row[3]
                    }
        return None
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all chat sessions, newest first"""
        sessions = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, agent_id, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC"
            ) as cursor:
                async for row in cursor:
                    sessions.append({
                        "id": row[0],
                        "agent_id": row[1],
                        "created_at": row[2],
                        "updated_at": row[3]
                    })
        return sessions
    
    async def update_session_timestamp(self, session_id: str):
        """Update session's last activity timestamp"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), session_id)
            )
            await db.commit()
    
    # ========== MESSAGE OPERATIONS ==========
    
    async def add_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """Add a message to a session"""
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, session_id, role, content, now)
            )
            await db.commit()
        
        # Update session timestamp
        await self.update_session_timestamp(session_id)
        
        return {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": now
        }
    
    async def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        messages = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT id, role, content, created_at 
                   FROM chat_messages 
                   WHERE session_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (session_id, limit)
            ) as cursor:
                async for row in cursor:
                    messages.append({
                        "id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "created_at": row[3]
                    })
        
        # Return in chronological order
        return list(reversed(messages))
    
    async def update_message_content(self, message_id: str, content: str):
        """Update a message's content (for streaming)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chat_messages SET content = ? WHERE id = ?",
                (content, message_id)
            )
            await db.commit()
    
    # ========== CLEANUP OPERATIONS ==========
    
    async def delete_session(self, session_id: str):
        """Delete a session and all its messages"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            await db.commit()
    
    async def cleanup_old_sessions(self, days: int = 30):
        """Delete sessions older than specified days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cutoff_date = datetime.fromtimestamp(cutoff).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get old session IDs
            async with db.execute(
                "SELECT id FROM chat_sessions WHERE updated_at < ?",
                (cutoff_date,)
            ) as cursor:
                old_sessions = [row[0] for row in await cursor.fetchall()]
            
            # Delete messages and sessions
            for session_id in old_sessions:
                await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
                await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            
            await db.commit()
            logger.info(f"Cleaned up {len(old_sessions)} old sessions")