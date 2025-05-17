# Gilgamesh Service Refactor Plan

## Phase 1 - Foundations & Input API
- [x] Clarify API contract
  - [x] Document exact response shape for each URL type (Instagram post, carousel, reel, YouTube)
  - [x] Add OpenAPI/Swagger documentation
  - [x] Validate current `/process` endpoint accepts `{"urls": [...]}` format
- [x] Isolate per-URL work
  - [x] Create `process_single_url(url) → dict` wrapper function
  - [x] Refactor `process_and_cleanup` to use new wrapper
  - [x] Ensure proper temp directory management with UUIDs
- [x] Linearize multi-URL sequencing
  - [x] Implement sequential processing in `download_handler`
  - [x] Add proper error handling per URL
  - [x] Test temp directory isolation

## Phase 2 - Error Handling & Idempotency
- [x] Per-URL error isolation
  - [x] Implement try/except blocks for each URL
  - [x] Define error response format
  - [x] Ensure consistent array length in responses
- [x] Idempotency
  - [x] Implement file-based caching with TTL
  - [x] Add cache management endpoints
  - [x] Integrate caching with process endpoint
  - [x] Add background task caching
  - [x] Implement thread-safe cache operations

## Phase 3 - Performance & Resource Management
- [x] Async I/O Implementation
  - [x] Convert downloaders to async
  - [x] Update FastAPI handlers
  - [x] Implement asyncio.to_thread for blocking calls
  - [x] Fix encode_base64 functionality
- [x] Background Task Cleanup
  - [x] Implement FastAPI BackgroundTasks
  - [x] Test cleanup reliability
- [ ] Rate Limiting
  - [ ] Add asyncio.Queue for request management
  - [ ] Implement concurrency limits
  - [ ] Add request timeout handling

## Phase 4 - Testing & Validation
- [x] Basic Testing
  - [x] Test script for various URL types
  - [x] Test encode_base64 functionality
  - [x] Test cleanup behavior
- [ ] Unit Tests
  - [ ] Test `process_single_url` with various media types
  - [ ] Mock external service calls
  - [ ] Test error handling
  - [ ] Test cache behavior
- [ ] Integration Tests
  - [ ] Docker container testing
  - [ ] Multi-URL request validation
  - [ ] Cleanup verification
  - [ ] Load testing with concurrent requests
- [ ] Edge Cases
  - [x] Empty URL list handling
  - [x] Unsupported URL handling
  - [ ] Concurrent request testing
  - [ ] Test with very large media files
  - [ ] Test with corrupted media files

## Phase 5 - CI/CD & Release Stages
- [ ] Alpha (Internal Dev)
  - [ ] Set up dev branch
  - [ ] Configure automated tests
  - [ ] Implement Docker smoke tests
- [ ] Beta (Staging)
  - [ ] Deploy to staging environment
  - [ ] Run real-world tests
  - [ ] Monitor performance metrics
- [ ] Production Release
  - [ ] Version tagging
  - [ ] Docker image publication
  - [ ] Deployment update
  - [ ] Monitoring setup

## Current Focus
- Completed Phase 3: Async I/O Implementation
- Moving to Phase 4: Testing & Validation
- Next tasks:
  1. Implement comprehensive unit tests
  2. Add rate limiting and request timeout handling
  3. Set up Docker container testing

## Notes
- Keep implementation simple and well-documented
- Focus on LLM IDE friendliness
- Maintain clear input→output mapping
- Ensure proper error handling at each stage
- Monitor memory usage with large media files
- Consider adding request timeout configuration

## Recent Changes
1. Implemented `process_single_url` with UUID-based temp directories
2. Updated FastAPI endpoint with proper response models and error handling
3. Added OpenAPI documentation
4. Improved error isolation per URL
5. Added type hints and docstrings for better code clarity
6. Added `encode_base64` option to control media encoding in responses
7. Implemented URL-based caching with file storage and TTL
8. Added `cleanup_temp` option to control temporary file and cache cleanup
9. Verified background task cleanup reliability with comprehensive tests
10. Converted downloaders and handlers to async
11. Implemented asyncio.to_thread for blocking operations
12. Fixed encode_base64 functionality to properly respect the flag
13. Added test script for various URL types and configurations 