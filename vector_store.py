import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path
from config import VECTOR_DB_DIR, COLLECTION_NAME, TOP_K_RESULTS
from gemini_client import gemini_client
from logger import query_logger

class VectorStore:
    def __init__(self):
        self.client = None
        self.collection = None
        self.initialize_client()
        
    def initialize_client(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Institutional memory knowledge base"}
            )
            
        except Exception as e:
            query_logger.log_error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def add_documents(self, chunks: List[Dict[str, Any]]) -> bool:
        """Add document chunks to the vector store"""
        try:
            if not chunks:
                return True
                
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                # Generate unique ID for each chunk
                chunk_id = str(uuid.uuid4())
                
                documents.append(chunk['content'])
                metadatas.append({
                    'source': chunk.get('source', ''),
                    'title': chunk.get('title', ''),
                    'chunk_id': chunk.get('chunk_id', 0),
                    'start_char': chunk.get('start_char', 0),
                    'end_char': chunk.get('end_char', 0)
                })
                ids.append(chunk_id)
            
            # Generate embeddings
            embeddings = gemini_client.generate_embeddings(documents)
            
            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
            
        except Exception as e:
            query_logger.log_error(f"Failed to add documents to vector store: {str(e)}")
            return False
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for relevant chunks using semantic similarity"""
        try:
            if top_k is None:
                top_k = TOP_K_RESULTS
                
            # Generate query embedding
            query_embedding = gemini_client.generate_embedding(query)
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            chunks = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    chunks.append({
                        'content': doc,
                        'source': metadata.get('source', ''),
                        'title': metadata.get('title', ''),
                        'chunk_id': metadata.get('chunk_id', 0),
                        'similarity_score': 1 - distance,  # Convert distance to similarity
                        'rank': i + 1
                    })
            
            return chunks
            
        except Exception as e:
            query_logger.log_error(f"Failed to search vector store: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                'name': COLLECTION_NAME,
                'count': count,
                'status': 'ready' if count > 0 else 'empty'
            }
        except Exception as e:
            query_logger.log_error(f"Failed to get collection info: {str(e)}")
            return {'name': COLLECTION_NAME, 'count': 0, 'status': 'error'}
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection"""
        try:
            # Delete the collection
            self.client.delete_collection(name=COLLECTION_NAME)
            
            # Recreate the collection
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Institutional memory knowledge base"}
            )
            
            return True
            
        except Exception as e:
            query_logger.log_error(f"Failed to clear collection: {str(e)}")
            return False

# Global vector store instance
vector_store = VectorStore()
