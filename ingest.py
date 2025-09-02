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
from config import DATA_DIR, GITHUB_REPO_URL, GITHUB_TOKEN
from github_crawler import initialize_github_crawler
from chat_sessions import chat_session_manager

def main():
    """Main ingestion function"""
    import argparse
    parser = argparse.ArgumentParser(description='Ingest documents into the knowledge base')
    parser.add_argument('--source', choices=['local', 'github'], default='auto', 
                       help='Source of documents (local files or GitHub repo)')
    parser.add_argument('--repo-url', type=str, help='GitHub repository URL')
    parser.add_argument('--github-token', type=str, help='GitHub token for private repos')
    args = parser.parse_args()
    
    print("Starting document ingestion...")
    
    try:
        documents = []
        source_type = args.source
        
        # Auto-detect source type
        if source_type == 'auto':
            repo_url = args.repo_url or GITHUB_REPO_URL
            if repo_url:
                source_type = 'github'
            elif DATA_DIR.exists() and any(DATA_DIR.iterdir()):
                source_type = 'local'
            else:
                print("No data source found. Please provide either local files or GitHub repo URL.")
                sys.exit(1)
        
        if source_type == 'github':
            # GitHub ingestion
            repo_url = args.repo_url or GITHUB_REPO_URL
            github_token = args.github_token or GITHUB_TOKEN
            
            if not repo_url:
                print("Error: GitHub repository URL is required")
                print("Set GITHUB_REPO_URL environment variable or use --repo-url")
                sys.exit(1)
            
            print(f"Loading documents from GitHub repository: {repo_url}")
            crawler = initialize_github_crawler(repo_url, github_token)
            if not crawler:
                print("Failed to initialize GitHub crawler")
                sys.exit(1)
            
            # Get repository info
            repo_info = crawler.get_repo_info()
            if repo_info:
                print(f"Repository: {repo_info.get('full_name', 'Unknown')}")
                print(f"Description: {repo_info.get('description', 'No description')}")
            
            # Fetch documents from GitHub
            documents = crawler.fetch_all_documents()
            
            # Store latest commit info for update detection
            latest_commit = crawler.get_latest_commit()
            if latest_commit:
                with open('.github_last_commit', 'w') as f:
                    f.write(latest_commit['sha'])
                print(f"Latest commit: {latest_commit['sha'][:8]}")
        
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
