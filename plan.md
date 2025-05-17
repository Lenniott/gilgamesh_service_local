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
- [ ] Idempotency (Optional)
  - [ ] Evaluate caching strategy
  - [ ] Implement URL-based caching if needed

## Phase 3 - Performance & Resource Management
- [ ] Async I/O Implementation
  - [ ] Convert downloaders to async
  - [ ] Update FastAPI handlers (partially done)
  - [ ] Implement asyncio.to_thread for blocking calls
- [ ] Background Task Cleanup
  - [x] Implement FastAPI BackgroundTasks (structure in place)
  - [ ] Test cleanup reliability
- [ ] Rate Limiting
  - [ ] Add asyncio.Queue for request management
  - [ ] Implement concurrency limits

## Phase 4 - Testing & Validation
- [ ] Unit Tests
  - [ ] Test `process_single_url` with various media types
  - [ ] Mock external service calls
  - [ ] Test error handling
- [ ] Integration Tests
  - [ ] Docker container testing
  - [ ] Multi-URL request validation
  - [ ] Cleanup verification
- [ ] Edge Cases
  - [ ] Empty URL list handling (done)
  - [ ] Unsupported URL handling
  - [ ] Concurrent request testing

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
- Completed Phase 1: Foundations & Input API
- Moving to Phase 2: Error Handling & Idempotency
- Next task: Implement caching strategy for idempotency

## Notes
- Keep implementation simple and well-documented
- Focus on LLM IDE friendliness
- Maintain clear input→output mapping
- Ensure proper error handling at each stage

## Recent Changes
1. Implemented `process_single_url` with UUID-based temp directories
2. Updated FastAPI endpoint with proper response models and error handling
3. Added OpenAPI documentation
4. Improved error isolation per URL
5. Added type hints and docstrings for better code clarity
6. Added `encode_base64` option to control media encoding in responses 