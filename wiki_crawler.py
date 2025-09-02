import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup

from logger import query_logger

class WikiJSCrawler:
    def __init__(self, base_url: str, api_key: str = None):
        """
        Initialize Wiki.js crawler
        
        Args:
            base_url: Wiki.js base URL (e.g., http://localhost:3000)
            api_key: Wiki.js API key (optional, for private wikis)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        
        # Setup headers for API requests
        self.headers = {
            'User-Agent': 'Institutional-Memory-Bot/1.0',
            'Content-Type': 'application/json'
        }
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def test_connection(self) -> bool:
        """Test if Wiki.js is accessible"""
        try:
            response = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            # Try alternative health check endpoints
            try:
                response = requests.get(f"{self.base_url}/", headers=self.headers, timeout=10)
                return response.status_code == 200
            except:
                return False
    
    def get_all_pages_via_api(self) -> List[Dict[str, Any]]:
        """Get all pages using Wiki.js GraphQL API"""
        try:
            # Wiki.js GraphQL endpoint
            graphql_url = f"{self.base_url}/graphql"
            
            # GraphQL query to get all pages
            query = """
            query {
                pages {
                    list {
                        id
                        path
                        title
                        description
                        content
                        contentType
                        createdAt
                        updatedAt
                        tags {
                            tag
                        }
                    }
                }
            }
            """
            
            response = requests.post(
                graphql_url,
                json={'query': query},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'pages' in data['data'] and 'list' in data['data']['pages']:
                    pages = data['data']['pages']['list']
                    query_logger.logger.info(f"Retrieved {len(pages)} pages via GraphQL API")
                    return pages
            
            query_logger.log_error(f"GraphQL API failed: {response.status_code}")
            return []
            
        except Exception as e:
            query_logger.log_error(f"Failed to get pages via API: {str(e)}")
            return []
    
    def get_all_pages_via_scraping(self) -> List[Dict[str, Any]]:
        """Get all pages by scraping Wiki.js (fallback method)"""
        try:
            query_logger.logger.info("Attempting to scrape Wiki.js pages...")
            
            # Try to get sitemap or page listing
            pages = []
            
            # Try common Wiki.js patterns
            sitemap_urls = [
                f"{self.base_url}/sitemap.xml",
                f"{self.base_url}/all",
                f"{self.base_url}/pages",
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    response = requests.get(sitemap_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        if 'sitemap.xml' in sitemap_url:
                            pages = self._parse_sitemap(response.content)
                        else:
                            pages = self._parse_page_listing(response.content)
                        
                        if pages:
                            break
                except:
                    continue
            
            if not pages:
                # Try to discover pages by crawling from root
                pages = self._discover_pages_from_root()
            
            query_logger.logger.info(f"Retrieved {len(pages)} pages via scraping")
            return pages
            
        except Exception as e:
            query_logger.log_error(f"Failed to scrape pages: {str(e)}")
            return []
    
    def _parse_sitemap(self, sitemap_content: bytes) -> List[Dict[str, Any]]:
        """Parse XML sitemap to extract page URLs"""
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(sitemap_content)
            
            pages = []
            # Handle different sitemap namespaces
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None:
                    url = loc_elem.text
                    if url and url != self.base_url and not url.endswith('/'):
                        page_info = self._fetch_page_content(url)
                        if page_info:
                            pages.append(page_info)
            
            return pages
            
        except Exception as e:
            query_logger.log_error(f"Failed to parse sitemap: {str(e)}")
            return []
    
    def _parse_page_listing(self, html_content: bytes) -> List[Dict[str, Any]]:
        """Parse HTML page listing to extract page URLs"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            pages = []
            
            # Look for common Wiki.js page link patterns
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and not href.startswith(('http', '#', 'mailto:', 'javascript:')):
                    # Convert relative URL to absolute
                    full_url = urljoin(self.base_url, href)
                    
                    # Skip common non-content URLs
                    if not any(skip in href.lower() for skip in ['login', 'register', 'admin', 'api', 'search', 'upload']):
                        page_info = self._fetch_page_content(full_url)
                        if page_info:
                            pages.append(page_info)
            
            return pages
            
        except Exception as e:
            query_logger.log_error(f"Failed to parse page listing: {str(e)}")
            return []
    
    def _discover_pages_from_root(self) -> List[Dict[str, Any]]:
        """Discover pages by crawling from the root URL"""
        try:
            discovered_urls = set()
            pages = []
            
            # Start with root page
            root_page = self._fetch_page_content(self.base_url)
            if root_page:
                pages.append(root_page)
                
                # Look for internal links in the root page
                soup = BeautifulSoup(root_page.get('raw_content', ''), 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and not href.startswith(('http', '#', 'mailto:', 'javascript:')):
                        full_url = urljoin(self.base_url, href)
                        
                        # Only process internal URLs
                        if urlparse(full_url).netloc == urlparse(self.base_url).netloc:
                            if full_url not in discovered_urls and len(discovered_urls) < 50:  # Limit crawling
                                discovered_urls.add(full_url)
                                page_info = self._fetch_page_content(full_url)
                                if page_info:
                                    pages.append(page_info)
            
            return pages
            
        except Exception as e:
            query_logger.log_error(f"Failed to discover pages: {str(e)}")
            return []
    
    def _fetch_page_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch content from a single Wiki.js page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract page title
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text().strip() if title_elem else urlparse(url).path.split('/')[-1]
            
            # Remove Wiki.js navigation and UI elements
            for element in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                element.decompose()
            
            # Remove elements with common Wiki.js CSS classes
            for class_name in ['v-navigation-drawer', 'v-toolbar', 'v-footer', 'wiki-sidebar']:
                for element in soup.find_all(class_=re.compile(class_name)):
                    element.decompose()
            
            # Extract main content
            content_selectors = [
                '.wiki-page-content',
                '.page-content', 
                'main',
                '.content',
                'article',
                '.markdown-body'
            ]
            
            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break
            
            if not content_elem:
                content_elem = soup.find('body') or soup
            
            # Clean up the content
            clean_content = self._clean_html_content(content_elem.get_text())
            
            if not clean_content or len(clean_content.strip()) < 50:
                return None
            
            # Extract path from URL
            path = urlparse(url).path
            
            return {
                'id': path,
                'path': path,
                'title': title,
                'content': clean_content,
                'contentType': 'html',
                'url': url,
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat(),
                'tags': [],
                'raw_content': str(content_elem)
            }
            
        except Exception as e:
            query_logger.log_error(f"Failed to fetch page content from {url}: {str(e)}")
            return None
    
    def _clean_html_content(self, text: str) -> str:
        """Clean and normalize extracted text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common Wiki.js UI text
        ui_texts = [
            'Edit this page',
            'Page history', 
            'Print this page',
            'Last modified',
            'Created by',
            'Table of contents'
        ]
        
        for ui_text in ui_texts:
            text = text.replace(ui_text, '')
        
        return text.strip()
    
    def fetch_all_documents(self) -> List[Dict[str, Any]]:
        """Fetch all Wiki.js documents, trying API first then scraping"""
        try:
            query_logger.logger.info(f"Fetching documents from Wiki.js at {self.base_url}")
            
            # Test connection first
            if not self.test_connection():
                query_logger.log_error(f"Cannot connect to Wiki.js at {self.base_url}")
                return []
            
            # Try API first (more reliable)
            pages = self.get_all_pages_via_api()
            
            # Fallback to scraping if API fails
            if not pages:
                query_logger.logger.info("API failed, falling back to web scraping")
                pages = self.get_all_pages_via_scraping()
            
            # Convert to standard document format
            documents = []
            for page in pages:
                doc = {
                    'content': page.get('content', ''),
                    'source': f"wiki:{page.get('path', page.get('id', 'unknown'))}",
                    'title': page.get('title', 'Untitled'),
                    'path': page.get('path', page.get('id', 'unknown')),
                    'extension': '.html',
                    'wiki_url': page.get('url', f"{self.base_url}{page.get('path', '')}"),
                    'last_modified': page.get('updatedAt', page.get('createdAt', datetime.now().isoformat())),
                    'tags': [tag.get('tag', '') if isinstance(tag, dict) else str(tag) for tag in page.get('tags', [])]
                }
                
                # Only include pages with meaningful content
                if doc['content'] and len(doc['content'].strip()) > 100:
                    documents.append(doc)
            
            query_logger.logger.info(f"Successfully retrieved {len(documents)} Wiki.js pages")
            return documents
            
        except Exception as e:
            query_logger.log_error(f"Failed to fetch Wiki.js documents: {str(e)}")
            return []

# Global instance (will be initialized when needed)
wiki_crawler = None

def initialize_wiki_crawler(base_url: str, api_key: str = None) -> WikiJSCrawler:
    """Initialize the global Wiki.js crawler instance"""
    global wiki_crawler
    if base_url:
        wiki_crawler = WikiJSCrawler(base_url, api_key)
        return wiki_crawler
    return None