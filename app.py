#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastapi==0.104.1",
#     "uvicorn[standard]==0.24.0",
#     "websockets==12.0",
#     "pydantic==2.5.0",
#     "aiosqlite==0.19.0",
#     "aiohttp==3.9.0",
#     "jinja2==3.1.2",
#     "python-dotenv==1.0.0",
# ]
# ///

from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import logging
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CreateSessionRequest, SendMessageRequest, 
    ChatSession, ChatMessage, WSMessage, ApiResponse
)
from database import SimpleDatabaseService
from ai_service import AIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== WEBSOCKET CONNECTION MANAGER ==========

class ConnectionManager:
    """Manages WebSocket connections for chat sessions"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected to session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")
    
    async def send_to_session(self, message: str, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message)
                except:
                    pass  # Connection might be closed

# ========== GLOBAL INSTANCES ==========

# Validate required environment variables
agent_base_url = os.getenv("AGENT_BASE_URL")
api_token = os.getenv("RAGWALLA_API_KEY")

if not agent_base_url:
    raise ValueError("ERROR: AGENT_BASE_URL environment variable is required")
if not api_token:
    raise ValueError("ERROR: RAGWALLA_API_KEY environment variable is required")

manager = ConnectionManager()
db = SimpleDatabaseService()
ai = AIService(
    agent_base_url=agent_base_url,
    api_token=api_token
)
templates = Jinja2Templates(directory="templates")

# ========== APP LIFECYCLE ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Ragwalla Agent Studio (Simplified)")
    await db.initialize()
    
    # Check agent connection
    is_connected = await ai.validate_agent_connection()
    if is_connected:
        logger.info("✅ Connected to Ragwalla API")
    else:
        logger.warning("⚠️ Cannot connect to Ragwalla API - check your API key")
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
    await ai.close()

# ========== FASTAPI APP ==========

app = FastAPI(
    title="Ragwalla Agent Studio",
    description="Simplified AI chat interface",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== WEB INTERFACE ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})

# ========== SESSION ENDPOINTS ==========

@app.post("/sessions", response_model=ApiResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chat session"""
    try:
        # Verify agent exists
        agents = await ai.get_agents()
        agent = next((a for a in agents if a.get('id') == request.agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create session
        session = await db.create_session(request.agent_id)
        
        return ApiResponse(
            success=True,
            data={
                "session": session,
                "agent": agent,
                "websocket_url": f"/ws/{session['id']}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=ApiResponse)
async def get_sessions():
    """Get all chat sessions"""
    try:
        sessions = await db.get_all_sessions()
        
        # For each session, get first message for preview
        for session in sessions:
            messages = await db.get_messages(session['id'], limit=1)
            if messages:
                session['preview'] = messages[0]['content'][:100]
            else:
                session['preview'] = "New chat"
        
        return ApiResponse(success=True, data={"sessions": sessions})
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/messages", response_model=ApiResponse)
async def get_messages(session_id: str, limit: int = 50):
    """Get messages for a session"""
    try:
        messages = await db.get_messages(session_id, limit)
        return ApiResponse(success=True, data={"messages": messages})
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== AGENT ENDPOINTS ==========

@app.get("/agents", response_model=ApiResponse)
async def get_agents():
    """Get available agents from Ragwalla"""
    try:
        agents = await ai.get_agents()
        return ApiResponse(success=True, data={"agents": agents})
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        return ApiResponse(success=False, error=str(e))

# ========== WEBSOCKET ENDPOINT ==========

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time chat"""
    try:
        # Verify session exists
        session = await db.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Connect
        await manager.connect(websocket, session_id)
        
        # Send message history
        messages = await db.get_messages(session_id)
        history_msg = WSMessage(
            type="history",
            payload={"messages": messages},
            timestamp=datetime.now().isoformat()
        )
        await websocket.send_text(history_msg.json())
        
        # Message loop
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "user_message":
                await handle_user_message(websocket, session_id, message_data, session['agent_id'])
            elif message_data["type"] == "ping":
                pong = WSMessage(type="pong", payload={}, timestamp=datetime.now().isoformat())
                await websocket.send_text(pong.json())
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)

async def handle_user_message(websocket: WebSocket, session_id: str, data: Dict, agent_id: str):
    """Handle incoming user message"""
    try:
        content = data["payload"]["content"]
        thread_id = data["payload"].get("threadId")  # Extract threadId if present
        
        if thread_id:
            logger.info(f"Received message with threadId: {thread_id}")
        else:
            logger.info("Received message without threadId - will create new thread")
        
        # Save user message
        user_msg = await db.add_message(session_id, "user", content)
        
        # Broadcast user message
        ws_msg = WSMessage(
            type="user_message",
            payload=user_msg,
            timestamp=datetime.now().isoformat()
        )
        await manager.send_to_session(ws_msg.json(), session_id)
        
        # Get agent info
        agents = await ai.get_agents()
        agent = next((a for a in agents if a.get('id') == agent_id), None)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return
        
        # Send typing indicator
        typing = WSMessage(
            type="typing",
            payload={"typing": True},
            timestamp=datetime.now().isoformat()
        )
        await manager.send_to_session(typing.json(), session_id)
        
        # Get conversation context
        context = await db.get_messages(session_id, limit=10)
        context_messages = [ChatMessage(**msg) for msg in context[:-1]]  # Exclude current message
        
        # Generate AI response with streaming
        ai_message_id = None
        full_response = ""
        
        async def stream_callback(chunk: str, is_complete: bool = False):
            nonlocal ai_message_id, full_response
            
            if chunk:
                # Check if this is a thread_info message
                if chunk.startswith("__THREAD_INFO__"):
                    thread_id = chunk.replace("__THREAD_INFO__", "")
                    logger.info(f"Forwarding thread_info to frontend: {thread_id}")
                    
                    # Send thread_info to frontend
                    thread_msg = WSMessage(
                        type="thread_info",
                        payload={"threadId": thread_id},
                        timestamp=datetime.now().isoformat()
                    )
                    await manager.send_to_session(thread_msg.json(), session_id)
                    return
                
                full_response += chunk
                
                # Create message on first chunk
                if ai_message_id is None:
                    ai_msg = await db.add_message(session_id, "assistant", "")
                    ai_message_id = ai_msg['id']
                
                # Send chunk
                chunk_msg = WSMessage(
                    type="ai_chunk",
                    payload={"chunk": chunk, "message_id": ai_message_id},
                    timestamp=datetime.now().isoformat()
                )
                await manager.send_to_session(chunk_msg.json(), session_id)
            
            if is_complete:
                # Update message with full content
                if ai_message_id:
                    await db.update_message_content(ai_message_id, full_response)
                
                # Send typing done
                typing_done = WSMessage(
                    type="typing",
                    payload={"typing": False},
                    timestamp=datetime.now().isoformat()
                )
                await manager.send_to_session(typing_done.json(), session_id)
                
                # Send complete message
                complete = WSMessage(
                    type="ai_complete",
                    payload={"message_id": ai_message_id, "content": full_response},
                    timestamp=datetime.now().isoformat()
                )
                await manager.send_to_session(complete.json(), session_id)
        
        # Generate response
        await ai.generate_response_stream(content, context_messages, agent, stream_callback, thread_id)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_msg = WSMessage(
            type="error",
            payload={"error": str(e)},
            timestamp=datetime.now().isoformat()
        )
        await manager.send_to_session(error_msg.json(), session_id)

# ========== HEALTH CHECK ==========

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)