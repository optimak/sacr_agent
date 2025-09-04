#!/usr/bin/env python3
"""
Main scraper runner script that coordinates all scrapers and sends data to Notion
"""

import logging
from typing import List, Dict, Any
import time

# Import configuration and scrapers
from config import *
from okta_scraper import OktaScraper
from mandiant_scraper import MandiantScraper
from paloalto_scraper import PaloAltoScraper
from crowdstrike_scraper import CrowdStrikeScraper
from notion_integration import create_notion_database_and_pages

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CyberSecurityScraper:
    """Main coordinator class for running all scrapers"""
    
    def __init__(self):
        # Validate configuration on initialization
        validate_config()
        
        # Initialize scrapers with configuration
        self.scrapers = {
            'Okta': OktaScraper(get_scraper_config('Okta')),
            'Mandiant': MandiantScraper(get_scraper_config('Mandiant')),
            'Palo Alto': PaloAltoScraper(get_scraper_config('Palo Alto')),
            'CrowdStrike': CrowdStrikeScraper(get_scraper_config('CrowdStrike'))
        }
    
    def run_single_scraper(self, scraper_name: str) -> List[Dict[Any, Any]]:
        """Run a single scraper and return its data"""
        if scraper_name not in self.scrapers:
            logger.error(f"Unknown scraper: {scraper_name}")
            return []
        
        logger.info(f"Starting {scraper_name} scraper...")
        try:
            scraper = self.scrapers[scraper_name]
            posts_data = scraper.scrape_all_posts()
            logger.info(f"{scraper_name} scraper completed. Found {len(posts_data)} posts.")
            return posts_data
        except Exception as e:
            logger.error(f"Error running {scraper_name} scraper: {e}")
            return []
    
    def run_all_scrapers(self) -> List[Dict[Any, Any]]:
        """Run all scrapers and collect all data"""
        all_posts = []
        
        for scraper_name in self.scrapers.keys():
            posts_data = self.run_single_scraper(scraper_name)
            all_posts.extend(posts_data)
            
            # Be respectful to websites
            time.sleep(DELAY_BETWEEN_SCRAPERS)
        
        logger.info(f"All scrapers completed. Total posts collected: {len(all_posts)}")
        return all_posts
    
    def send_to_notion(self, posts_data: List[Dict[Any, Any]]):
        """Send scraped data to Notion database"""
        if not posts_data:
            logger.warning("No posts data to send to Notion")
            return
        
        logger.info(f"Sending {len(posts_data)} posts to Notion database '{DATABASE_NAME}'...")
        
        try:
            result = create_notion_database_and_pages(
                posts_data, 
                NOTION_TOKEN, 
                PARENT_PAGE_ID, 
                DATABASE_NAME
            )
            
            if result.get('error'):
                logger.error(f"Error creating Notion database: {result['error']}")
            else:
                logger.info(f"Successfully sent data to Notion. Database ID: {result.get('database_id')}")
                
        except Exception as e:
            logger.error(f"Error sending data to Notion: {e}")
    
    def run_full_pipeline(self):
        """Run the complete scraping pipeline"""
        logger.info("Starting full cybersecurity scraping pipeline...")
        
        # Run all scrapers
        all_posts = self.run_all_scrapers()
        
        if all_posts:
            # Send to Notion
            self.send_to_notion(all_posts)
        else:
            logger.warning("No posts were scraped from any source")
        
        logger.info("Pipeline completed")

def main():
    """Main entry point"""
    try:
        # Initialize and run the scraper
        scraper = CyberSecurityScraper()
        
        # You can run individual scrapers like this:
        # okta_posts = scraper.run_single_scraper('Okta')
        # scraper.send_to_notion(okta_posts)
        
        # Or run the full pipeline:
        scraper.run_full_pipeline()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()