#!/usr/bin/env python3
"""
Ingestion script for the Institutional Memory system.
Reads documents from the data/ directory and builds a vector index.
"""

import sys
from pathlib import Path
from document_processor import document_processor
from vector_store import vector_store
from logger import query_logger
from config import DATA_DIR

def main():
    """Main ingestion function"""
    print("Starting document ingestion...")
    
    try:
        # Check if data directory exists
        if not DATA_DIR.exists():
            print(f"Error: Data directory {DATA_DIR} does not exist")
            sys.exit(1)
        
        # Load documents
        print(f"Loading documents from {DATA_DIR}...")
        documents = document_processor.load_documents()
        
        if not documents:
            print("No documents found to process")
            sys.exit(0)
        
        print(f"Loaded {len(documents)} documents")
        
        # Chunk documents
        print("Chunking documents...")
        chunks = document_processor.chunk_documents(documents)
        print(f"Created {len(chunks)} chunks")
        
        # Clear existing collection (re-index)
        print("Clearing existing vector store...")
        vector_store.clear_collection()
        
        # Add chunks to vector store
        print("Adding chunks to vector store...")
        success = vector_store.add_documents(chunks)
        
        if success:
            print("✅ Ingestion completed successfully!")
            query_logger.log_ingestion(len(documents), len(chunks))
            
            # Show collection info
            info = vector_store.get_collection_info()
            print(f"Collection '{info['name']}' now contains {info['count']} chunks")
            
            sys.exit(0)
        else:
            print("❌ Failed to add documents to vector store")
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        print(f"❌ {error_msg}")
        query_logger.log_error(error_msg, "ingestion")
        sys.exit(1)

if __name__ == "__main__":
    main()
