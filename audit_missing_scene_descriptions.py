#!/usr/bin/env python3
"""
Audit Qdrant scene description collection for missing/placeholder descriptions.
Counts and lists all segments with missing or placeholder descriptions.
"""

import os
import sys
from collections import Counter

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db_connections import DatabaseConnections

import asyncio

def is_placeholder(description: str) -> bool:
    if not description:
        return True
    desc = description.strip().lower()
    return (
        desc == "descriptions not generated" or
        desc == "description not generated" or
        desc == "" or
        desc.startswith("No key frames available for analysis") or
        desc.startswith("n/a")
    )

async def audit_scene_descriptions():
    print("🔍 Auditing Qdrant scene description collection for missing/placeholder descriptions...")
    connections = DatabaseConnections()
    await connections.connect_all()
    qdrant = connections.qdrant_client
    collection_name = "video_scene_descriptions"
    
    # Get all points with pagination
    all_points = []
    offset = None
    while True:
        result, next_page = qdrant.scroll(collection_name=collection_name, limit=1000, offset=offset)
        all_points.extend(result)
        if not next_page:
            break
        offset = next_page
    print(f"Total points in collection: {len(all_points)}")
    
    # Extract all points with their IDs and descriptions
    points_data = []
    for pt in all_points:
        payload = getattr(pt, "payload", {})
        desc = payload.get("description") or payload.get("scene_description") or ""
        video_id = payload.get("video_id", "unknown")
        seg_id = getattr(pt, "id", None)
        points_data.append({
            "id": seg_id,
            "video_id": video_id,
            "description": desc
        })
    
    # Write to JSON file
    import json
    with open("scene_descriptions_audit.json", "w") as f:
        json.dump(points_data, f, indent=2)
    
    print(f"✅ Wrote {len(points_data)} points to scene_descriptions_audit.json")
    print("Done.")

if __name__ == "__main__":
    asyncio.run(audit_scene_descriptions()) 