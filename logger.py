import logging
import json
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR

class QueryLogger:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = LOGS_DIR / "queries.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def log_query(self, query: str, retrieved_chunks: list, response: str, feedback: str = None):
        """Log a query with its results and feedback"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "retrieved_chunks": [
                {
                    "content": chunk.get("content", "")[:200] + "...",  # Truncate for logging
                    "source": chunk.get("source", ""),
                    "similarity_score": chunk.get("similarity_score", 0)
                }
                for chunk in retrieved_chunks
            ],
            "response": response[:500] + "..." if len(response) > 500 else response,
            "feedback": feedback
        }
        
        self.logger.info(f"Query logged: {json.dumps(log_entry, indent=2)}")
        
        # Also save to JSON file for structured analysis
        json_log_file = LOGS_DIR / "queries.json"
        
        # Load existing logs or create new list
        if json_log_file.exists():
            with open(json_log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
            
        logs.append(log_entry)
        
        # Save updated logs
        with open(json_log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    def log_ingestion(self, files_processed: int, chunks_created: int):
        """Log ingestion statistics"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "ingestion",
            "files_processed": files_processed,
            "chunks_created": chunks_created
        }
        
        self.logger.info(f"Ingestion completed: {json.dumps(log_entry)}")
        
    def log_error(self, error_message: str, context: str = ""):
        """Log errors"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "error": error_message,
            "context": context
        }
        
        self.logger.error(f"Error: {json.dumps(log_entry)}")

# Global logger instance
query_logger = QueryLogger()
