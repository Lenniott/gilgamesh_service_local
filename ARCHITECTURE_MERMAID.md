# Gilgamesh Service Architecture - Mermaid Diagrams

## Overview
This document contains comprehensive Mermaid diagrams that serve as the programmatic "guiding star" for all documentation. These diagrams ensure consistency across data storage, API endpoints, and system components.

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "External Clients"
        CA[Client Apps]
        WI[Web Interface]
        AC[API Clients]
    end

    subgraph "FastAPI Application"
        API[API Endpoints]
        RL[Rate Limiting]
        HC[Health Checks]
        
        subgraph "Core Processing Pipeline"
            VP[Video Processing]
            SD[Scene Detection]
            AI[AI Analysis]
        end
    end

    subgraph "Data Storage Layer"
        PG[(PostgreSQL<br/>Metadata)]
        QD[(Qdrant<br/>Vectors)]
        FS[File Storage<br/>Video Clips]
    end

    subgraph "External Services"
        OA[OpenAI<br/>GPT-4]
        GA[Gemini<br/>2.0 Flash]
        YT[YouTube/Instagram<br/>APIs]
    end

    CA --> API
    WI --> API
    AC --> API
    
    API --> RL
    API --> HC
    
    API --> VP
    VP --> SD
    SD --> AI
    
    AI --> PG
    AI --> QD
    AI --> FS
    
    VP --> OA
    VP --> GA
    VP --> YT
```

## 2. Data Flow Architecture

```mermaid
flowchart TD
    subgraph "1. Input Processing"
        URL[URL Input]
        VAL[Validation]
        DL[Download Service]
        
        URL --> VAL
        VAL --> DL
    end

    subgraph "2. Video Processing"
        VD[Video Download]
        SD[Scene Detection]
        CE[Clip Extraction]
        
        DL --> VD
        VD --> SD
        SD --> CE
    end

    subgraph "3. AI Analysis"
        AE[Audio Extraction<br/>from Full Video]
        TG[Full Transcript<br/>with Timestamps]
        RT[Raw Transcript<br/>Text Only]
        LS[Link Scenes to<br/>Transcript Segments]
        SA[Scene Analysis using<br/>H.264 Key Frames<br/>(Significantly Different)]
        
        VD --> AE
        AE --> TG
        TG --> RT
        TG --> LS
        LS --> SA
    end

    subgraph "4. Storage & Indexing"
        MS[Metadata Storage]
        VI[Vector Indexing]
        FST[File Storage]
        
        SA --> MS
        TG --> MS
        RT --> MS
        TG --> VI
        CE --> FST
    end

    subgraph "5. Compilation"
        SM[Search & Match]
        SV[Stitch Videos]
        OG[Output Generation]
        
        VI --> SM
        SM --> SV
        SV --> OG
    end
```

## 3. Database Schema Architecture

```mermaid
erDiagram
    simple_videos {
        uuid id PK
        text url
        timestamp created_at
        text title
        float duration
        bigint file_size
        jsonb metadata
        text status
        jsonb video_metadata
        integer clip_storage_version
    }

    video_clips {
        uuid id PK
        uuid video_id FK
        uuid scene_id
        text clip_path
        float start_time
        float end_time
        float duration
        bigint file_size
        timestamp created_at
        timestamp updated_at
    }

    video_embeddings {
        uuid point_id PK
        vector vector_1536
        uuid video_id FK
        text type
        text content
        float timestamp
        json metadata
        float score
    }

    simple_videos ||--o{ video_clips : "has clips"
    simple_videos ||--o{ video_embeddings : "has embeddings"
```

## 4. API Endpoints Architecture

```mermaid
graph TB
    subgraph "Core Processing Endpoints"
        PROCESS[POST /process]
        PROCESS_PARAMS[url, save_video, transcribe, describe,<br/>save_to_postgres, save_to_qdrant,<br/>include_base64, raw_transcript]
    end

    subgraph "Vectorization Endpoints"
        VECTORIZE[POST /vectorize/existing]
        VECTORIZE_PARAMS[limit, dry_run, verbose]
        
        QDRANT_INDEX[POST /qdrant/force-index]
        QDRANT_PARAMS[collections, force_rebuild]
    end

    subgraph "Retrieval Endpoints"
        GET_VIDEO[GET /video/{video_id}]
        GET_VIDEO_PARAMS[video_id, include_base64]
        
        GET_CAROUSEL[GET /carousel]
        GET_CAROUSEL_PARAMS[url, include_base64]
        
        SEARCH[GET /search]
        SEARCH_PARAMS[q, limit]
        
        LIST_VIDEOS[GET /videos]
        LIST_VIDEOS_PARAMS[limit]
    end

    subgraph "System Endpoints"
        ROOT[GET /]
        HEALTH[GET /health]
        RATE_LIMITS[GET /rate-limits]
    end

    PROCESS --> PROCESS_PARAMS
    VECTORIZE --> VECTORIZE_PARAMS
    QDRANT_INDEX --> QDRANT_PARAMS
    GET_VIDEO --> GET_VIDEO_PARAMS
    GET_CAROUSEL --> GET_CAROUSEL_PARAMS
    SEARCH --> SEARCH_PARAMS
    LIST_VIDEOS --> LIST_VIDEOS_PARAMS
```

## 5. Processing Pipeline Architecture

```mermaid
stateDiagram-v2
    [*] --> URL_INPUT: Start
    
    URL_INPUT --> URL_VALIDATION: Validate URL
    URL_VALIDATION --> VIDEO_DOWNLOAD: URL Valid
    URL_VALIDATION --> ERROR: Invalid URL
    
    VIDEO_DOWNLOAD --> SCENE_DETECTION: Download Success
    VIDEO_DOWNLOAD --> ERROR: Download Failed
    
    SCENE_DETECTION --> CLIP_EXTRACTION: Scenes Detected
    SCENE_DETECTION --> ERROR: Detection Failed
    
    CLIP_EXTRACTION --> AUDIO_EXTRACTION: Clips Extracted
    CLIP_EXTRACTION --> ERROR: Extraction Failed
    
    AUDIO_EXTRACTION --> TRANSCRIPT_GENERATION: Audio Extracted
    AUDIO_EXTRACTION --> ERROR: Audio Failed
    
    TRANSCRIPT_GENERATION --> RAW_TRANSCRIPT: Timestamped Transcript Generated
    TRANSCRIPT_GENERATION --> ERROR: Transcript Failed
    
    RAW_TRANSCRIPT --> SCENE_LINKING: Raw Transcript Extracted
    RAW_TRANSCRIPT --> ERROR: Raw Transcript Failed
    
    SCENE_LINKING --> SCENE_ANALYSIS: Scenes Linked to Transcript
    SCENE_LINKING --> ERROR: Scene Linking Failed
    
    SCENE_ANALYSIS --> METADATA_STORAGE: Key Frame Analysis Complete
    SCENE_ANALYSIS --> ERROR: Scene Analysis Failed
    
    METADATA_STORAGE --> VECTOR_INDEXING: Metadata Stored
    METADATA_STORAGE --> ERROR: Storage Failed
    
    VECTOR_INDEXING --> FILE_STORAGE: Vectors Indexed
    VECTOR_INDEXING --> ERROR: Indexing Failed
    
    FILE_STORAGE --> COMPILATION: Files Stored
    FILE_STORAGE --> ERROR: File Storage Failed
    
    COMPILATION --> [*]: Success
    COMPILATION --> ERROR: Compilation Failed
    
    ERROR --> [*]: End with Error
```

## 6. Component Interaction Architecture

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant VP as VideoProcessor
    participant SD as SceneDetector
    participant AI as AIAnalyzer
    participant DB as Database
    participant QD as Qdrant
    participant FS as FileStorage
    participant OA as OpenAI
    participant GA as Gemini

    Client->>API: POST /process {url}
    API->>VP: Process Video
    VP->>SD: Detect Scenes
    SD->>VP: Return Scene Timestamps
    
    VP->>AI: Analyze Full Video
    AI->>GA: Generate Full Transcript<br/>with Timestamps
    GA->>AI: Return Timestamped Transcript
    
    AI->>AI: Extract Raw Transcript<br/>Text Only
    AI->>AI: Link Scenes to<br/>Transcript Segments
    AI->>OA: Analyze Key Frames<br/>(Significantly Different)
    OA->>AI: Return Scene Descriptions
    
    AI->>VP: Return Analysis Results
    VP->>DB: Store Metadata & Transcript
    VP->>QD: Store Vectors from Transcript
    VP->>FS: Store Video Clips
    
    VP->>API: Return Results
    API->>Client: Return Response
```

## 7. Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Network: gilgamesh-network"
        subgraph "API Container"
            API[gilgamesh-api<br/>Port: 8500]
            API_INTERNAL[FastAPI Application<br/>Video Processing<br/>AI Analysis<br/>Rate Limiting]
        end
        
        subgraph "Database Container"
            PG[postgres<br/>Port: 5432]
            PG_INTERNAL[PostgreSQL 15<br/>Metadata Storage<br/>User Data<br/>Clips Info]
        end
        
        subgraph "Vector DB Container"
            QD[qdrant<br/>Port: 6333]
            QD_INTERNAL[Qdrant Vector DB<br/>Embeddings<br/>Similarity Search]
        end
    end
    
    subgraph "Volume Mounts"
        PG_DATA[postgres_data<br/>Persistent]
        QD_DATA[qdrant_data<br/>Persistent]
        TEMP[./temp<br/>Temporary]
        CACHE[./cache<br/>Cache]
    end
    
    subgraph "External Connections"
        OA[OpenAI API]
        GA[Gemini API]
        YT[YouTube API]
        IG[Instagram API]
    end
    
    API --> PG
    API --> QD
    PG --> PG_DATA
    QD --> QD_DATA
    API --> TEMP
    API --> CACHE
    
    API --> OA
    API --> GA
    API --> YT
    API --> IG
```

## 8. Data Storage Strategy

```mermaid
graph TB
    subgraph "Metadata Storage (PostgreSQL)"
        PG[(PostgreSQL)]
        SV[simple_videos table]
        VC[video_clips table]
        
        SV --> PG
        VC --> PG
    end
    
    subgraph "Vector Storage (Qdrant)"
        QD[(Qdrant)]
        VE[video_embeddings collection]
        
        VE --> QD
    end
    
    subgraph "File Storage (Local/Network)"
        FS[File Storage]
        CLIPS[/storage/clips/]
        YEAR[2024/]
        MONTH[01/, 02/, 03/]
        VIDEO[video_id_1/]
        SCENE[scene_001.mp4<br/>scene_002.mp4]
        
        CLIPS --> YEAR
        YEAR --> MONTH
        MONTH --> VIDEO
        VIDEO --> SCENE
        SCENE --> FS
    end
    
    subgraph "Cache Storage (Temporary)"
        CACHE[Cache Storage]
        TEMP[/app/cache/]
        DOWNLOADS[Downloaded Videos]
        ARTIFACTS[Processing Artifacts]
        OUTPUTS[AI Model Outputs]
        
        TEMP --> DOWNLOADS
        TEMP --> ARTIFACTS
        TEMP --> OUTPUTS
        OUTPUTS --> CACHE
    end
```

## 9. Rate Limiting & Circuit Breaker Architecture

```mermaid
stateDiagram-v2
    [*] --> CLOSED: Normal Operation
    
    CLOSED --> CLOSED: Success
    CLOSED --> OPEN: Failure Threshold Reached
    
    OPEN --> HALF_OPEN: Timeout Expired
    
    HALF_OPEN --> CLOSED: Success Threshold Reached
    HALF_OPEN --> OPEN: Failure
    
    OPEN --> OPEN: Still in Timeout
    HALF_OPEN --> HALF_OPEN: Testing
```

## 10. Error Handling Flow

```mermaid
flowchart TD
    REQUEST[API Request] --> VALIDATE{Validate Input}
    VALIDATE -->|Valid| PROCESS[Process Request]
    VALIDATE -->|Invalid| ERROR_400[400 Bad Request]
    
    PROCESS --> DB_CHECK{Database Available?}
    DB_CHECK -->|Yes| AI_CHECK{AI Service Available?}
    DB_CHECK -->|No| ERROR_503[503 Service Unavailable]
    
    AI_CHECK -->|Yes| RATE_CHECK{Rate Limit OK?}
    AI_CHECK -->|No| FALLBACK[Use Fallback Provider]
    
    RATE_CHECK -->|Yes| EXECUTE[Execute Processing]
    RATE_CHECK -->|No| ERROR_429[429 Too Many Requests]
    
    FALLBACK --> RATE_CHECK
    EXECUTE --> SUCCESS[Success Response]
    EXECUTE --> ERROR_500[500 Internal Server Error]
    
    ERROR_400 --> END[End]
    ERROR_503 --> END
    ERROR_429 --> END
    ERROR_500 --> END
    SUCCESS --> END
```

## 11. Health Check Architecture

```mermaid
graph TB
    subgraph "Health Check Endpoints"
        HEALTH[GET /health]
        RATE_LIMITS[GET /rate-limits]
    end
    
    subgraph "Health Checks"
        DB_HEALTH[Database Health]
        AI_HEALTH[AI Provider Health]
        QD_HEALTH[Qdrant Health]
        FS_HEALTH[File Storage Health]
    end
    
    subgraph "Status Responses"
        OK[200 OK]
        DEGRADED[200 Degraded]
        ERROR[503 Error]
    end
    
    HEALTH --> DB_HEALTH
    HEALTH --> AI_HEALTH
    HEALTH --> QD_HEALTH
    HEALTH --> FS_HEALTH
    
    DB_HEALTH --> OK
    AI_HEALTH --> OK
    QD_HEALTH --> OK
    FS_HEALTH --> OK
    
    RATE_LIMITS --> OK
```

## Usage Guidelines

### For Documentation Consistency
1. **Reference these Mermaid diagrams** in all documentation files
2. **Maintain consistency** with the data flow and component interactions shown
3. **Update diagrams** when architecture changes are made
4. **Use consistent terminology** across all documentation

### For Development
1. **Follow the data flow** shown in the processing pipeline
2. **Respect the API contract** defined in the endpoints architecture
3. **Maintain the database schema** structure shown
4. **Adhere to the deployment** patterns illustrated

### For Testing
1. **Test each component** according to the interaction architecture
2. **Validate data flow** through the processing pipeline
3. **Verify API endpoints** match the defined contract
4. **Check storage consistency** across all data stores

## Notes
- **Scalability**: Architecture supports horizontal scaling of API containers
- **Reliability**: Circuit breaker and rate limiting ensure system stability
- **Maintainability**: Clear separation of concerns between components
- **Extensibility**: Modular design allows for easy addition of new features
- **Monitoring**: Built-in health checks and metrics for all components 