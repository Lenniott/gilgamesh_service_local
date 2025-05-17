#!/bin/bash

echo "Testing Async Implementation"
echo "==========================="

# Test 1: Single URL Processing (Instagram Post)
echo -e "\nTest 1: Single URL Processing (Instagram Post)"
curl -X POST http://localhost:8500/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
    "cleanup_temp": true,
    "encode_base64": false
  }' | jq '.'

# Test 2: Batch Processing (Multiple URLs)
echo -e "\n\nTest 2: Batch Processing (Multiple URLs)"
curl -X POST http://localhost:8500/process/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
      "https://www.instagram.com/p/DJRiA-gI2GT/?igsh=bXI4MWJzNnhhMm5t",
      "https://www.instagram.com/reel/DJVTMdRxRmJ/?igsh=eHJtN214OWpuMnIx"
    ],
    "cleanup_temp": true,
    "encode_base64": false
  }' | jq '.'

# Test 3: Concurrent Error Handling
echo -e "\n\nTest 3: Concurrent Error Handling"
curl -X POST http://localhost:8500/process/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
      "https://invalid-url.com",
      "https://youtube.com/shorts/izeO1Vpqvvo?si=blnnaTO0uYEe5htC"
    ],
    "cleanup_temp": true,
    "encode_base64": false
  }' | jq '.'

# Test 4: Cache Stats After Processing
echo -e "\n\nTest 4: Cache Stats After Processing"
curl -X GET http://localhost:8500/cache/stats | jq '.'

# Test 5: Cleanup and Verify
echo -e "\n\nTest 5: Cleanup and Verify"
curl -X POST http://localhost:8500/cleanup \
  -H "Content-Type: application/json" \
  -d '{"clear_cache_data": true, "encode_base64": false}' | jq '.'

# Test 6: Cache Stats After Cleanup
echo -e "\n\nTest 6: Cache Stats After Cleanup"
curl -X GET http://localhost:8500/cache/stats | jq '.'

echo -e "\n\nAsync Implementation Tests Completed" 