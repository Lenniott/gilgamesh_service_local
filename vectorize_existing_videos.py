#!/usr/bin/env python3
"""
Vectorize Existing Videos Script

This script finds all videos in the PostgreSQL database that haven't been vectorized yet
and processes them to add vector embeddings to Qdrant.

Usage:
    python vectorize_existing_videos.py [--limit N] [--dry-run]

Options:
    --limit N    : Only process N videos (default: no limit)
    --dry-run    : Show what would be processed without actually doing it
    --verbose    : Show detailed logging
"""

import asyncio
import argparse
import logging

# Import the vectorization class from the app module
from app.vectorization import VectorizeExistingVideos

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the vectorization script."""
    parser = argparse.ArgumentParser(description="Vectorize existing videos that haven't been vectorized yet")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without actually doing it")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    vectorizer = VectorizeExistingVideos()
    
    try:
        # Initialize
        await vectorizer.initialize()
        
        # Run vectorization
        result = await vectorizer.vectorize_all_unvectorized(
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        # Print final result
        print("\n" + "="*50)
        print("VECTORIZATION SUMMARY")
        print("="*50)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        if result.get('total_videos'):
            print(f"Total videos: {result['total_videos']}")
            print(f"Processed: {result['processed']}")
            print(f"Successful: {result['successful']}")
            print(f"Failed: {result['failed']}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        print(f"\n❌ Error: {e}")
        
    finally:
        await vectorizer.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 