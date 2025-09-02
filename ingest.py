#!/usr/bin/env python3
"""
Ingestion script for the Institutional Memory system.
Reads documents from the data/ directory and builds a vector index.
"""

import sys
from pathlib import Path
from datetime import datetime
from document_processor import document_processor
from vector_store import vector_store
from logger import query_logger
from config import DATA_DIR, WIKI_BASE_URL, WIKI_API_KEY
from wiki_crawler import initialize_wiki_crawler

def main():
    """Main ingestion function"""
    import argparse
    parser = argparse.ArgumentParser(description='Ingest documents into the knowledge base')
    parser.add_argument('--source', choices=['local', 'wiki'], default='auto', 
                       help='Source of documents (local files or Wiki.js)')
    parser.add_argument('--wiki-url', type=str, help='Wiki.js base URL')
    parser.add_argument('--wiki-api-key', type=str, help='Wiki.js API key')
    args = parser.parse_args()
    
    print("Starting document ingestion...")
    
    try:
        documents = []
        source_type = args.source
        
        # Auto-detect source type
        if source_type == 'auto':
            wiki_url = args.wiki_url or WIKI_BASE_URL
            if wiki_url and wiki_url != 'http://localhost:3000':
                source_type = 'wiki'
            elif DATA_DIR.exists() and any(DATA_DIR.iterdir()):
                source_type = 'local'
            else:
                print("No data source found. Please provide either local files or Wiki.js URL.")
                sys.exit(1)
        
        if source_type == 'wiki':
            # Wiki.js ingestion
            wiki_url = args.wiki_url or WIKI_BASE_URL
            wiki_api_key = args.wiki_api_key or WIKI_API_KEY
            
            if not wiki_url:
                print("Error: Wiki.js base URL is required")
                print("Set WIKI_BASE_URL environment variable or use --wiki-url")
                sys.exit(1)
            
            print(f"Loading documents from Wiki.js instance: {wiki_url}")
            crawler = initialize_wiki_crawler(wiki_url, wiki_api_key)
            if not crawler:
                print("Failed to initialize Wiki.js crawler")
                sys.exit(1)
            
            # Test connection
            if not crawler.test_connection():
                print(f"Warning: Cannot connect to Wiki.js at {wiki_url}")
                print("Make sure your Wiki.js instance is running and accessible")
            
            # Fetch documents from Wiki.js
            documents = crawler.fetch_all_documents()
            
            # Store fetch timestamp for change detection
            with open('.wiki_last_fetch', 'w') as f:
                f.write(datetime.now().isoformat())
            print(f"Fetched at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        else:
            # Local file ingestion
            if not DATA_DIR.exists():
                print(f"Error: Data directory {DATA_DIR} does not exist")
                sys.exit(1)
            
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
