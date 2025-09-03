#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic==2.5.0",
# ]
# ///

from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime

# ========== SIMPLE REQUEST/RESPONSE MODELS ==========

class CreateSessionRequest(BaseModel):
    """Request to create a new chat session"""
    agent_id: str

class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str

class ChatSession(BaseModel):
    """Minimal chat session model"""
    id: str
    agent_id: str
    created_at: str
    updated_at: str

class ChatMessage(BaseModel):
    """Minimal message model"""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: str

class WSMessage(BaseModel):
    """WebSocket message format"""
    type: str  # 'user_message', 'ai_response', 'ai_chunk', 'error', 'typing', etc.
    payload: Dict[str, Any]
    timestamp: str

class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None