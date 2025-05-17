#!/bin/bash

# Test cleanup functionality
echo "Testing cleanup functionality..."

# 1. Test cleanup after processing with cleanup_temp=true
echo "Test 1: Cleanup after processing (cleanup_temp=true)..."
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv"],
    "encode_base64": false,
    "cleanup_temp": true
  }'
echo -e "\n\n"

# 2. Test cleanup after processing with cleanup_temp=false
echo "Test 2: No cleanup after processing (cleanup_temp=false)..."
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv"],
    "encode_base64": false,
    "cleanup_temp": false
  }'
echo -e "\n\n"

# 3. Test manual cleanup endpoint
echo "Test 3: Manual cleanup endpoint..."
curl -X POST "http://localhost:8500/cleanup?clear_cache=true"
echo -e "\n\n"

# 4. Test cache stats after cleanup
echo "Test 4: Cache stats after cleanup..."
curl -X GET "http://localhost:8500/cache/stats"
echo -e "\n\n"

# 5. Test cleanup with invalid URL (error handling)
echo "Test 5: Cleanup with invalid URL..."
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://invalid-url-that-will-fail.com"],
    "encode_base64": false,
    "cleanup_temp": true
  }'
echo -e "\n\n"

# 6. Test cleanup with multiple URLs (some valid, some invalid)
echo "Test 6: Cleanup with mixed valid/invalid URLs..."
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
      "https://invalid-url-that-will-fail.com"
    ],
    "encode_base64": false,
    "cleanup_temp": true
  }'
echo -e "\n\n"

# 7. Final cleanup and stats check
echo "Test 7: Final cleanup and stats check..."
curl -X POST "http://localhost:8500/cleanup?clear_cache=true"
echo -e "\n"
curl -X GET "http://localhost:8500/cache/stats"
echo -e "\n\n"

echo "Cleanup tests completed. Check the output above for any errors." 