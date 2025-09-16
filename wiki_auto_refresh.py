#!/usr/bin/env python3
"""
Auto-refresh system for Wiki.js content changes.
Monitors Wiki.js for content updates and triggers re-ingestion when needed.
"""

import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import schedule
from typing import Optional

from config import WIKI_BASE_URL, WIKI_API_KEY, WIKI_REFRESH_INTERVAL
from wiki_crawler import initialize_wiki_crawler
from logger import query_logger

class WikiAutoRefresh:
    def __init__(self):
        self.last_fetch_file = Path('.wiki_last_fetch')
        self.is_running = False
    
    def get_last_fetch_time(self) -> Optional[datetime]:
        """Get the last fetch timestamp"""
        try:
            if self.last_fetch_file.exists():
                with open(self.last_fetch_file, 'r') as f:
                    timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
            return None
        except Exception as e:
            query_logger.log_error(f"Failed to read last fetch time: {str(e)}")
            return None
    
    def save_fetch_time(self, fetch_time: datetime = None):
        """Save the fetch timestamp"""
        try:
            if fetch_time is None:
                fetch_time = datetime.now()
            
            with open(self.last_fetch_file, 'w') as f:
                f.write(fetch_time.isoformat())
        except Exception as e:
            query_logger.log_error(f"Failed to save fetch time: {str(e)}")
    
    def should_refresh(self) -> bool:
        """Check if it's time to refresh Wiki.js content"""
        try:
            if not WIKI_BASE_URL or WIKI_BASE_URL == 'http://localhost':
                return False
            
            last_fetch = self.get_last_fetch_time()
            if not last_fetch:
                # Never fetched before, should refresh
                return True
            
            # Check if enough time has passed since last fetch
            time_since_fetch = datetime.now() - last_fetch
            refresh_interval = timedelta(seconds=WIKI_REFRESH_INTERVAL)
            
            should_refresh = time_since_fetch >= refresh_interval
            
            if should_refresh:
                query_logger.logger.info(f"Wiki.js refresh needed - {time_since_fetch.total_seconds()}s since last fetch")
            
            return should_refresh
            
        except Exception as e:
            query_logger.log_error(f"Failed to check refresh status: {str(e)}")
            return False
    
    def test_wiki_availability(self) -> bool:
        """Test if Wiki.js is available"""
        try:
            if not WIKI_BASE_URL:
                return False
            
            crawler = initialize_wiki_crawler(WIKI_BASE_URL, WIKI_API_KEY)
            return crawler and crawler.test_connection()
            
        except Exception as e:
            query_logger.log_error(f"Wiki.js availability test failed: {str(e)}")
            return False
    
    def trigger_wiki_ingestion(self) -> bool:
        """Trigger Wiki.js content ingestion"""
        try:
            query_logger.logger.info("Triggering automatic Wiki.js ingestion")
            
            # Run the ingestion script for Wiki.js
            result = subprocess.run([
                'python', 'ingest.py', '--source', 'wiki'
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                query_logger.logger.info("Automatic Wiki.js ingestion completed successfully")
                self.save_fetch_time()
                return True
            else:
                query_logger.log_error(f"Wiki.js ingestion failed: {result.stderr}", "auto_refresh")
                return False
                
        except Exception as e:
            query_logger.log_error(f"Failed to trigger Wiki.js ingestion: {str(e)}", "auto_refresh")
            return False
    
    def refresh_job(self):
        """Job function for scheduled Wiki.js refreshes"""
        if self.is_running:
            query_logger.logger.info("Wiki.js refresh already running, skipping...")
            return
        
        self.is_running = True
        try:
            query_logger.logger.info("Checking Wiki.js for content updates...")
            
            # Test Wiki.js availability first
            if not self.test_wiki_availability():
                query_logger.logger.info("Wiki.js not available, skipping refresh")
                return
            
            # Check if refresh is needed
            if self.should_refresh():
                query_logger.logger.info("Refreshing Wiki.js content...")
                success = self.trigger_wiki_ingestion()
                
                if success:
                    query_logger.logger.info("Wiki.js content refresh completed successfully")
                else:
                    query_logger.log_error("Failed to complete Wiki.js content refresh")
            else:
                query_logger.logger.info("Wiki.js content is up to date")
                
        except Exception as e:
            query_logger.log_error(f"Wiki.js refresh job failed: {str(e)}", "auto_refresh")
        
        finally:
            self.is_running = False
    
    def start_scheduler(self):
        """Start the Wiki.js auto-refresh scheduler"""
        if not WIKI_BASE_URL or WIKI_BASE_URL == 'http://localhost':
            query_logger.logger.info("No Wiki.js URL configured or using default localhost, auto-refresh disabled")
            return
        
        # Convert seconds to minutes for schedule library
        interval_minutes = max(1, WIKI_REFRESH_INTERVAL // 60)
        
        query_logger.logger.info(f"Starting Wiki.js auto-refresh (checking every {interval_minutes} minutes)")
        query_logger.logger.info(f"Monitoring Wiki.js: {WIKI_BASE_URL}")
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(self.refresh_job)
        
        # Run initial check
        query_logger.logger.info("Running initial Wiki.js check...")
        self.refresh_job()
        
        # Keep the scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            query_logger.logger.info("Wiki.js auto-refresh scheduler stopped by user")
    
    def manual_refresh(self) -> bool:
        """Manually trigger a Wiki.js content refresh"""
        query_logger.logger.info("Manual Wiki.js refresh triggered")
        
        if not self.test_wiki_availability():
            query_logger.log_error("Wiki.js not available for refresh")
            return False
        
        return self.trigger_wiki_ingestion()

# Global auto-refresh instance
wiki_auto_refresh = WikiAutoRefresh()

def main():
    """Main function to run the Wiki.js auto-refresh scheduler"""
    print("Starting Wiki.js Auto-Refresh Scheduler...")
    try:
        wiki_auto_refresh.start_scheduler()
    except KeyboardInterrupt:
        print("\\nWiki.js auto-refresh scheduler stopped by user")
    except Exception as e:
        print(f"Wiki.js auto-refresh scheduler error: {str(e)}")

if __name__ == "__main__":
    main()