#!/usr/bin/env python3
"""
Simple test script to check API endpoints
"""
import requests
import json
import time

def test_api_endpoint(url, description):
    """Test an API endpoint"""
    print(f"\n🧪 Testing: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ JSON response received")
                if isinstance(data, dict) and 'error' in data:
                    print(f"❌ API Error: {data['error']}")
                else:
                    print("✅ Valid data received")
                    # Print first few keys if it's a dict
                    if isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        print(f"Keys: {keys}")
            except json.JSONDecodeError:
                # Might be Plotly JSON
                print("✅ Non-JSON response (possibly Plotly figure)")
                print(f"Content length: {len(response.text)} characters")
                # Check if it looks like Plotly JSON
                if '"data":' in response.text and '"layout":' in response.text:
                    print("✅ Looks like valid Plotly figure JSON")
                else:
                    print("❓ Unknown response format")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    base_url = "http://localhost:5000"
    
    print("🚀 Testing Aadhaar Analytics API Endpoints")
    print("=" * 50)
    print("⏳ Waiting for server to be ready...")
    
    # Wait for server to be ready
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/api/overview", timeout=5)
            if response.status_code in [200, 500]:  # Server is responding
                break
        except:
            pass
        time.sleep(2)
        print(f"   Attempt {i+1}/10...")
    
    # Test endpoints
    endpoints = [
        ("/api/overview", "National Overview"),
        ("/api/map/states", "State Map (default)"),
        ("/api/map/states?map_type=normalized", "State Map (normalized)"),
        ("/api/debug/states", "Debug States"),
        ("/api/test/simple-map", "Test Simple Map"),
    ]
    
    for endpoint, description in endpoints:
        test_api_endpoint(f"{base_url}{endpoint}", description)
    
    print("\n" + "=" * 50)
    print("✅ API testing completed!")