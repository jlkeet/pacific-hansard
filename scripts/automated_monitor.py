#!/usr/bin/env python3
"""
Pacific Hansard Automated Monitoring Pipeline
Continuously monitors for new Hansards and processes them automatically
"""

import os
import sys
import logging
import json
import time
import schedule
from datetime import datetime, timedelta
import subprocess
import hashlib
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hansard_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HansardMonitor:
    """Automated monitor for new Hansard publications"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.monitor_state_file = self.base_dir / "monitor_state.json"
        
        # URLs to monitor
        self.fiji_hansard_url = "https://www.parliament.gov.fj/hansard/"
        self.ci_hansard_url = "https://www.parliament.gov.ck/hansards"
        
        # Paths to processing scripts
        self.fiji_scraper = self.base_dir / "scripts/Fiji/fiji-hansard-scraper-dynamic.py"
        self.fiji_converter = self.base_dir / "scripts/Fiji/fiji-hansard-converter-integrated.py"
        
        self.ci_scraper = self.base_dir / "scripts/Cook Islands/CI-hansard-scraper.py"
        self.ci_converter = self.base_dir / "scripts/Cook Islands/CI-hansard-converter-integrated.py"
        
        self.indexer = self.base_dir / "pipelines_smart.py"
        
        # Load previous state
        self.load_state()
    
    def load_state(self):
        """Load monitoring state from file"""
        if self.monitor_state_file.exists():
            with open(self.monitor_state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "fiji": {
                    "last_check": None,
                    "known_hansards": [],
                    "last_hash": None
                },
                "cook_islands": {
                    "last_check": None,
                    "known_hansards": [],
                    "last_hash": None
                },
                "monitor_started": datetime.now().isoformat()
            }
    
    def save_state(self):
        """Save monitoring state to file"""
        with open(self.monitor_state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_page_hash(self, url):
        """Get hash of webpage content to detect changes"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML and extract relevant content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove dynamic elements (timestamps, etc.)
            for element in soup.find_all(['script', 'style', 'meta']):
                element.decompose()
            
            content = soup.get_text()
            return hashlib.sha256(content.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error getting hash for {url}: {e}")
            return None
    
    def check_fiji_updates(self):
        """Check for new Fiji Hansards"""
        logger.info("🇫🇯 Checking Fiji Parliament for updates...")
        
        current_hash = self.get_page_hash(self.fiji_hansard_url)
        
        if current_hash is None:
            logger.error("Failed to check Fiji site")
            return False
        
        last_hash = self.state["fiji"]["last_hash"]
        
        if last_hash != current_hash:
            logger.info("📄 New content detected on Fiji Parliament site!")
            
            # Run scraper to get new hansards
            self.process_new_hansards("fiji")
            
            # Update state
            self.state["fiji"]["last_hash"] = current_hash
            self.state["fiji"]["last_check"] = datetime.now().isoformat()
            self.save_state()
            
            return True
        else:
            logger.info("✅ No new Fiji hansards detected")
            self.state["fiji"]["last_check"] = datetime.now().isoformat()
            self.save_state()
            return False
    
    def check_cook_islands_updates(self):
        """Check for new Cook Islands Hansards"""
        logger.info("🏝️ Checking Cook Islands Parliament for updates...")
        
        current_hash = self.get_page_hash(self.ci_hansard_url)
        
        if current_hash is None:
            logger.error("Failed to check Cook Islands site")
            return False
        
        last_hash = self.state["cook_islands"]["last_hash"]
        
        if last_hash != current_hash:
            logger.info("📄 New content detected on Cook Islands Parliament site!")
            
            # Run scraper to get new hansards
            self.process_new_hansards("cook_islands")
            
            # Update state
            self.state["cook_islands"]["last_hash"] = current_hash
            self.state["cook_islands"]["last_check"] = datetime.now().isoformat()
            self.save_state()
            
            return True
        else:
            logger.info("✅ No new Cook Islands hansards detected")
            self.state["cook_islands"]["last_check"] = datetime.now().isoformat()
            self.save_state()
            return False
    
    def process_new_hansards(self, country):
        """Process newly detected hansards"""
        logger.info(f"🔄 Processing new {country} hansards...")
        
        try:
            if country == "fiji":
                scraper = self.fiji_scraper
                converter = self.fiji_converter
            else:  # cook_islands
                scraper = self.ci_scraper
                converter = self.ci_converter
            
            # Run scraper (only gets new documents)
            logger.info(f"📥 Running {country} scraper...")
            result = subprocess.run([sys.executable, str(scraper), "--recent-only"], 
                                  capture_output=True, text=True, cwd=self.base_dir,
                                  timeout=1800)  # 30 minute timeout
            
            if result.returncode == 0:
                logger.info(f"✅ {country} scraping completed")
                
                # Run converter
                logger.info(f"🔄 Running {country} converter...")
                result = subprocess.run([sys.executable, str(converter)], 
                                      capture_output=True, text=True, cwd=self.base_dir,
                                      timeout=1800)
                
                if result.returncode == 0:
                    logger.info(f"✅ {country} conversion completed")
                    
                    # Run indexer
                    self.reindex_new_documents()
                    
                    # Send notification
                    self.send_notification(f"New {country} hansards processed successfully")
                    
                else:
                    logger.error(f"❌ {country} conversion failed: {result.stderr}")
                    self.send_notification(f"ERROR: {country} conversion failed")
            else:
                logger.error(f"❌ {country} scraping failed: {result.stderr}")
                self.send_notification(f"ERROR: {country} scraping failed")
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {country} processing timed out")
            self.send_notification(f"ERROR: {country} processing timed out")
        except Exception as e:
            logger.error(f"❌ Error processing {country} hansards: {e}")
            self.send_notification(f"ERROR: {country} processing failed - {e}")
    
    def reindex_new_documents(self):
        """Re-index documents to include new ones"""
        logger.info("🔄 Re-indexing documents...")
        
        try:
            result = subprocess.run([sys.executable, str(self.indexer)], 
                                  capture_output=True, text=True, cwd=self.base_dir,
                                  timeout=3600)  # 1 hour timeout
            
            if result.returncode == 0:
                logger.info("✅ Re-indexing completed")
            else:
                logger.error(f"❌ Re-indexing failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Re-indexing error: {e}")
    
    def send_notification(self, message):
        """Send notification about processing results"""
        # For now, just log it - you can add email/Slack notifications later
        logger.info(f"📧 NOTIFICATION: {message}")
        
        # TODO: Add email/webhook notifications here
        # Example:
        # - Send email to admin
        # - Post to Slack channel  
        # - Send webhook to monitoring system
    
    def run_daily_check(self):
        """Run daily check for all countries"""
        logger.info("🕐 Starting daily Hansard check...")
        
        fiji_updated = self.check_fiji_updates()
        ci_updated = self.check_cook_islands_updates()
        
        if not fiji_updated and not ci_updated:
            logger.info("✅ Daily check completed - no updates found")
        else:
            logger.info("🎉 Daily check completed - updates processed")
    
    def run_weekly_maintenance(self):
        """Run weekly maintenance tasks"""
        logger.info("🔧 Running weekly maintenance...")
        
        # Clean up old log files
        log_files = list(Path('.').glob('*.log'))
        for log_file in log_files:
            if log_file.stat().st_mtime < (datetime.now() - timedelta(days=30)).timestamp():
                log_file.unlink()
                logger.info(f"🗑️ Deleted old log file: {log_file}")
        
        # Verify Solr health
        try:
            response = requests.get('http://localhost:8983/solr/admin/ping', timeout=10)
            if response.status_code == 200:
                logger.info("✅ Solr health check passed")
            else:
                logger.warning("⚠️ Solr health check failed")
        except Exception as e:
            logger.error(f"❌ Solr health check error: {e}")
        
        logger.info("✅ Weekly maintenance completed")
    
    def get_status(self):
        """Get current monitor status"""
        return {
            "monitor_started": self.state.get("monitor_started"),
            "fiji_last_check": self.state["fiji"]["last_check"],
            "cook_islands_last_check": self.state["cook_islands"]["last_check"],
            "total_checks": len([c for c in [self.state["fiji"]["last_check"], 
                               self.state["cook_islands"]["last_check"]] if c]),
            "uptime_hours": (datetime.now() - datetime.fromisoformat(self.state["monitor_started"])).total_seconds() / 3600 if self.state.get("monitor_started") else 0
        }
    
    def start_monitoring(self):
        """Start the automated monitoring"""
        logger.info("🚀 Starting Hansard automated monitoring...")
        
        # Schedule daily checks at 9 AM
        schedule.every().day.at("09:00").do(self.run_daily_check)
        
        # Schedule weekly maintenance on Sundays at 2 AM  
        schedule.every().sunday.at("02:00").do(self.run_weekly_maintenance)
        
        logger.info("⏰ Scheduled daily checks at 9:00 AM")
        logger.info("⏰ Scheduled weekly maintenance on Sundays at 2:00 AM")
        
        # Run initial check
        self.run_daily_check()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main entry point"""
    monitor = HansardMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            status = monitor.get_status()
            print("\n📊 Monitor Status:")
            print(f"Started: {status['monitor_started']}")
            print(f"Uptime: {status['uptime_hours']:.1f} hours")
            print(f"Fiji last check: {status['fiji_last_check']}")
            print(f"Cook Islands last check: {status['cook_islands_last_check']}")
            return
        
        elif sys.argv[1] == "--check-now":
            monitor.run_daily_check()
            return
        
        elif sys.argv[1] == "--maintenance":
            monitor.run_weekly_maintenance()
            return
    
    # Start continuous monitoring
    monitor.start_monitoring()

if __name__ == "__main__":
    main()