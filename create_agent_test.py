#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_test_agent():
    """Create a test agent for the current API key"""
    
    agent_base_url = os.getenv("AGENT_BASE_URL")
    api_token = os.getenv("RAGWALLA_API_KEY")
    
    if not agent_base_url:
        print("❌ ERROR: AGENT_BASE_URL environment variable is required")
        return
    
    if not api_token:
        print("❌ ERROR: RAGWALLA_API_KEY environment variable is required")
        return
    
    print(f"Creating agent with API key: {api_token[:10]}...")
    print(f"Base URL: {agent_base_url}")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "User-Agent": "Ragwalla-Agent-Studio/2.0"
    }
    
    # Agent creation payload
    agent_data = {
        "name": "ragwalla-test-agent",
        "description": "Test agent for Ragwalla Agent Studio integration",
        "model": "gpt-4o-mini",
        "instructions": "You are a helpful AI assistant for testing purposes."
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Try to create an agent
            async with session.post(
                f"{agent_base_url}/agents",
                headers=headers,
                json=agent_data
            ) as response:
                
                print(f"Response status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text}")
                
                if response.status == 201 or response.status == 200:
                    try:
                        data = json.loads(response_text)
                        agent_id = data.get('id') or data.get('agent_id') or data.get('agentId')
                        print(f"✅ Agent created successfully!")
                        print(f"Agent ID: {agent_id}")
                        return agent_id
                    except json.JSONDecodeError:
                        print("✅ Agent creation response received, but couldn't parse JSON")
                        return "created"
                else:
                    print(f"❌ Failed to create agent: {response.status}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error creating agent: {e}")
            return None

if __name__ == "__main__":
    asyncio.run(create_test_agent())
