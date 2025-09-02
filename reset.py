#!/usr/bin/env python3
"""
Reset script for the Institutional Memory system.
Clears the vector database and logs.
"""

import sys
import shutil
from pathlib import Path
from vector_store import vector_store
from config import VECTOR_DB_DIR, LOGS_DIR

def main():
    """Main reset function"""
    print("Resetting Institutional Memory system...")
    
    try:
        # Clear vector store
        print("Clearing vector database...")
        success = vector_store.clear_collection()
        
        if success:
            print("✅ Vector database cleared")
        else:
            print("⚠️  Warning: Failed to clear vector database")
        
        # Optionally clear logs
        response = input("Do you want to clear logs as well? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            if LOGS_DIR.exists():
                shutil.rmtree(LOGS_DIR)
                LOGS_DIR.mkdir(exist_ok=True)
                print("✅ Logs cleared")
            else:
                print("ℹ️  No logs to clear")
        
        # Optionally clear vector database files
        response = input("Do you want to remove all vector database files? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            if VECTOR_DB_DIR.exists():
                shutil.rmtree(VECTOR_DB_DIR)
                print("✅ Vector database files removed")
            else:
                print("ℹ️  No vector database files to remove")
        
        print("✅ Reset completed successfully!")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Reset failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
