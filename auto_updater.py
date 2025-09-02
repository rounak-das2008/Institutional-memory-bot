#!/usr/bin/env python3
"""
Auto-updater for GitHub repository changes.
Monitors GitHub repos for changes and triggers re-ingestion.
"""

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
import schedule
from typing import Optional

from config import GITHUB_REPO_URL, GITHUB_TOKEN, AUTO_UPDATE_INTERVAL
from github_crawler import initialize_github_crawler
from logger import query_logger

class AutoUpdater:
    def __init__(self):
        self.last_commit_file = Path('.github_last_commit')
        self.is_running = False
    
    def get_last_known_commit(self) -> Optional[str]:
        """Get the last known commit SHA"""
        try:
            if self.last_commit_file.exists():
                with open(self.last_commit_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            query_logger.log_error(f"Failed to read last commit: {str(e)}")
            return None
    
    def save_last_commit(self, commit_sha: str):
        """Save the latest commit SHA"""
        try:
            with open(self.last_commit_file, 'w') as f:
                f.write(commit_sha)
        except Exception as e:
            query_logger.log_error(f"Failed to save last commit: {str(e)}")
    
    def check_for_updates(self) -> bool:
        """Check if there are updates available"""
        if not GITHUB_REPO_URL:
            return False
        
        try:
            crawler = initialize_github_crawler(GITHUB_REPO_URL, GITHUB_TOKEN)
            if not crawler:
                return False
            
            last_known = self.get_last_known_commit()
            if not last_known:
                # First time setup - consider there are updates
                return True
            
            has_updates = crawler.check_for_updates(last_known)
            if has_updates:
                latest_commit = crawler.get_latest_commit()
                if latest_commit:
                    query_logger.logger.info(f"New commit detected: {latest_commit['sha'][:8]}")
                    query_logger.logger.info(f"Commit message: {latest_commit['commit']['message'][:100]}...")
                    return True
            
            return False
            
        except Exception as e:
            query_logger.log_error(f"Failed to check for updates: {str(e)}")
            return False
    
    def trigger_ingestion(self) -> bool:
        """Trigger the ingestion process"""
        try:
            query_logger.logger.info("Triggering automatic ingestion due to GitHub updates")
            
            # Run the ingestion script
            result = subprocess.run([
                'python', 'ingest.py', '--source', 'github'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                query_logger.logger.info("Automatic ingestion completed successfully")
                return True
            else:
                query_logger.log_error(f"Ingestion failed: {result.stderr}", "auto_updater")
                return False
                
        except Exception as e:
            query_logger.log_error(f"Failed to trigger ingestion: {str(e)}", "auto_updater")
            return False
    
    def update_check_job(self):
        """Job function for scheduled updates"""
        if self.is_running:
            query_logger.logger.info("Update check already running, skipping...")
            return
        
        self.is_running = True
        try:
            query_logger.logger.info("Checking for GitHub repository updates...")
            
            if self.check_for_updates():
                query_logger.logger.info("Updates found, triggering ingestion...")
                success = self.trigger_ingestion()
                
                if success:
                    # Update the last known commit
                    if GITHUB_REPO_URL:
                        crawler = initialize_github_crawler(GITHUB_REPO_URL, GITHUB_TOKEN)
                        if crawler:
                            latest_commit = crawler.get_latest_commit()
                            if latest_commit:
                                self.save_last_commit(latest_commit['sha'])
                else:
                    query_logger.log_error("Failed to complete automatic ingestion")
            else:
                query_logger.logger.info("No updates found")
                
        except Exception as e:
            query_logger.log_error(f"Update check job failed: {str(e)}", "auto_updater")
        
        finally:
            self.is_running = False
    
    def start_scheduler(self):
        """Start the update scheduler"""
        if not GITHUB_REPO_URL:
            query_logger.logger.info("No GitHub repo configured, auto-updater disabled")
            return
        
        # Convert seconds to minutes for schedule library
        interval_minutes = max(1, AUTO_UPDATE_INTERVAL // 60)
        
        query_logger.logger.info(f"Starting auto-updater (checking every {interval_minutes} minutes)")
        query_logger.logger.info(f"Monitoring repository: {GITHUB_REPO_URL}")
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(self.update_check_job)
        
        # Run initial check
        query_logger.logger.info("Running initial update check...")
        self.update_check_job()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def manual_update(self) -> bool:
        """Manually trigger an update check and ingestion"""
        query_logger.logger.info("Manual update triggered")
        return self.update_check_job()

# Global updater instance
auto_updater = AutoUpdater()

def main():
    """Main function to run the auto-updater"""
    print("Starting GitHub Auto-Updater...")
    try:
        auto_updater.start_scheduler()
    except KeyboardInterrupt:
        print("\\nAuto-updater stopped by user")
    except Exception as e:
        print(f"Auto-updater error: {str(e)}")

if __name__ == "__main__":
    main()