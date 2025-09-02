import os
from typing import List, Dict, Any
from google import genai
from google.genai import types
import json
from config import GEMINI_API_KEY, EMBEDDING_MODEL, GENERATION_MODEL, SYSTEM_PROMPT
from logger import query_logger

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = []
            for text in texts:
                response = self.client.models.embed_content(
                    model="models/text-embedding-004",
                    contents=text
                )
                embeddings.append(response.embeddings[0].values)
            return embeddings
        except Exception as e:
            query_logger.log_error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = self.client.models.embed_content(
                model="models/text-embedding-004",
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            query_logger.log_error(f"Failed to generate embedding: {str(e)}")
            raise
            
    def generate_response(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate response using RAG with context chunks"""
        try:
            # Format context from chunks
            context = "\n\n".join([
                f"Source: {chunk.get('source', 'Unknown')}\n{chunk.get('content', '')}"
                for chunk in context_chunks
            ])
            
            # Create prompt
            prompt = SYSTEM_PROMPT.format(context=context, question=question)
            
            response = self.client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt
            )
            
            return response.text or "I couldn't generate a response. Please try again."
            
        except Exception as e:
            query_logger.log_error(f"Failed to generate response: {str(e)}")
            return f"Error generating response: {str(e)}"

# Global client instance
gemini_client = GeminiClient()
