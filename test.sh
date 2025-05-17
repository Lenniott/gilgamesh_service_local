#!/bin/bash

# # Test 1: Instagram Post (could have videos, scenes, transcripts and/or images)
# echo "Testing Instagram Post..."
# curl -X POST "http://localhost:8500/process" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "url": "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
#     "encode_base64": false,
#     "cleanup_temp": false
#   }'
# echo -e "\n\n"

# # Test 2: Instagram Carousel
# echo "Testing Instagram Carousel..."
# curl -X POST "http://localhost:8500/process" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "url": "https://www.instagram.com/p/DJRiA-gI2GT/?igsh=bXI4MWJzNnhhMm5t",
#     "encode_base64": false,
#     "cleanup_temp": false
#   }'
# echo -e "\n\n"

# Test 3: Instagram Reel
echo "Testing Instagram Reel..."
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/DJVTMdRxRmJ/?igsh=eHJtN214OWpuMnIx",
    "encode_base64": false,
    "cleanup_temp": false
  }'
echo -e "\n\n"

# Test 4: YouTube Short
# echo "Testing YouTube Short..."
# curl -X POST "http://localhost:8500/process" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "url": "https://youtube.com/shorts/izeO1Vpqvvo?si=blnnaTO0uYEe5htC",
#     "encode_base64": false,
#     "cleanup_temp": false
#   }'
# echo -e "\n\n"

# Note: To run individual tests, you can comment out the ones you don't want to run
# Each test will:
# 1. Not encode videos/images as base64
# 2. Keep temporary files for inspection
# 3. Process each URL independently
# 4. Return file paths instead of base64 data

# To inspect temp files after running:
# 1. Look in the /tmp directory for folders starting with "gilgamesh_"
# 2. Each URL gets its own UUID-based temp directory
# 3. Inside each temp directory you'll find:
#    - Downloaded media files
#    - Frames directory (for videos)
#    - Any intermediate processing files 