#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_agent_details():
    """Check agent details to find the correct assistantId"""
    
    agent_base_url = os.getenv("AGENT_BASE_URL")
    api_token = os.getenv("RAGWALLA_API_KEY")
    agent_id = os.getenv("DEFAULT_AGENT_ID")
    
    if not agent_base_url:
        print("❌ ERROR: AGENT_BASE_URL environment variable is required")
        return
    
    if not api_token:
        print("❌ ERROR: RAGWALLA_API_KEY environment variable is required")
        return
    
    if not agent_id:
        print("❌ ERROR: DEFAULT_AGENT_ID environment variable is required")
        return
    
    print(f"Checking agent details for: {agent_id}")
    print(f"Base URL: {agent_base_url}")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "User-Agent": "Ragwalla-Agent-Studio/2.0"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Get agent details
            async with session.get(
                f"{agent_base_url}/agents/{agent_id}",
                headers=headers
            ) as response:
                
                print(f"Response status: {response.status}")
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        print("✅ Agent details:")
                        print(json.dumps(data, indent=2))
                        
                        # Look for assistant-related fields
                        assistant_id = data.get('assistantId') or data.get('assistant_id') or data.get('openai_assistant_id')
                        if assistant_id:
                            print(f"\n🎯 Found Assistant ID: {assistant_id}")
                        else:
                            print("\n❓ No obvious Assistant ID found in response")
                            
                    except json.JSONDecodeError:
                        print(f"❌ Could not parse JSON response: {response_text}")
                else:
                    print(f"❌ Failed to get agent details: {response.status}")
                    print(f"Response: {response_text}")
                    
        except Exception as e:
            print(f"❌ Error checking agent details: {e}")

if __name__ == "__main__":
    asyncio.run(check_agent_details())
