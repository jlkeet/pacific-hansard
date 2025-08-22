#!/usr/bin/env python3
"""
Pacific Hansard Backlog Processor
Downloads and processes last 3 years of Hansards for Fiji and Cook Islands
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
import subprocess
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacklogProcessor:
    """Process backlog of Hansards for the last 3 years"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.target_years = [2022, 2023, 2024]
        
        # Paths to existing scrapers
        self.fiji_scraper = self.base_dir / "scripts/Fiji/fiji-hansard-scraper-2022-2024.py"
        self.fiji_converter = self.base_dir / "scripts/Fiji/fiji-hansard-converter-integrated.py"
        
        self.ci_scraper = self.base_dir / "scripts/Cook Islands/CI-hansard-scraper-simple.py"
        self.ci_converter = self.base_dir / "scripts/Cook Islands/CI-hansard-converter-integrated.py"
        
        # Status tracking
        self.status_file = self.base_dir / "backlog_status.json"
        self.load_status()
    
    def load_status(self):
        """Load processing status from file"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                self.status = json.load(f)
        else:
            self.status = {
                "fiji": {"completed_years": [], "last_updated": None},
                "cook_islands": {"completed_years": [], "last_updated": None},
                "started_at": None
            }
    
    def save_status(self):
        """Save processing status to file"""
        self.status["last_updated"] = datetime.now().isoformat()
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def check_existing_data(self, country):
        """Check what years we already have data for"""
        country_dir = self.base_dir / f"collections/{country}"
        existing_years = []
        
        if country_dir.exists():
            for year_dir in country_dir.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    year = int(year_dir.name)
                    if year in self.target_years:
                        # Check if year has substantial data (more than 1 document)
                        doc_count = len(list(year_dir.rglob("*.json")))
                        if doc_count > 2:  # metadata.json + processing_report.json minimum
                            existing_years.append(year)
        
        return existing_years
    
    def process_fiji_backlog(self):
        """Process Fiji Hansards for target years"""
        logger.info("🇫🇯 Starting Fiji backlog processing...")
        
        existing_years = self.check_existing_data("Fiji")
        completed_years = self.status["fiji"]["completed_years"]
        
        years_to_process = [year for year in self.target_years 
                           if year not in existing_years and year not in completed_years]
        
        if not years_to_process:
            logger.info("✅ All Fiji years already processed")
            return
        
        logger.info(f"📅 Processing Fiji years: {years_to_process}")
        
        for year in years_to_process:
            try:
                logger.info(f"🔄 Processing Fiji {year}...")
                
                # Run scraper for specific year
                cmd = [sys.executable, str(self.fiji_scraper), "--year", str(year)]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                
                if result.returncode == 0:
                    logger.info(f"✅ Fiji {year} scraping completed")
                    
                    # Run converter
                    cmd = [sys.executable, str(self.fiji_converter)]
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Fiji {year} conversion completed")
                        self.status["fiji"]["completed_years"].append(year)
                        self.save_status()
                    else:
                        logger.error(f"❌ Fiji {year} conversion failed: {result.stderr}")
                else:
                    logger.error(f"❌ Fiji {year} scraping failed: {result.stderr}")
                
                # Wait between years to be respectful to the server
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error processing Fiji {year}: {e}")
    
    def process_cook_islands_backlog(self):
        """Process Cook Islands Hansards for target years"""
        logger.info("🏝️ Starting Cook Islands backlog processing...")
        
        existing_years = self.check_existing_data("Cook Islands")
        completed_years = self.status["cook_islands"]["completed_years"]
        
        years_to_process = [year for year in self.target_years 
                           if year not in existing_years and year not in completed_years]
        
        if not years_to_process:
            logger.info("✅ All Cook Islands years already processed")
            return
        
        logger.info(f"📅 Processing Cook Islands years: {years_to_process}")
        
        for year in years_to_process:
            try:
                logger.info(f"🔄 Processing Cook Islands {year}...")
                
                # Run scraper with year filter
                cmd = [sys.executable, str(self.ci_scraper), "--start-year", str(year), "--end-year", str(year)]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                
                if result.returncode == 0:
                    logger.info(f"✅ Cook Islands {year} scraping completed")
                    
                    # Run converter
                    cmd = [sys.executable, str(self.ci_converter)]
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Cook Islands {year} conversion completed")
                        self.status["cook_islands"]["completed_years"].append(year)
                        self.save_status()
                    else:
                        logger.error(f"❌ Cook Islands {year} conversion failed: {result.stderr}")
                else:
                    logger.error(f"❌ Cook Islands {year} scraping failed: {result.stderr}")
                
                # Wait between years
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error processing Cook Islands {year}: {e}")
    
    def reindex_all(self):
        """Re-index all processed documents in Solr"""
        logger.info("🔄 Re-indexing all documents in Solr...")
        
        try:
            # Run the smart indexing pipeline
            indexer_path = self.base_dir / "pipelines_smart.py"
            cmd = [sys.executable, str(indexer_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                logger.info("✅ Re-indexing completed successfully")
            else:
                logger.error(f"❌ Re-indexing failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Error during re-indexing: {e}")
    
    def run_full_backlog(self):
        """Run complete backlog processing"""
        logger.info("🚀 Starting Pacific Hansard backlog processing...")
        
        if not self.status["started_at"]:
            self.status["started_at"] = datetime.now().isoformat()
            self.save_status()
        
        # Process both countries
        self.process_fiji_backlog()
        self.process_cook_islands_backlog()
        
        # Re-index everything
        self.reindex_all()
        
        logger.info("🎉 Backlog processing completed!")
        self.save_status()
    
    def get_status_report(self):
        """Get current processing status"""
        fiji_existing = self.check_existing_data("Fiji")
        ci_existing = self.check_existing_data("Cook Islands")
        
        return {
            "target_years": self.target_years,
            "fiji": {
                "existing_years": fiji_existing,
                "completed_years": self.status["fiji"]["completed_years"],
                "remaining": [y for y in self.target_years if y not in fiji_existing and y not in self.status["fiji"]["completed_years"]]
            },
            "cook_islands": {
                "existing_years": ci_existing,
                "completed_years": self.status["cook_islands"]["completed_years"],
                "remaining": [y for y in self.target_years if y not in ci_existing and y not in self.status["cook_islands"]["completed_years"]]
            }
        }

def main():
    """Main entry point"""
    processor = BacklogProcessor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        # Show status report
        status = processor.get_status_report()
        print("\n[STATUS] Backlog Processing Status:")
        print(f"Target Years: {status['target_years']}")
        print(f"\n[FIJI] Status:")
        print(f"  Existing: {status['fiji']['existing_years']}")
        print(f"  Completed: {status['fiji']['completed_years']}")
        print(f"  Remaining: {status['fiji']['remaining']}")
        print(f"\n[COOK ISLANDS] Status:")
        print(f"  Existing: {status['cook_islands']['existing_years']}")
        print(f"  Completed: {status['cook_islands']['completed_years']}")
        print(f"  Remaining: {status['cook_islands']['remaining']}")
        return
    
    # Run full backlog processing
    processor.run_full_backlog()

if __name__ == "__main__":
    main()