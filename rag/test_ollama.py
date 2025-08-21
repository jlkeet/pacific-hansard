#!/usr/bin/env python3
"""
Test script for Ollama LLM integration with Hansard chunks
"""

import json
import time
import requests
from typing import List, Dict

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollama is running!")
            print(f"Available models: {[m['name'] for m in models.get('models', [])]}")
            return True
        else:
            print(f"❌ Ollama responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("Make sure Ollama is running with: ollama serve")
        return False

def download_deepseek_r1():
    """Download Deepseek R1 8B model"""
    print("📥 Downloading Deepseek R1 8B model...")
    print("This will take several minutes and ~4.7GB of disk space.")
    
    try:
        response = requests.post(
            "http://localhost:11434/api/pull",
            json={"name": "deepseek-r1:8b"},
            stream=True,
            timeout=1800  # 30 minutes timeout
        )
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'status' in data:
                    print(f"Status: {data['status']}")
                if 'completed' in data and 'total' in data:
                    progress = (data['completed'] / data['total']) * 100
                    print(f"Progress: {progress:.1f}%")
                    
        print("✅ Deepseek R1 8B model downloaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False

def test_basic_generation():
    """Test basic text generation"""
    print("\n🧪 Testing basic text generation...")
    
    prompt = "What is parliament? Answer in one sentence."
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test successful!")
            print(f"Prompt: {prompt}")
            print(f"Response: {result.get('response', 'No response')}")
            return True
        else:
            print(f"❌ Generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error in generation: {e}")
        return False

def test_hansard_qa():
    """Test Q&A with sample Hansard content"""
    print("\n🏛️ Testing Hansard Q&A...")
    
    # Sample Hansard chunks
    chunks = [
        {
            "id": "test-doc-001_chunk_1",
            "speaker": "HON. JANE SMITH",
            "date": "2023-06-15",
            "text": "Mr. Speaker, I rise to ask the Minister of Health about the tobacco excise policy. What measures is the government taking to reduce smoking rates in our community?",
            "url": "/article.php?id=1"
        },
        {
            "id": "test-doc-001_chunk_2", 
            "speaker": "HON. MINISTER OF HEALTH",
            "date": "2023-06-15",
            "text": "Thank you, Mr. Speaker. The government has implemented a comprehensive tobacco control strategy. We have increased excise taxes by 10% annually for the past four years. Additionally, we have expanded smoking cessation programs in all health districts.",
            "url": "/article.php?id=1"
        }
    ]
    
    question = "What did the Minister of Health say about tobacco excise taxes?"
    
    # Build context from chunks
    context = "\n\n".join([
        f"[#{i}] Speaker: {chunk['speaker']} | Date: {chunk['date']}\n{chunk['text']}"
        for i, chunk in enumerate(chunks)
    ])
    
    prompt = f"""Answer using ONLY the provided Hansard excerpts. If not found in them, say: "Not found in the provided records." Attach [#id] after supported sentences.

Question: {question}

Excerpts:
{context}

Instructions:
- Be concise and neutral
- Include citation [#id] after each supported sentence
- Include a short "Sources" list with speaker/date
"""

    try:
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for factual responses
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            },
            timeout=60
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', 'No response')
            
            print(f"✅ Hansard Q&A test successful!")
            print(f"⏱️ Response time: {response_time:.2f} seconds")
            print(f"\nQuestion: {question}")
            print(f"\nAnswer: {answer}")
            
            # Check for citations
            if '[#' in answer:
                print("✅ Citations found in response")
            else:
                print("⚠️ No citations found - may need prompt tuning")
                
            return True, response_time
        else:
            print(f"❌ Hansard Q&A failed with status {response.status_code}")
            return False, 0
            
    except Exception as e:
        print(f"❌ Error in Hansard Q&A: {e}")
        return False, 0

def test_performance_benchmark():
    """Test performance with multiple queries"""
    print("\n⚡ Running performance benchmark...")
    
    questions = [
        "What are the main topics discussed?",
        "Who are the speakers in this session?", 
        "What policies were mentioned?",
        "What dates are covered?",
        "What questions were asked?"
    ]
    
    times = []
    successful = 0
    
    for i, question in enumerate(questions):
        print(f"Test {i+1}/5: {question}")
        
        try:
            start_time = time.time()
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "deepseek-r1:8b",
                    "prompt": f"Answer in one sentence: {question}",
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = end_time - start_time
                times.append(response_time)
                successful += 1
                print(f"  ✅ {response_time:.2f}s")
            else:
                print(f"  ❌ Failed")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"\n📊 Performance Results:")
        print(f"Successful: {successful}/{len(questions)}")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Min time: {min_time:.2f}s") 
        print(f"Max time: {max_time:.2f}s")
        
        if avg_time < 3.0:
            print("✅ Performance target met (< 3.0s average)")
        else:
            print("⚠️ Performance target missed (> 3.0s average)")
            print("Consider using 4-bit quantization: ollama run llama3:8b-q4_0")

def main():
    """Run all Ollama tests"""
    print("🚀 Ollama LLM Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Connection
    if not test_ollama_connection():
        print("\n❌ Cannot proceed without Ollama connection")
        print("Please install and start Ollama:")
        print("1. Run the OllamaSetup.exe installer")
        print("2. Open a new terminal and run: ollama serve")
        print("3. Run this test again")
        return
    
    # Test 2: Model download (skip since you're downloading manually)
    print("\n" + "=" * 50)
    print("Using Deepseek R1 8B model (downloading manually in Ollama)...")
    
    # Test 3: Basic generation
    print("\n" + "=" * 50)
    if not test_basic_generation():
        return
    
    # Test 4: Hansard Q&A
    print("\n" + "=" * 50)
    success, response_time = test_hansard_qa()
    
    # Test 5: Performance benchmark
    print("\n" + "=" * 50)
    test_performance_benchmark()
    
    print("\n" + "=" * 50)
    print("🎉 Ollama testing complete!")
    print("Next steps:")
    print("1. Integrate with FastAPI service")
    print("2. Connect to Solr for hybrid search")
    print("3. Build full RAG pipeline")

if __name__ == "__main__":
    main()