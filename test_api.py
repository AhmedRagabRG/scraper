#!/usr/bin/env python3
"""
Test script for Google Maps Scraper API
"""

import requests
import time
import sys

API_BASE_URL = "http://localhost:8000"

def test_api():
    """Test the API endpoints."""
    print("🧪 Testing Google Maps Scraper API")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1️⃣  Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to {API_BASE_URL}")
        print("   💡 Make sure the API server is running:")
        print("      python api.py")
        return False
    
    # Test 2: Root endpoint
    print("\n2️⃣  Testing root endpoint...")
    response = requests.get(f"{API_BASE_URL}/")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ API Name: {data.get('name')}")
        print(f"   ✅ Version: {data.get('version')}")
    else:
        print(f"   ❌ Root endpoint failed: {response.status_code}")
        return False
    
    # Test 3: Start scraping job
    print("\n3️⃣  Starting scraping job...")
    scrape_data = {
        "query": "Coffee Shops in Cairo",
        "max_results": 3,
        "headless": True
    }
    
    response = requests.post(f"{API_BASE_URL}/scrape", json=scrape_data)
    if response.status_code == 200:
        data = response.json()
        job_id = data.get('job_id')
        print(f"   ✅ Job started: {job_id}")
        print(f"   📝 Status: {data.get('status')}")
    else:
        print(f"   ❌ Failed to start job: {response.status_code}")
        return False
    
    # Test 4: Monitor job status
    print("\n4️⃣  Monitoring job status...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while True:
        if time.time() - start_time > max_wait:
            print("   ⏰ Timeout waiting for job completion")
            return False
        
        response = requests.get(f"{API_BASE_URL}/status/{job_id}")
        if response.status_code == 200:
            status = response.json()
            current_status = status.get('status')
            progress = status.get('progress', '')
            
            print(f"   📊 Status: {current_status} - {progress}")
            
            if current_status == 'completed':
                print(f"   ✅ Job completed!")
                print(f"   📈 Total results: {status.get('total_results')}")
                break
            elif current_status == 'failed':
                print(f"   ❌ Job failed: {status.get('error')}")
                return False
            
            time.sleep(5)
        else:
            print(f"   ❌ Failed to get status: {response.status_code}")
            return False
    
    # Test 5: Get results as JSON
    print("\n5️⃣  Getting results as JSON...")
    response = requests.get(f"{API_BASE_URL}/results/{job_id}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved {data.get('total_results')} results")
        
        # Show first result
        if data.get('results'):
            first = data['results'][0]
            print(f"\n   📍 Sample result:")
            print(f"      Name: {first.get('business_name')}")
            print(f"      Rating: {first.get('rating')}⭐")
            print(f"      Reviews: {first.get('review_count')}")
            if first.get('phone'):
                print(f"      Phone: {first.get('phone')}")
            if first.get('email'):
                print(f"      Email: {first.get('email')}")
    else:
        print(f"   ❌ Failed to get results: {response.status_code}")
        return False
    
    # Test 6: Download CSV
    print("\n6️⃣  Downloading CSV...")
    response = requests.get(f"{API_BASE_URL}/download/{job_id}")
    if response.status_code == 200:
        filename = f"test_results_{job_id}.csv"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   ✅ CSV downloaded: {filename}")
    else:
        print(f"   ❌ Failed to download CSV: {response.status_code}")
        return False
    
    # Test 7: List all jobs
    print("\n7️⃣  Listing all jobs...")
    response = requests.get(f"{API_BASE_URL}/jobs")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Total jobs: {data.get('total_jobs')}")
    else:
        print(f"   ❌ Failed to list jobs: {response.status_code}")
        return False
    
    # Test 8: Delete job (optional)
    print("\n8️⃣  Cleaning up (delete job)...")
    response = requests.delete(f"{API_BASE_URL}/job/{job_id}")
    if response.status_code == 200:
        print(f"   ✅ Job deleted successfully")
    else:
        print(f"   ⚠️  Failed to delete job: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed!")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
