#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

def cleanup_temp_folder(temp_dir):
    """
    Clean out the specified temp directory.
    """
    if not os.path.exists(temp_dir):
        print(f"Temp directory {temp_dir} does not exist.")
        return
    try:
        shutil.rmtree(temp_dir)
        print(f"Successfully cleaned temp directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning temp directory {temp_dir}: {e}")

if __name__ == '__main__':
    # If run directly, clean the temp folder
    cleanup_temp_folder(os.path.join(os.path.dirname(__file__), 'temp')) 