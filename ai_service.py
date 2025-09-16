#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiohttp==3.9.0",
#     "pydantic==2.5.0",
# ]
# ///

import asyncio
import json
import os
import aiohttp
from typing import List, Dict, Any, Optional
import logging
from models import ChatMessage

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, agent_base_url: Optional[str] = None, api_token: Optional[str] = None):
        if not agent_base_url:
            raise ValueError("agent_base_url is required")
        if not api_token:
            raise ValueError("api_token is required")
        
        self.agent_base_url = agent_base_url
        self.api_token = api_token
        self.session = None
        
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Ragwalla-Agent-Studio/2.0"
        }
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        return headers
    
    async def _get_websocket_token(self, agent_id: str) -> str:
        """Get WebSocket authentication token from Ragwalla"""
        session = await self.get_session()
        
        token_url = f"{self.agent_base_url}/agents/auth/websocket"
        payload = {
            "agentId": agent_id,
            "expiresIn": 3600  # 1 hour
        }
        
        logger.info(f"Requesting WebSocket token from: {token_url}")
        logger.info(f"Payload: {payload}")
        logger.info(f"Headers: {self._get_auth_headers()}")
        
        try:
            async with session.post(
                token_url,
                json=payload,
                headers=self._get_auth_headers(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                logger.info(f"WebSocket token response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    ws_token = data.get("token")
                    logger.info(f"Got WebSocket token: {ws_token[:20] if ws_token else 'None'}...")
                    return ws_token
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get WebSocket token: {response.status} - {error_text}")
                    # If WebSocket token endpoint doesn't exist, try using API key directly
                    if response.status == 404:
                        logger.info("WebSocket token endpoint not found, falling back to API key")
                        return self.api_token
                    raise Exception(f"Failed to get WebSocket token: {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Timeout getting WebSocket token, falling back to API key")
            return self.api_token
        except Exception as e:
            logger.error(f"Error getting WebSocket token: {e}, falling back to API key")
            return self.api_token
    
    async def generate_response(
        self, 
        message: str, 
        context: List[ChatMessage], 
        agent: Dict[str, Any],
        stream: bool = False
    ) -> str:
        """Generate AI response by communicating with remote agent (buffered)"""
        try:
            # Get agent instance name or create one
            instance_name = agent.get('username') or agent.get('id', 'default')
            
            # Build conversation history for the agent
            messages = self._build_conversation_history(message, context, agent)
            
            # Parse model settings
            model_settings = self._parse_model_settings(agent.get('model_settings'))
            
            # Call the remote agent's chat method
            response = await self._call_remote_agent(
                instance_name=instance_name,
                message=message,
                options={
                    "model": model_settings.get("model", "gpt-4o-mini"),
                    "temperature": model_settings.get("temperature", 0.7),
                    "maxTokens": model_settings.get("max_tokens", 2000),
                    "messages": messages
                }
            )
            
            return response
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again."
    
    async def generate_response_stream(
        self, 
        message: str, 
        context: List[ChatMessage], 
        agent_data: Dict[str, Any],
        stream_callback,
        thread_id: Optional[str] = None
    ) -> None:
        """Generate AI response with real-time streaming via callback"""
        try:
            # Get agent instance name from agent data
            instance_name = agent_data.get('id')
            
            # Build conversation history for the agent
            messages = self._build_conversation_history_from_data(message, context, agent_data)
            
            # Use default model settings since agent data doesn't include them
            model_settings = {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # Call the remote agent's chat method with streaming
            await self._call_remote_agent_stream(
                instance_name=instance_name,
                message=message,
                options={
                    "model": model_settings.get("model", "gpt-4o-mini"),
                    "temperature": model_settings.get("temperature", 0.7),
                    "maxTokens": model_settings.get("max_tokens", 2000),
                    "messages": messages
                },
                stream_callback=stream_callback,
                thread_id=thread_id
            )
                
        except Exception as e:
            logger.error(f"Error generating streaming AI response: {e}")
            await stream_callback("I apologize, but I encountered an error while processing your request. Please try again.", is_complete=True)
    
    async def _call_remote_agent(
        self,
        instance_name: str,
        message: str,
        options: Dict[str, Any]
    ) -> str:
        """Call the remote agent's chat method via WebSocket"""
        
        # Generate required parameters for WebSocket connection
        import uuid
        import time
        
        session_id = f"session-{int(time.time() * 1000)}-{uuid.uuid4().hex[:9]}"
        tab_id = uuid.uuid4().hex[:26]
        
        # Convert HTTP URL to WebSocket URL with correct pattern
        ws_url = self.agent_base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/agents/{instance_name}/ws"
        
        # Add required query parameters
        ws_url += f"?session_id={session_id}&tab_id={tab_id}&auth=true"
        
        # Create timestamps with milliseconds (like the working system)
        import datetime
        current_time = datetime.datetime.utcnow()
        timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  # Trim to 3 decimal places
        
        # Create the auth message first (like the working system)
        auth_payload = {
            "type": "auth",
            "sessionId": session_id,
            "agentId": instance_name,
            "timestamp": timestamp
        }
        
        # Create the actual message payload
        # Agent has default assistant configured, so no need to specify assistantId
        message_payload = {
            "type": "message",
            "content": message,
            "userId": "1",  # Default user ID for WebSocket protocol
            "sessionId": session_id,
            "agentId": instance_name,  # This is the Ragwalla agent ID
            "timestamp": timestamp,
            "tabId": tab_id
        }
        
        logger.info(f"Connecting to WebSocket: {ws_url}")
        logger.info(f"Auth payload: {auth_payload}")
        logger.info(f"Message payload: {message_payload}")
        
        try:
            # First, get WebSocket authentication token
            logger.info("Getting WebSocket token...")
            ws_token = await self._get_websocket_token(instance_name)
            logger.info(f"WebSocket token obtained: {ws_token[:20]}...")
            
            # Create WebSocket connection with proper headers
            headers = {
                "Authorization": f"Bearer {ws_token}"
            }
            
            logger.info(f"Attempting WebSocket connection to: {ws_url}")
            logger.info(f"WebSocket headers: {headers}")
            
            session = await self.get_session()
            
            # Connect to WebSocket
            async with session.ws_connect(
                ws_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as ws:
                logger.info("✅ WebSocket connection established!")
                
                # First send auth message (like the working system)
                await ws.send_str(json.dumps(auth_payload))
                logger.info(f"Auth message sent: {json.dumps(auth_payload)}")
                
                # Then send the actual message
                await ws.send_str(json.dumps(message_payload))
                logger.info(f"Chat message sent: {json.dumps(message_payload)}")
                
                # Collect response chunks
                response_parts = []
                timeout_seconds = 30  # Increase timeout for agent processing
                
                try:
                    # Use asyncio.wait_for for Python 3.10 compatibility
                    async def collect_messages():
                        async for msg in ws:
                            logger.info(f"Received WebSocket message type: {msg.type}")
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.data
                                logger.info(f"Received WebSocket text data: {data}")
                                try:
                                    # Try to parse as JSON
                                    json_data = json.loads(data)
                                    
                                    # Handle different message types from Ragwalla agent
                                    msg_type = json_data.get("type")
                                    
                                    if msg_type == "chunk":
                                        # Streaming content chunks
                                        content = json_data.get("content", "")
                                        response_parts.append(content)
                                        logger.info(f"Received chunk: {content}")
                                    elif msg_type == "complete":
                                        # End of response
                                        logger.info("Response complete")
                                        return
                                    elif msg_type == "connected":
                                        logger.info("Agent connected successfully")
                                    elif msg_type == "typing":
                                        is_typing = json_data.get("isTyping", False)
                                        logger.info(f"Agent typing: {is_typing}")
                                    elif msg_type == "thread_info":
                                        # Log thread info for non-streaming mode
                                        thread_id = json_data.get("threadId")
                                        if thread_id:
                                            logger.info(f"Received thread_info (non-streaming): {thread_id}")
                                    elif json_data.get("error"):
                                        logger.error(f"Agent error: {json_data['error']}")
                                        raise Exception(f"Agent error: {json_data['error']}")
                                    # Ignore other message types like cf_agent_state, etc.
                                        
                                except json.JSONDecodeError:
                                    # Handle plain text responses
                                    response_parts.append(data)
                                    
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket error: {ws.exception()}")
                                return
                            elif msg.type == aiohttp.WSMsgType.CLOSE:
                                logger.info("WebSocket connection closed")
                                return
                    
                    await asyncio.wait_for(collect_messages(), timeout=timeout_seconds)
                                
                except asyncio.TimeoutError:
                    logger.info(f"WebSocket response timeout after {timeout_seconds}s")
                
                # Combine response parts
                full_response = "".join(response_parts).strip()
                
                if full_response:
                    return full_response
                else:
                    return "WebSocket connection successful, but no response received."

                    
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to agent WebSocket")
            return "Request timed out. Please try again."
        except aiohttp.ClientError as e:
            logger.error(f"WebSocket client error: {e}")
            return "Unable to connect to AI agent. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error calling remote agent: {e}")
            return "An unexpected error occurred. Please try again."
    
    async def _call_remote_agent_stream(
        self,
        instance_name: str,
        message: str,
        options: Dict[str, Any],
        stream_callback,
        thread_id: Optional[str] = None
    ) -> None:
        """Call the remote agent's chat method via WebSocket with real-time streaming"""
        
        # Generate required parameters for WebSocket connection
        import uuid
        import time
        
        session_id = f"session-{int(time.time() * 1000)}-{uuid.uuid4().hex[:9]}"
        tab_id = uuid.uuid4().hex[:26]
        
        # Convert HTTP URL to WebSocket URL with correct pattern
        ws_url = self.agent_base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/agents/{instance_name}/ws"
        
        # Add required query parameters
        ws_url += f"?session_id={session_id}&tab_id={tab_id}&auth=true"
        
        # Create timestamps with milliseconds
        import datetime
        current_time = datetime.datetime.utcnow()
        timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        # Create the auth message first
        auth_payload = {
            "type": "auth",
            "sessionId": session_id,
            "agentId": instance_name,
            "timestamp": timestamp
        }
        
        # Create the actual message payload
        message_payload = {
            "type": "message",
            "content": message,
            "userId": "1",
            "sessionId": session_id,
            "agentId": instance_name,
            "timestamp": timestamp,
            "tabId": tab_id
        }
        
        # Include threadId if provided
        if thread_id:
            message_payload["threadId"] = thread_id
            logger.info(f"Including threadId in message: {thread_id}")
        
        logger.info(f"Streaming WebSocket connection to: {ws_url}")
        
        try:
            # Get WebSocket authentication token
            ws_token = await self._get_websocket_token(instance_name)
            
            # Create WebSocket connection with proper headers
            headers = {
                "Authorization": f"Bearer {ws_token}"
            }
            
            session = await self.get_session()
            
            # Connect to WebSocket
            async with session.ws_connect(
                ws_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as ws:
                logger.info("✅ Streaming WebSocket connection established!")
                
                # First send auth message
                await ws.send_str(json.dumps(auth_payload))
                logger.info("Auth message sent for streaming")
                
                # Then send the actual message
                await ws.send_str(json.dumps(message_payload))
                logger.info("Chat message sent for streaming")
                
                # Stream response chunks in real-time
                timeout_seconds = 30
                
                try:
                    async def stream_messages():
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.data
                                try:
                                    json_data = json.loads(data)
                                    msg_type = json_data.get("type")
                                    
                                    if msg_type == "chunk":
                                        # Stream content chunks immediately
                                        content = json_data.get("content", "")
                                        if content:
                                            logger.info(f"Streaming chunk: {content}")
                                            await stream_callback(content, is_complete=False)
                                    elif msg_type == "complete":
                                        # End of response
                                        logger.info("Streaming response complete")
                                        await stream_callback("", is_complete=True)
                                        return
                                    elif msg_type == "connected":
                                        logger.info("Agent connected for streaming")
                                    elif msg_type == "typing":
                                        is_typing = json_data.get("isTyping", False)
                                        logger.info(f"Agent typing: {is_typing}")
                                    elif msg_type == "thread_info":
                                        # Forward thread info to frontend
                                        thread_id = json_data.get("threadId")
                                        if thread_id:
                                            logger.info(f"Received thread_info: {thread_id}")
                                            await stream_callback(f"__THREAD_INFO__{thread_id}", is_complete=False)
                                    elif json_data.get("error"):
                                        logger.error(f"Agent error: {json_data.get('error')}")
                                        await stream_callback(f"Error: {json_data.get('error')}", is_complete=True)
                                        return
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse WebSocket message: {data}")
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket error: {ws.exception()}")
                                await stream_callback("Connection error occurred.", is_complete=True)
                                return
                            elif msg.type == aiohttp.WSMsgType.CLOSE:
                                logger.info("WebSocket connection closed by server")
                                await stream_callback("", is_complete=True)
                                return
                    
                    # Use asyncio.wait_for for timeout (Python 3.10 compatibility)
                    await asyncio.wait_for(stream_messages(), timeout=timeout_seconds)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"WebSocket streaming timeout after {timeout_seconds} seconds")
                    await stream_callback("Response timeout. Please try again.", is_complete=True)
                except Exception as e:
                    logger.error(f"Error during streaming: {e}")
                    await stream_callback("An error occurred during streaming.", is_complete=True)
                    
        except Exception as e:
            logger.error(f"Error during streaming WebSocket communication: {e}")
            await stream_callback("I apologize, but I encountered an error while processing your request. Please try again.", is_complete=True)
    
    def _build_conversation_history(
        self, 
        current_message: str, 
        context: List[ChatMessage], 
        agent: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build conversation history for OpenAI API"""
        messages = []
        
        # System prompt
        system_prompt = agent.get('persona_instructions') or agent.get('instructions', 'You are a helpful AI assistant.')
        messages.append({"role": "system", "content": system_prompt})
        
        # Add context messages (last 10 for efficiency)
        for msg in context[-10:]:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def _build_conversation_history_from_data(self, current_message: str, context: List[ChatMessage], agent_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build conversation history for agent using agent data from API"""
        messages = []
        
        # Add system prompt from agent instructions
        system_prompt = agent_data.get('instructions', 'You are a helpful AI assistant.')
        messages.append({"role": "system", "content": system_prompt})
        
        # Add context messages (last 10 for efficiency)
        for msg in context[-10:]:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def _parse_model_settings(self, model_settings_json: Optional[str]) -> Dict[str, Any]:
        """Parse model settings from JSON string"""
        default_settings = {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        if not model_settings_json:
            return default_settings
        
        try:
            settings = json.loads(model_settings_json)
            return {**default_settings, **settings}
        except json.JSONDecodeError:
            logger.warning("Failed to parse model settings, using defaults")
            return default_settings
    
    async def generate_streaming_response_with_callback(
        self,
        message: str,
        context: List[ChatMessage],
        agent: Dict[str, Any],
        callback: callable
    ):
        """Generate streaming response with callback for real-time updates via remote agent"""
        try:
            # Get agent instance name
            instance_name = agent.get('username') or agent.get('id', 'default')
            
            # Build conversation history
            messages = self._build_conversation_history(message, context, agent)
            model_settings = self._parse_model_settings(agent.get('model_settings'))
            
            # Call remote agent with streaming option
            session = await self.get_session()
            url = f"{self.agent_base_url}/agents/{instance_name}/chat"
            
            payload = {
                "input": message,
                "options": {
                    "model": model_settings.get("model", "gpt-4o-mini"),
                    "temperature": model_settings.get("temperature", 0.7),
                    "maxTokens": model_settings.get("max_tokens", 2000),
                    "messages": messages,
                    "stream": True
                }
            }
            
            async with session.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Ragwalla-Agent-Studio/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    # Handle streaming response
                    async for line in response.content:
                        if line:
                            try:
                                chunk = line.decode('utf-8').strip()
                                if chunk:
                                    await callback(chunk)
                            except Exception as e:
                                logger.error(f"Error processing stream chunk: {e}")
                else:
                    error_text = await response.text()
                    await callback(f"\n\n[Agent Error {response.status}: {error_text}]")
                    
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            await callback(f"\n\n[Connection Error: {str(e)}]")
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models from remote agent"""
        try:
            session = await self.get_session()
            url = f"{self.agent_base_url}/models"
            
            async with session.get(
                url,
                headers={"User-Agent": "Salvador-Agent/1.0"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    models = await response.json()
                    return models if isinstance(models, list) else ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
                else:
                    logger.warning(f"Failed to fetch models from agent: {response.status}")
                    return ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
                    
        except Exception as e:
            logger.error(f"Error fetching models from agent: {e}")
            return ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
    
    async def get_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents"""
        try:
            session = await self.get_session()
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "Ragwalla-Agent-Studio/1.0"
            }
            
            url = f"{self.agent_base_url}/agents"
            logger.info(f"Fetching agents from: {url}")
            logger.info(f"Using headers: {dict(headers)}")
            
            async with session.get(url, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Agent discovery response status: {response.status}")
                logger.info(f"Agent discovery response body: {response_text}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"Parsed JSON data: {data}")
                        
                        # Check different possible response structures
                        agents = []
                        if isinstance(data, list):
                            agents = data
                        elif isinstance(data, dict):
                            # Try different possible keys
                            agents = data.get('agents', data.get('data', data.get('results', [])))
                        
                        logger.info(f"Extracted {len(agents)} agents: {agents}")
                        return agents
                    except Exception as json_error:
                        logger.error(f"Failed to parse JSON response: {json_error}")
                        logger.error(f"Raw response: {response_text}")
                        return []
                else:
                    logger.error(f"Failed to get agents: {response.status} - {response_text}")
                    return []
        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            return []
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents"""
        return await self.get_agents()
    
    async def validate_agent_connection(self) -> bool:
        """Validate connection to remote agent"""
        try:
            session = await self.get_session()
            async with session.get(
                f"{self.agent_base_url}/agents",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Ragwalla-Agent-Studio/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Agent connection validation failed: {e}")
            return False
