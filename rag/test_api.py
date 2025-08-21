#!/usr/bin/env python3
"""
Test script for the FastAPI RAG service
"""

import asyncio
import httpx
import json
import time

async def test_api_endpoints():
    """Test all API endpoints"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        print("Testing FastAPI RAG Service")
        print("=" * 50)
        
        # Test 1: Root endpoint
        print("\n1. Testing root endpoint...")
        try:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("Root endpoint working")
                print(f"Response: {response.json()}")
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("Make sure to start the API with: uvicorn rag.api.main:app --reload")
            return
        
        # Test 2: Health check
        print("\n2. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Health endpoint working")
                print(f"Status: {health_data['status']}")
                print(f"Services: {health_data['services']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test 3: Search endpoint (will probably fail without Solr data)
        print("\n3. Testing search endpoint...")
        try:
            params = {
                "q": "tobacco excise",
                "top_k": 5
            }
            response = await client.get(f"{base_url}/search", params=params)
            if response.status_code == 200:
                search_data = response.json()
                print("✅ Search endpoint working")
                print(f"Found {search_data['total_found']} results")
                print(f"Response time: {search_data['response_time_ms']}ms")
            else:
                print(f"⚠️ Search endpoint returned {response.status_code}")
                print("This is expected if Solr doesn't have data yet")
        except Exception as e:
            print(f"❌ Search error: {e}")
        
        # Test 4: Ask endpoint
        print("\n4. Testing ask endpoint...")
        try:
            ask_data = {
                "question": "What is parliament?",
                "top_k": 5,
                "temperature": 0.1
            }
            
            start_time = time.time()
            response = await client.post(f"{base_url}/ask", json=ask_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                answer_data = response.json()
                print("✅ Ask endpoint working")
                print(f"Question: {answer_data['question']}")
                print(f"Answer: {answer_data['answer']}")
                print(f"Sources: {len(answer_data['sources'])}")
                print(f"Response time: {response_time:.2f}s")
                print(f"Model used: {answer_data['model_used']}")
            else:
                print(f"⚠️ Ask endpoint returned {response.status_code}")
                error_data = response.json()
                print(f"Error: {error_data}")
        except Exception as e:
            print(f"❌ Ask error: {e}")
        
        # Test 5: Models endpoint
        print("\n5. Testing models endpoint...")
        try:
            response = await client.get(f"{base_url}/models")
            if response.status_code == 200:
                models_data = response.json()
                print("✅ Models endpoint working")
                print(f"Available models: {models_data['models']}")
            else:
                print(f"❌ Models endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Models error: {e}")

def main():
    """Run the API tests"""
    print("Starting API tests...")
    print("Make sure the API is running with:")
    print("cd C:\\Users\\jacks\\pacific-hansard")
    print("uvicorn rag.api.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    
    try:
        asyncio.run(test_api_endpoints())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    
    print("\n" + "=" * 50)
    print("🎉 API testing complete!")
    print("\nNext steps:")
    print("1. Fix any failing endpoints")
    print("2. Add your Hansard data to Solr")
    print("3. Test with real parliamentary questions")

if __name__ == "__main__":
    main()