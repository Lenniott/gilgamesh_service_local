#!/usr/bin/env python3
import requests
import sys
import time
from typing import Dict, Any

def check_health(url: str) -> bool:
    """Check if the service is healthy."""
    try:
        response = requests.get(f"{url}/health")
        return response.status_code == 200
    except requests.RequestException:
        return False

def test_process_endpoint(url: str) -> Dict[str, Any]:
    """Test the /process endpoint with a simple request."""
    test_url = "https://www.instagram.com/p/example"  # Replace with a real test URL
    payload = {
        "url": test_url,
        "cleanup_temp": True,
        "threshold": 0.22,
        "encode_base64": True
    }
    
    try:
        response = requests.post(f"{url}/process", json=payload)
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else None,
            "error": None
        }
    except Exception as e:
        return {
            "status_code": None,
            "response": None,
            "error": str(e)
        }

def main():
    base_url = "http://localhost:8500"
    max_retries = 5
    retry_delay = 2

    print("Starting smoke test...")
    
    # Check health endpoint
    for i in range(max_retries):
        print(f"Checking health endpoint (attempt {i + 1}/{max_retries})...")
        if check_health(base_url):
            print("✅ Health check passed")
            break
        if i < max_retries - 1:
            print(f"Health check failed, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    else:
        print("❌ Health check failed after all retries")
        sys.exit(1)

    # Test process endpoint
    print("\nTesting /process endpoint...")
    result = test_process_endpoint(base_url)
    
    if result["status_code"] == 200:
        print("✅ Process endpoint test passed")
        print(f"Response: {result['response']}")
    else:
        print("❌ Process endpoint test failed")
        print(f"Status code: {result['status_code']}")
        print(f"Error: {result['error']}")
        sys.exit(1)

    print("\n✅ All smoke tests passed!")

if __name__ == "__main__":
    main() 