import os
import re
from pathlib import Path
from typing import List, Dict, Any
import markdown
from bs4 import BeautifulSoup
from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from logger import query_logger

class DocumentProcessor:
    def __init__(self):
        self.markdown_parser = markdown.Markdown(extensions=['meta', 'toc'])
        
    def load_documents(self) -> List[Dict[str, Any]]:
        """Load all documents from the data directory"""
        documents = []
        
        if not DATA_DIR.exists():
            query_logger.log_error("Data directory does not exist", str(DATA_DIR))
            return documents
            
        # Supported file extensions
        supported_extensions = {'.md', '.markdown', '.txt', '.html', '.htm'}
        
        for file_path in DATA_DIR.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    doc = self.load_document(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    query_logger.log_error(f"Failed to load document {file_path}: {str(e)}")
                    
        return documents
    
    def load_document(self, file_path: Path) -> Dict[str, Any]:
        """Load a single document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Determine file type and parse accordingly
            if file_path.suffix.lower() in {'.md', '.markdown'}:
                content = self.parse_markdown(content)
            elif file_path.suffix.lower() in {'.html', '.htm'}:
                content = self.parse_html(content)
            # .txt files are used as-is
            
            return {
                'content': content,
                'source': str(file_path.relative_to(DATA_DIR)),
                'title': file_path.stem,
                'path': str(file_path),
                'extension': file_path.suffix
            }
            
        except Exception as e:
            query_logger.log_error(f"Error loading document {file_path}: {str(e)}")
            return {}
    
    def parse_markdown(self, content: str) -> str:
        """Parse markdown content to plain text"""
        try:
            html = self.markdown_parser.convert(content)
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()
        except Exception as e:
            query_logger.log_error(f"Error parsing markdown: {str(e)}")
            return content  # Return raw content as fallback
    
    def parse_html(self, content: str) -> str:
        """Parse HTML content to plain text"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text()
        except Exception as e:
            query_logger.log_error(f"Error parsing HTML: {str(e)}")
            return content  # Return raw content as fallback
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks for vector storage"""
        chunks = []
        
        for doc in documents:
            doc_chunks = self.chunk_text(
                doc['content'], 
                doc['source'], 
                doc['title']
            )
            chunks.extend(doc_chunks)
            
        return chunks
    
    def chunk_text(self, text: str, source: str, title: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        chunks = []
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) <= CHUNK_SIZE:
            # If text is smaller than chunk size, return as single chunk
            chunks.append({
                'content': text,
                'source': source,
                'title': title,
                'chunk_id': 0,
                'start_char': 0,
                'end_char': len(text)
            })
            return chunks
        
        # Split into overlapping chunks
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + CHUNK_SIZE
            
            # Try to end at a sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                for i in range(min(100, CHUNK_SIZE // 4)):  # Look back up to 100 chars
                    if end - i > start and text[end - i] in '.!?':
                        end = end - i + 1
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    'content': chunk_text,
                    'source': source,
                    'title': title,
                    'chunk_id': chunk_id,
                    'start_char': start,
                    'end_char': end
                })
                chunk_id += 1
            
            # Move start position with overlap
            start = end - CHUNK_OVERLAP
            
            if start >= len(text):
                break
                
        return chunks

# Global processor instance
document_processor = DocumentProcessor()
