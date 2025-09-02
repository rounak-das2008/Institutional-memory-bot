import os
import requests
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import base64
from logger import query_logger

class GitHubCrawler:
    def __init__(self, repo_url: str, token: str = None):
        """
        Initialize GitHub crawler
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo)
            token: GitHub personal access token (optional, for private repos or higher rate limits)
        """
        self.repo_url = repo_url
        self.token = token
        self.api_base = "https://api.github.com"
        
        # Parse repo URL to get owner and repo name
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            self.owner = path_parts[0]
            self.repo = path_parts[1]
        else:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        # Setup headers for API requests
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Institutional-Memory-Bot/1.0'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get basic repository information"""
        try:
            url = f"{self.api_base}/repos/{self.owner}/{self.repo}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            query_logger.log_error(f"Failed to get repo info: {str(e)}", f"Repo: {self.repo_url}")
            return {}
    
    def get_latest_commit(self) -> Optional[Dict[str, Any]]:
        """Get the latest commit information"""
        try:
            url = f"{self.api_base}/repos/{self.owner}/{self.repo}/commits"
            response = requests.get(url, headers=self.headers, params={'per_page': 1})
            response.raise_for_status()
            commits = response.json()
            return commits[0] if commits else None
        except Exception as e:
            query_logger.log_error(f"Failed to get latest commit: {str(e)}", f"Repo: {self.repo_url}")
            return None
    
    def get_content_tree(self, path: str = "", recursive: bool = True) -> List[Dict[str, Any]]:
        """Get all files and directories in the repository"""
        try:
            url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{path}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            contents = response.json()
            if not isinstance(contents, list):
                # Single file
                return [contents] if self._is_supported_file(contents.get('name', '')) else []
            
            files = []
            for item in contents:
                if item['type'] == 'file' and self._is_supported_file(item['name']):
                    files.append(item)
                elif item['type'] == 'dir' and recursive:
                    # Recursively get files from subdirectories
                    sub_files = self.get_content_tree(item['path'], recursive=True)
                    files.extend(sub_files)
            
            return files
            
        except Exception as e:
            query_logger.log_error(f"Failed to get content tree: {str(e)}", f"Path: {path}")
            return []
    
    def _is_supported_file(self, filename: str) -> bool:
        """Check if file is supported for ingestion"""
        supported_extensions = {'.md', '.markdown', '.txt', '.html', '.htm', '.rst'}
        return any(filename.lower().endswith(ext) for ext in supported_extensions)
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a specific file"""
        try:
            url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            file_data = response.json()
            if file_data.get('encoding') == 'base64':
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return content
            else:
                return file_data.get('content', '')
                
        except Exception as e:
            query_logger.log_error(f"Failed to get file content: {str(e)}", f"File: {file_path}")
            return None
    
    def fetch_all_documents(self) -> List[Dict[str, Any]]:
        """Fetch all supported documents from the repository"""
        try:
            query_logger.logger.info(f"Fetching documents from {self.repo_url}")
            
            # Get all supported files
            files = self.get_content_tree()
            documents = []
            
            for file_info in files:
                content = self.get_file_content(file_info['path'])
                if content:
                    # Parse file extension to determine type
                    file_path = Path(file_info['path'])
                    
                    doc = {
                        'content': content,
                        'source': f"github:{self.owner}/{self.repo}:{file_info['path']}",
                        'title': file_path.stem,
                        'path': file_info['path'],
                        'extension': file_path.suffix,
                        'github_url': file_info['html_url'],
                        'last_modified': file_info.get('last_modified', datetime.now().isoformat()),
                        'sha': file_info.get('sha', '')
                    }
                    documents.append(doc)
            
            query_logger.logger.info(f"Fetched {len(documents)} documents from GitHub")
            return documents
            
        except Exception as e:
            query_logger.log_error(f"Failed to fetch documents: {str(e)}", f"Repo: {self.repo_url}")
            return []
    
    def check_for_updates(self, last_known_commit: str) -> bool:
        """Check if there are new commits since the last known commit"""
        try:
            latest_commit = self.get_latest_commit()
            if not latest_commit:
                return False
            
            latest_sha = latest_commit['sha']
            return latest_sha != last_known_commit
            
        except Exception as e:
            query_logger.log_error(f"Failed to check for updates: {str(e)}")
            return False
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get GitHub API rate limit information"""
        try:
            url = f"{self.api_base}/rate_limit"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            query_logger.log_error(f"Failed to get rate limit info: {str(e)}")
            return {}

# Global instances (will be initialized when needed)
github_crawler = None

def initialize_github_crawler(repo_url: str, token: str = None) -> GitHubCrawler:
    """Initialize the global GitHub crawler instance"""
    global github_crawler
    if repo_url:
        github_crawler = GitHubCrawler(repo_url, token)
        return github_crawler
    return None