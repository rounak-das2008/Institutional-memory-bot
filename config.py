import os
from pathlib import Path

# Paths
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
VECTOR_DB_DIR = Path("chroma_db")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
VECTOR_DB_DIR.mkdir(exist_ok=True)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")

# Vector Store Configuration
COLLECTION_NAME = "institutional_memory"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval Configuration
TOP_K_RESULTS = 5
SIMILARITY_THRESHOLD = 0.5

# Model Configuration
EMBEDDING_MODEL = "gemini-2.5-flash"
GENERATION_MODEL = "gemini-2.5-flash"

# System Prompt Template
SYSTEM_PROMPT = """You are an institutional memory assistant that helps users find information from technical documentation.

Your task is to answer questions using ONLY the provided context chunks from the knowledge base. 

Guidelines:
1. Base your answer ONLY on the provided context chunks
2. If the context doesn't contain enough information, say so clearly
3. Always cite which source documents/chunks you used
4. Provide step-by-step instructions when applicable
5. Do not hallucinate or make up information not present in the context
6. If multiple versions exist, clearly distinguish between them

Context chunks:
{context}

User question: {question}

Please provide a helpful answer with source citations."""
