# Media Processing Service Refactor Plan

## Overview
Refactor the media processing service to improve structure, performance, and maintainability. The goal is to create a more robust, async-first service that can handle multiple videos efficiently while maintaining a clean output structure.

## Phase 1: Core Structure and Data Models

### Current Analysis
- Basic Pydantic models for request validation
- Synchronous and blocking processing
- Basic error handling with try/except blocks
- Loosely defined data structures (using dictionaries)
- No clear separation between API, business logic, and data models

### Key Issues to Address
1. No proper data validation for complex nested structures
2. Synchronous processing blocks the event loop
3. Error handling is inconsistent and lacks proper error types
4. No progress tracking or status updates
5. Temporary file management is scattered

### Proposed Directory Structure
```
app/
├── api/
│   ├── __init__.py
│   ├── routes.py          # FastAPI route definitions
│   └── dependencies.py    # Shared dependencies
├── core/
│   ├── __init__.py
│   ├── config.py         # Configuration management
│   └── errors.py         # Custom error types
├── models/
│   ├── __init__.py
│   ├── request.py        # Request models
│   ├── response.py       # Response models
│   └── common.py         # Shared models
├── services/
│   ├── __init__.py
│   ├── media.py          # Media processing service
│   ├── download.py       # Download service
│   └── storage.py        # Temporary storage management
└── utils/
    ├── __init__.py
    └── helpers.py        # Shared utilities
```

### Implementation Tasks
- [x] Create new data models using Pydantic for input/output validation
  - [x] Implement common models (TranscriptSegment, SceneCut, VideoMetadata, ProcessingStatus)
  - [x] Implement request models (ProcessRequest, BatchProcessRequest)
  - [x] Implement response models (VideoResult, ProcessResponse)
  - [x] Add validation rules and field constraints
- [x] Set up FastAPI async endpoint structure
  - [x] Create base router and endpoints
  - [x] Implement request validation
  - [x] Add basic error handling
  - [x] Add async processing support (stub)
- [x] Add testing infrastructure
  - [x] Set up test directory structure
  - [x] Add model validation tests
  - [x] Add API endpoint tests (stub)

### Commit Strategy
1. [x] "Add core Pydantic models"
2. [x] "Add FastAPI async structure"
3. [x] "Add processing status tracking" (stub only)

## Phase X: Integration, End-to-End, and Blocked Tasks

These tasks require the completion of all core service layers and orchestration. They are blocked until the rest of the refactor is complete.

- [ ] Integration tests for the full processing pipeline  
  _Blocked: Requires all service layers and async orchestration to be implemented._
- [ ] Add status tracking to processing pipeline  
  _Blocked: Requires real async/queue-based processing._
- [ ] Update tests for real service layer  
  _Blocked: Requires refactored service logic._
- [ ] Final refactor of API to use new service layer  
  _Blocked: Requires all business logic to be modularized and tested._
- [ ] End-to-end validation and QA  
  _Blocked: Requires all above to be in place._

## Phase 2: Media Processing Pipeline
- [x] Refactor media download system
  - [x] Create async download handler
  - [x] Implement carousel detection
  - [x] Add temporary storage management
  - [x] Add proper error handling
  - [x] Implement cleanup mechanisms
- [ ] Implement new scene processing pipeline
  - [ ] Refactor scene detection to be more efficient
  - [ ] Update frame extraction logic
  - [ ] Modify OCR processing to work with new structure
- [ ] Update transcription system
  - [ ] Ensure async compatibility
  - [ ] Add proper error handling
  - [ ] Implement progress tracking

## Phase 3: Performance and Scalability
- [ ] Implement async processing
  - [ ] Convert blocking operations to async
  - [ ] Add proper resource management
  - [ ] Implement concurrency limits
- [ ] Add task queue system
  - [ ] Set up Celery + Redis (or alternative)
  - [ ] Create task status tracking
  - [ ] Implement result caching
- [ ] Add resource isolation
  - [ ] Implement per-request temp directories
  - [ ] Add cleanup mechanisms
  - [ ] Set up proper logging

## Phase 4: API and Response Handling
- [ ] Implement new response structure
  - [ ] Create JSON response builder
  - [ ] Add proper error responses
  - [ ] Implement partial success handling
- [ ] Add status endpoint
  - [ ] Create task status tracking
  - [ ] Implement progress reporting
  - [ ] Add result retrieval endpoint

## Phase 5: Testing and Documentation
- [ ] Add comprehensive tests
  - [ ] Unit tests for core functions
  - [ ] Integration tests for full pipeline
  - [ ] Load testing for performance
- [ ] Update documentation
  - [ ] API documentation
  - [ ] Setup instructions
  - [ ] Usage examples

## Current Issues to Address
1. Blocking operations in media processing
2. Lack of proper error handling
3. No progress tracking
4. Resource management issues
5. No proper task queuing
6. Inefficient scene processing

## Success Criteria
- [ ] All endpoints respond within 200ms for status checks
- [ ] Processing pipeline can handle multiple concurrent requests
- [ ] Memory usage remains stable under load
- [ ] Failed requests don't affect other processing
- [ ] All operations are properly logged
- [ ] Results are cached appropriately
- [ ] Clean, maintainable code structure

## Notes
- Keep existing functionality working during refactor
- Implement changes incrementally
- Add tests before major changes
- Monitor performance metrics
- Document all major decisions 