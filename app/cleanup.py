#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

def cleanup_temp_folder():
    """
    Clean out the entire temp folder in the app directory.
    """
    # Get the temp directory path
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    
    if not os.path.exists(temp_dir):
        print("Temp directory does not exist.")
        return
    
    try:
        # Remove the entire temp directory and recreate it
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        print(f"Successfully cleaned temp directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning temp directory: {e}")

if __name__ == '__main__':
    # If run directly, clean the temp folder
    cleanup_temp_folder() 